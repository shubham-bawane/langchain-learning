import asyncio
import json
import time
import uuid
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from main import llm
import rag
from reflection import reflection_graph, run_stream
from multiagent import GRAPHS as MA_GRAPHS, run_stream as run_multi_stream
from flow import enabled as flow_enabled, flow_graph, run_stream as run_flow_stream
from agent import agent_memory, agent_threads, build_agent, extract_steps, forget_agent_thread
from observability import MonitoringHandler, log, metrics

app = FastAPI(title="LangChain + OpenRouter")

MODELS = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "anthropic/claude-3.5-haiku",
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.1-8b-instruct",
]


@app.middleware("http")
async def monitor(request: Request, call_next):
    rid = uuid.uuid4().hex[:8]
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("rid=%s %s %s crashed", rid, request.method, request.url.path)
        metrics.record_request(error=True, rid=rid, method=request.method, path=request.url.path, status=500)
        raise
    ms = (time.perf_counter() - start) * 1000
    if not request.url.path.startswith(("/metrics", "/memory")):
        metrics.record_request(
            error=response.status_code >= 400, rid=rid, method=request.method,
            path=request.url.path, status=response.status_code, ms=round(ms),
        )
    log.info("rid=%s %s %s -> %s %.0fms", rid, request.method, request.url.path, response.status_code, ms)
    response.headers["X-Request-ID"] = rid
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def get_metrics() -> dict:
    return metrics.snapshot()


@app.get("/metrics/{name}")
async def get_metric_detail(name: str) -> list[dict]:
    rows = metrics.detail(name)
    if rows is None:
        raise HTTPException(status_code=404, detail=f"No detail for metric '{name}'")
    return rows


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    system_prompt: str = "You are a helpful assistant."
    temperature: float = Field(default=0.7, ge=0, le=2)
    model: str | None = Field(default=None, pattern=r"^[\w.\-]+/[\w.\-:]+$")
    thread_id: str | None = Field(default=None, pattern=r"^[\w\-]{1,64}$")


class ChatResponse(BaseModel):
    reply: str


MAX_HISTORY = 20  # messages kept per chat thread
chat_history: dict[str, list[tuple[str, str]]] = {}


@app.get("/memory")
async def list_memory() -> dict[str, dict[str, int]]:
    return {
        "agent_threads": agent_threads(),
        "chat_threads": {k: len(v) for k, v in chat_history.items()},
    }


@app.get("/memory/{thread_id}")
async def get_memory(thread_id: str) -> list[dict[str, Any]]:
    if thread_id.startswith("chat-"):
        return [{"role": r, "content": c} for r, c in chat_history.get(thread_id, [])]
    return agent_memory(thread_id)


@app.delete("/memory/{thread_id}")
async def clear_memory(thread_id: str) -> dict[str, str]:
    chat_history.pop(thread_id, None)
    forget_agent_thread(thread_id)
    return {"status": "cleared"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    history = chat_history.get(req.thread_id, []) if req.thread_id else []
    try:
        bound = llm.bind(temperature=req.temperature, model=req.model or llm.model_name)
        result = await bound.ainvoke(
            [("system", req.system_prompt), *history, ("human", req.message)],
            config={
                "callbacks": [MonitoringHandler()],
                "run_name": "chat",
                "tags": ["chapter-2"],
                "metadata": {"temperature": req.temperature, "model": req.model or llm.model_name},
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    reply = str(result.content)
    if req.thread_id:
        history = [*history, ("human", req.message), ("ai", reply)]
        chat_history[req.thread_id] = history[-MAX_HISTORY:]
    return ChatResponse(reply=reply)


class AgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    temperature: float = Field(default=0, ge=0, le=2)
    model: str | None = Field(default=None, pattern=r"^[\w.\-]+/[\w.\-:]+$")
    thread_id: str | None = Field(default=None, pattern=r"^[\w\-]{1,64}$")


class AgentResponse(BaseModel):
    answer: str
    steps: list[dict[str, Any]]


@app.post("/agent", response_model=AgentResponse)
async def run_agent(req: AgentRequest) -> AgentResponse:
    agent = build_agent(req.model or llm.model_name, req.temperature)
    thread_id = req.thread_id or uuid.uuid4().hex
    try:
        result = await agent.ainvoke(
            {"messages": [("human", req.message)]},
            config={
                "callbacks": [MonitoringHandler()],
                "run_name": "react-agent",
                "tags": ["chapter-3", "chapter-4"],
                "recursion_limit": 12,
                "configurable": {"thread_id": thread_id},
                "metadata": {"thread_id": thread_id},
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    steps, answer = extract_steps(result["messages"])
    return AgentResponse(answer=answer, steps=steps)


class RagRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    temperature: float = Field(default=0.2, ge=0, le=2)
    model: str | None = Field(default=None, pattern=r"^[\w.\-]+/[\w.\-:]+$")
    k: int = Field(default=4, ge=1, le=10)


class IngestRequest(BaseModel):
    source: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=500_000)


async def _rag(fn, *args):
    try:
        return await asyncio.to_thread(fn, *args)
    except rag.RagNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/rag/status")
async def rag_status() -> dict[str, Any]:
    return {"configured": rag.is_configured(), "collection": rag.COLLECTION, "embedding_model": rag.EMBED_MODEL}


@app.post("/rag/ingest")
async def rag_ingest(req: IngestRequest) -> dict[str, Any]:
    return {"source": req.source, "chunks": await _rag(rag.ingest_text, req.source, req.text)}


@app.post("/rag/ingest-docs")
async def rag_ingest_docs() -> dict[str, int]:
    return await _rag(rag.ingest_project_docs)


@app.get("/rag/sources")
async def rag_sources() -> dict[str, int]:
    return await _rag(rag.list_sources)


@app.delete("/rag/sources")
async def rag_delete_source(source: str) -> dict[str, str]:
    await _rag(rag.delete_source, source)
    return {"status": "deleted"}


@app.post("/rag/ask")
async def rag_ask(req: RagRequest) -> dict[str, Any]:
    if not rag.is_configured():
        raise HTTPException(status_code=503, detail="Set QDRANT_URL and QDRANT_API_KEY in .env and restart the server.")
    try:
        return await rag.answer(
            req.question, req.model or llm.model_name, req.temperature, req.k, [MonitoringHandler()]
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


class ReflectRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    max_reflections: int = Field(default=2, ge=1, le=5)
    temperature: float = Field(default=0.7, ge=0, le=2)
    model: str | None = Field(default=None, pattern=r"^[\w.\-]+/[\w.\-:]+$")


@app.post("/reflect")
async def reflect(req: ReflectRequest) -> StreamingResponse:
    async def lines():
        try:
            async for event in run_stream(
                req.message, req.max_reflections, req.model, req.temperature, [MonitoringHandler()]
            ):
                yield json.dumps(event) + "\n"
        except Exception as exc:
            log.exception("reflection graph failed")
            yield json.dumps({"type": "error", "detail": str(exc)}) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")


@app.get("/reflect/graph")
async def reflect_graph() -> dict[str, str]:
    return {"mermaid": reflection_graph.get_graph().draw_mermaid()}


class MultiRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    kind: Literal["duo", "trio", "quartet"] = "quartet"
    max_steps: int = Field(default=6, ge=2, le=8)
    temperature: float = Field(default=0.3, ge=0, le=2)
    model: str | None = Field(default=None, pattern=r"^[\w.\-]+/[\w.\-:]+$")


@app.post("/multi")
async def multi(req: MultiRequest) -> StreamingResponse:
    async def lines():
        try:
            async for event in run_multi_stream(
                req.kind, req.message, req.max_steps, req.model, req.temperature, [MonitoringHandler()]
            ):
                yield json.dumps(event) + "\n"
        except Exception as exc:
            log.exception("multi-agent graph failed")
            yield json.dumps({"type": "error", "detail": str(exc)}) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")


@app.get("/multi/graph/{kind}")
async def multi_graph(kind: str) -> dict[str, str]:
    if kind not in MA_GRAPHS:
        raise HTTPException(status_code=404, detail=f"Unknown kind '{kind}'")
    return {"mermaid": MA_GRAPHS[kind].get_graph().draw_mermaid()}


class FlowRequest(BaseModel):
    problem: str = Field(min_length=1, max_length=1500)
    max_attempts: int = Field(default=3, ge=1, le=5)
    temperature: float = Field(default=0.2, ge=0, le=2)
    model: str | None = Field(default=None, pattern=r"^[\w.\-]+/[\w.\-:]+$")


@app.get("/flow/status")
async def flow_status() -> dict[str, bool]:
    return {"enabled": flow_enabled()}


@app.post("/flow")
async def flow_run(req: FlowRequest) -> StreamingResponse:
    if not flow_enabled():
        raise HTTPException(
            status_code=403,
            detail="Running generated code is disabled. Set FLOW_ALLOW_CODE_EXEC=true in .env and restart.",
        )

    async def lines():
        try:
            async for event in run_flow_stream(
                req.problem, req.max_attempts, req.model, req.temperature, [MonitoringHandler()]
            ):
                yield json.dumps(event) + "\n"
        except Exception as exc:
            log.exception("flow graph failed")
            yield json.dumps({"type": "error", "detail": str(exc)}) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")


@app.get("/flow/graph")
async def flow_graph_def() -> dict[str, str]:
    return {"mermaid": flow_graph.get_graph().draw_mermaid()}


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>LangChain Chat</title>
<style>
body{font-family:sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem}
#log{border:1px solid #ccc;border-radius:6px;padding:.5rem;height:380px;overflow:auto;white-space:pre-wrap}
.u{color:#0645ad;margin:.4rem 0}.a{margin:.4rem 0}.e{color:#b00;margin:.4rem 0}.s{color:#666;font-size:13px;margin:.2rem 0 .2rem 1rem}
form{display:flex;gap:.5rem;margin-top:.5rem}input{flex:1;padding:.5rem}
@keyframes fadein{from{opacity:0;transform:translateY(6px)}}
@keyframes grow{from{width:0}}
@keyframes glow{0%,16%{background:#7c4dff;color:#fff;transform:scale(1.08)}17%,100%{background:#eee;color:#222;transform:none}}
#log>div{animation:fadein .3s ease-out}
.bar{height:6px;background:#eee;border-radius:3px;margin-top:3px;overflow:hidden}
.bar span{display:block;height:100%;width:var(--w);background:linear-gradient(90deg,#7c4dff,#00bcd4);animation:grow .8s ease-out}
.pipe{display:flex;flex-wrap:wrap;align-items:center;gap:.3rem;margin:.5rem 0;font-size:12px}
.pipe span{padding:.3rem .5rem;border-radius:6px;background:#eee;animation:glow 6s infinite;animation-delay:calc(var(--i)*1s)}
.pipe i{color:#999;font-style:normal}
.terms{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.5rem;margin-top:.5rem}
.term{border:1px solid #ccc;border-radius:8px;padding:.5rem;cursor:pointer;transition:transform .2s,box-shadow .2s;animation:fadein .4s backwards;animation-delay:calc(var(--i)*40ms)}
.term:hover{transform:translateY(-3px);box-shadow:0 4px 10px #0002}
.term p{margin:.3rem 0 0;font-size:12px;max-height:0;overflow:hidden;opacity:0;transition:max-height .3s,opacity .3s}
.term.open p{max-height:220px;opacity:1}
.term b::after{content:' +';color:#7c4dff}.term.open b::after{content:' −'}
#vb{transform-origin:100px 100px;transition:transform .25s}
.lg{border:1px solid #ddd;border-radius:10px;padding:.6rem;margin:.5rem 0;background:#fcfbff}
.lgcols{display:flex;gap:.8rem;flex-wrap:wrap;align-items:flex-start}
.lgnode rect,.lgnode circle{fill:#f2f0ff;stroke:#7c4dff;stroke-width:2;transition:fill .3s,stroke .3s}
.lgnode text{font-size:13px;text-anchor:middle;fill:#222;pointer-events:none}
.lgnode circle+text{font-size:10px}
.lgnode.active rect,.lgnode.active circle{fill:#7c4dff;animation:pulse 1s ease-in-out infinite}
.lgnode.active text{fill:#fff}
.lgnode.done rect,.lgnode.done circle{stroke:#2e7d32;fill:#e8f5e9}
@keyframes pulse{50%{filter:drop-shadow(0 0 8px #7c4dff)}}
.lgedge{fill:none;stroke:#bbb;stroke-width:2;transition:stroke .3s}
.lgedge.active{stroke:#7c4dff;stroke-dasharray:6 4;animation:dash .5s linear infinite}
@keyframes dash{to{stroke-dashoffset:-10}}
.lgl{font-size:10px;fill:#777;text-anchor:middle}
.lgcap{min-height:2.6em;font-size:13px;font-weight:bold;color:#4527a0;animation:fadein .4s}
.wwh{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:.5rem;margin:.5rem 0}
.wwh div{border-radius:8px;padding:.5rem;font-size:12px;border-left:4px solid #7c4dff;background:#f5f3ff;animation:fadein .5s backwards;animation-delay:calc(var(--i)*120ms)}
.wwh b{display:block;color:#5b34d6;margin-bottom:.2rem}
#lgstate{background:#272822;color:#e6e6e6;padding:.5rem;border-radius:6px;font-size:11px;min-width:240px;flex:1;overflow:auto;margin:0}
.tst{font-family:monospace;font-size:12px;padding:.15rem .4rem;border-radius:4px;margin:.15rem 0;animation:fadein .3s backwards;white-space:pre-wrap}
.tst.pending{background:#f5f5f5}.tst.pending::before{content:'… '}
.tst.pass{background:#e8f5e9}.tst.pass::before{content:'✓ ';color:#2e7d32;font-weight:bold}
.tst.fail{background:#ffebee}.tst.fail::before{content:'✗ ';color:#c62828;font-weight:bold}
#flcode{background:#272822;color:#e6e6e6;padding:.5rem;border-radius:6px;font-size:11px;overflow:auto;max-height:260px}
.chip{display:inline-block;padding:.15rem .5rem;border-radius:12px;color:#fff;font-size:11px;margin:.1rem;animation:fadein .4s backwards}
@keyframes glow4{0%,24%{background:#7c4dff;color:#fff;transform:scale(1.08)}25%,100%{background:#eee;color:#222;transform:none}}
.pipe.p4 span{animation-name:glow4;animation-duration:4s}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style></head><body>
<h2>LangChain + OpenRouter</h2>
<input id="sys" style="width:100%;box-sizing:border-box" value="You are a helpful assistant.">
<label>Model: <select id="model">__MODEL_OPTIONS__</select></label>
<label>Mode: <select id="mode"><option value="chat">Chat</option>
<option value="agent">Agent (ReAct tools)</option><option value="rag">RAG (knowledge base)</option>
<option value="reflect">Reflection (LangGraph)</option><option value="multi">Multi-agent team (LangGraph)</option><option value="flow">Flow engineering (code + tests)</option></select></label>
<label id="makindlbl" style="display:none">Team: <select id="makind"><option value="duo">2 agents: pipeline</option>
<option value="trio">3 agents: router</option><option value="quartet" selected>4 agents: supervisor loop</option></select></label>
<label id="flattlbl" style="display:none">Attempts: <select id="flatt"><option>1</option><option>2</option><option selected>3</option><option>4</option><option>5</option></select></label>
<label id="maxreflbl">Reflections: <select id="maxref"><option>1</option><option selected>2</option><option>3</option><option>4</option></select></label><br>
<details style="margin:.4rem 0"><summary>Knowledge base (Qdrant)</summary>
<div id="kbstatus" style="font-size:12px"></div>
<button type="button" id="kbdocs">Index project notes</button>
<button type="button" id="kbrefresh">Refresh sources</button><br>
<input id="kbname" placeholder="source name" style="width:200px;flex:none">
<input id="kbfile" type="file" accept=".txt,.md" style="flex:none">
<br><textarea id="kbtext" rows="3" style="width:100%;box-sizing:border-box" placeholder="...or paste text to index"></textarea>
<button type="button" id="kbadd">Add text</button>
<div id="kbsources" style="font-size:12px"></div></details>
<details style="margin:.4rem 0"><summary>Vector search glossary (click a card)</summary>
<div class="pipe">
<span style="--i:0">Question</span><i>&rarr;</i><span style="--i:1">Embed</span><i>&rarr;</i>
<span style="--i:2">Vector search (Qdrant)</span><i>&rarr;</i><span style="--i:3">Top-k chunks</span><i>&rarr;</i>
<span style="--i:4">LLM + context</span><i>&rarr;</i><span style="--i:5">Answer</span></div>
<div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap">
<svg width="200" height="200" viewBox="0 0 200 200" style="background:#fafafa;border:1px solid #ddd;border-radius:8px">
<defs><marker id="ah1" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#7c4dff"/></marker>
<marker id="ah2" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#00bcd4"/></marker></defs>
<circle cx="100" cy="100" r="80" fill="none" stroke="#ddd" stroke-dasharray="4"/>
<line x1="100" y1="100" x2="178" y2="100" stroke="#7c4dff" stroke-width="3" marker-end="url(#ah1)"/>
<g id="vb"><line x1="100" y1="100" x2="178" y2="100" stroke="#00bcd4" stroke-width="3" marker-end="url(#ah2)"/></g></svg>
<div><label>Angle between two vectors: <span id="ang">30</span>&deg;<br>
<input id="angle" type="range" min="0" max="180" value="30" style="width:220px;padding:0;flex:none"></label>
<div id="cosv" style="font-weight:bold;margin-top:.3rem"></div>
<small>Cosine similarity depends only on the angle (meaning), not on vector length.</small></div></div>
<div class="terms" id="terms"></div></details>
<details id="graphbox" style="margin:.4rem 0"><summary>LangGraph: reflection graph</summary>
<div class="pipe p4"><span style="--i:0">User request</span><i>&rarr;</i><span style="--i:1">Generate</span><i>&rarr;</i>
<span style="--i:2">Reflect</span><i>&#8635; repeat N times, or stop on APPROVED &rarr;</i><span style="--i:3">Final answer</span></div>
<small>Generated from the compiled graph (<code>get_graph().draw_mermaid()</code>):</small>
<pre id="graphsrc" style="background:#f5f5f5;padding:.5rem;font-size:11px;overflow:auto"></pre></details>
<label>Temperature: <span id="tv">0.7</span>
<input id="temp" type="range" min="0" max="2" step="0.1" value="0.7" style="width:200px;padding:0;flex:none"
 oninput="tv.textContent=this.value"></label>
<div id="maview" class="lg" style="display:none">
<div class="wwh" id="mainfo"></div>
<svg id="masvg" viewBox="0 0 520 230" style="width:100%;max-width:520px"></svg>
<div id="macap" class="lgcap">Pick a team size, then send a question. Each agent step is explained here.</div>
<div id="maroster"></div>
<div id="flextra" style="display:none">
<b style="font-size:12px">Tests (updated live: pending, then pass or fail)</b><div id="fltests"></div>
<b style="font-size:12px">Current code</b><pre id="flcode">(no code yet)</pre></div>
</div>
<div id="lgview" class="lg" style="display:none">
<div class="wwh">
<div style="--i:0"><b>WHAT</b>Reflection: one LLM call writes a draft, a second call critiques it, and the critique is fed back so the draft is rewritten. Repeated N times.</div>
<div style="--i:1"><b>WHY</b>A model reviewing finished text spots weak or missing parts better than it avoids them in one shot. Better quality, at the cost of extra calls (time and tokens).</div>
<div style="--i:2"><b>HOW</b>Shared state holds request, draft, critique and iteration. Nodes update it. Conditional edges choose: loop again, or stop at N or when the reviewer says APPROVED.</div>
<div style="--i:3"><b>LANGGRAPH</b>A graph is nodes + edges + state. You declare it once, compile() it, and LangGraph runs it and streams each node update. That stream drives this animation.</div></div>
<div class="lgcols">
<svg id="lgsvg" viewBox="0 0 520 200" style="width:100%;max-width:520px;flex:none">
<defs><marker id="lga" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#999"/></marker></defs>
<path id="e_start" class="lgedge" d="M52,100 L100,100" marker-end="url(#lga)"/>
<path id="e_gen_ref" class="lgedge" d="M200,100 L300,100" marker-end="url(#lga)"/>
<text class="lgl" x="250" y="92">more to do</text>
<path id="e_ref_gen" class="lgedge" d="M350,125 C350,185 150,185 150,125" marker-end="url(#lga)"/>
<text class="lgl" x="250" y="176">rewrite using critique</text>
<path id="e_gen_end" class="lgedge" d="M150,75 C150,10 480,10 480,78" marker-end="url(#lga)"/>
<text class="lgl" x="315" y="22">done: all reflections used</text>
<path id="e_ref_end" class="lgedge" d="M400,100 L458,100" marker-end="url(#lga)"/>
<text class="lgl" x="429" y="92">APPROVED</text>
<g class="lgnode" id="n_start"><circle cx="30" cy="100" r="22"/><text x="30" y="104">START</text></g>
<g class="lgnode" id="n_gen"><rect x="100" y="75" width="100" height="50" rx="10"/><text x="150" y="104">generate</text></g>
<g class="lgnode" id="n_ref"><rect x="300" y="75" width="100" height="50" rx="10"/><text x="350" y="104">reflect</text></g>
<g class="lgnode" id="n_end"><circle cx="480" cy="100" r="22"/><text x="480" y="104">END</text></g>
<circle id="tok" r="6" fill="#ff9800" opacity="0"><animateMotion id="tokanim" dur=".7s" begin="indefinite" fill="freeze"><mpath id="tokmpath" href="#e_start"/></animateMotion></circle>
</svg>
<pre id="lgstate">state = (run the Reflection mode to watch the shared state change)</pre></div>
<div id="lgcap" class="lgcap">Choose Mode: Reflection and send a request. Each step of the graph is explained here.</div>
</div>
<div id="log"></div>
<div style="margin-top:.3rem"><button type="button" id="newchat">New chat</button>
<button type="button" id="showmem">Memory</button>
<button type="button" id="clearmem">Clear memory</button>
<small>This tab remembers the conversation until you click New chat.</small></div>
<div id="memory" style="overflow:auto;font-size:12px"></div>
<div id="stats" style="display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.5rem"></div>
<div id="detail" style="overflow:auto;font-size:12px"></div>
<form id="f"><input id="m" placeholder="Type a message..." autocomplete="off" required>
<button>Send</button></form>
<script>
const log=document.getElementById('log');
let threadId=Math.random().toString(36).slice(2)+Date.now().toString(36);
document.getElementById('newchat').onclick=()=>{
  threadId=Math.random().toString(36).slice(2)+Date.now().toString(36);log.replaceChildren();
  if(memOpen)showMemory();
};
let memOpen=false;
const mode=()=>document.getElementById('mode').value;
const tid=()=>mode()+'-'+threadId;
const showLg=()=>{
  const m=mode(),$=id=>document.getElementById(id);
  $('lgview').style.display=m==='reflect'?'block':'none';
  $('maview').style.display=m==='multi'||m==='flow'?'block':'none';
  $('makindlbl').style.display=m==='multi'?'inline':'none';
  $('flattlbl').style.display=m==='flow'?'inline':'none';
  $('flextra').style.display=m==='flow'?'block':'none';
  $('maxreflbl').style.display=m==='reflect'?'inline':'none';
  if(m==='multi'||m==='flow')maBuild();
};
document.getElementById('mode').onchange=showLg;showLg();
async function showMemory(){
  memOpen=true;
  const box=document.getElementById('memory');
  const rows=await (await fetch('/memory/'+tid())).json();
  const t=document.createElement('table');t.style.borderCollapse='collapse';
  const row=(vals,tag)=>{const tr=t.insertRow();vals.forEach(v=>{const c=document.createElement(tag);c.textContent=v??'';c.style.cssText='border:1px solid #ccc;padding:2px 6px;text-align:left;vertical-align:top';tr.append(c)})};
  row(['#','role','content','tool calls'],'th');
  rows.forEach((x,i)=>row([i+1,x.role+(x.tool?' ('+x.tool+')':''),x.content,x.tool_calls?JSON.stringify(x.tool_calls):''],'td'));
  box.replaceChildren(document.createTextNode('Memory for thread '+tid()+': '+rows.length+' messages'),t);
}
document.getElementById('showmem').onclick=showMemory;
document.getElementById('clearmem').onclick=async()=>{
  await fetch('/memory/'+tid(),{method:'DELETE'});log.replaceChildren();if(memOpen)showMemory();
};
function add(c,t){const d=document.createElement('div');d.className=c;d.textContent=t;log.append(d);log.scrollTop=log.scrollHeight}
const lg=id=>document.getElementById(id);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const LG_NODES=['n_start','n_gen','n_ref','n_end'],LG_EDGES=['e_start','e_gen_ref','e_ref_gen','e_gen_end','e_ref_end'];
let lgState,lgMax=2,lgQueue=Promise.resolve();
function lgReset(request,max){
  lgMax=max;lgQueue=Promise.resolve();
  lgState={request:request,iteration:0,draft:'',critique:'',trace:[]};
  LG_NODES.forEach(n=>lg(n).classList.remove('active','done'));
  LG_EDGES.forEach(e=>lg(e).classList.remove('active'));
  lg('tok').setAttribute('opacity','0');lgShow();
}
function lgShow(){
  const S=lgState,nl=String.fromCharCode(10);
  lg('lgstate').textContent=['state = {',
    '  request: '+JSON.stringify(S.request.slice(0,50)),
    '  iteration: '+S.iteration+'   // drafts written so far',
    '  max_reflections: '+lgMax,
    '  draft: '+JSON.stringify(S.draft.slice(0,60)+(S.draft.length>60?'...':'')),
    '  critique: '+JSON.stringify(S.critique.slice(0,60)+(S.critique.length>60?'...':'')),
    '  trace: '+JSON.stringify(S.trace)+'   // reducer: appended, not replaced','}'].join(nl);
}
function lgSet(active,done,edge,caption){
  LG_NODES.forEach(n=>{lg(n).classList.toggle('active',n===active);lg(n).classList.toggle('done',done.includes(n))});
  LG_EDGES.forEach(e=>lg(e).classList.toggle('active',e===edge));
  if(edge&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
    lg('tok').setAttribute('opacity','1');lg('tokmpath').setAttribute('href','#'+edge);lg('tokanim').beginElement();
  } else lg('tok').setAttribute('opacity','0');
  const c=lg('lgcap');c.style.animation='none';c.offsetHeight;c.style.animation='';c.textContent=caption;
}
function lgStep(ev){lgQueue=lgQueue.then(()=>lgRun(ev))}
async function lgRun(ev){
  const S=lgState,base=['n_start'];
  if(ev.type==='start'){
    lgSet('n_start',[],'e_start','The request enters the graph at START and follows the edge to the generate node.');
    await sleep(800);
    lgSet('n_gen',base,null,'Node generate is running: the LLM writes draft 1 from the request.');
  }else if(ev.type==='draft'){
    S.iteration=ev.iteration;S.draft=ev.content;S.trace.push('generate #'+ev.iteration);lgShow();
    const done=ev.iteration>lgMax;
    lgSet('n_gen',base,done?'e_gen_end':'e_gen_ref','Draft '+ev.iteration+' saved to state. Conditional edge after_generate: iteration '+ev.iteration+(done?' is more than '+lgMax+' reflections, so route to END.':' is within '+lgMax+' reflections, so route to reflect.'));
    await sleep(900);
    if(!done)lgSet('n_ref',base,null,'Node reflect is running: the LLM reviews draft '+ev.iteration+' and writes Critique, Merits and Recommendations.');
  }else if(ev.type==='critique'){
    S.critique=ev.content;S.trace.push('reflect #'+ev.iteration);lgShow();
    if(ev.approved){
      lgSet('n_ref',base,'e_ref_end','Critique saved. Conditional edge after_reflect sees APPROVED, so route to END.');
      await sleep(900);
    }else{
      lgSet('n_ref',base,'e_ref_gen','Critique saved to state. after_reflect: not approved, so loop back to generate.');
      await sleep(900);
      lgSet('n_gen',base,null,'Node generate is running again: rewriting draft '+(ev.iteration+1)+' to address the critique.');
    }
  }else if(ev.type==='final'){
    lgSet('n_end',['n_start','n_gen','n_ref'],null,'Reached END after '+ev.drafts+' draft(s). Stopped because: '+(ev.stopped==='approved'?'the reviewer replied APPROVED.':'all allowed reflections were used.'));
  }else if(ev.type==='error'){
    lgSet(null,[],null,'The graph stopped with an error.');
  }
}
const MA_COLORS={supervisor:'#ff9800',researcher:'#2196f3',analyst:'#4caf50',writer:'#9c27b0',
 analyze:'#607d8b',write_tests:'#2196f3',generate_code:'#9c27b0',check_code:'#ff9800',run_tests:'#4caf50',diagnose:'#f44336'};
const MA_NAME={write_tests:'write tests',generate_code:'gen code',check_code:'check',run_tests:'run tests'};
const MA_LABELS={quartet:[[390,32,'FINISH']],
 flow:[[367,16,'unsafe code'],[318,168,'tests fail'],[300,128,'code bug'],[170,128,'test bug'],[352,142,'fixed tests'],[470,163,'pass']]};
let flHasCode=false,flMax=3;
const MA_ROLE={supervisor:'routes the work',researcher:'web search + knowledge base',analyst:'calculator, time, weather, word count',writer:'writes the final answer',
 analyze:'restates the task, signature and edge cases',write_tests:'writes assert tests, each one validated',generate_code:'writes the solution',
 check_code:'static allowlist safety check',run_tests:'runs the tests in a sandbox',diagnose:'code bug or test bug?'};
const MA_TEAM={duo:['researcher','writer'],trio:['supervisor','researcher','analyst'],quartet:['supervisor','researcher','analyst','writer'],
 flow:['analyze','write_tests','generate_code','check_code','run_tests','diagnose']};
const MA_INFO={
 duo:[['PATTERN','2 agents: pipeline. Researcher then Writer, always in that order. Fixed edges, no decisions.'],
  ['WHY','Splitting research from writing keeps each prompt focused. Simple, cheap and predictable.'],
  ['HOW','START to researcher (web search) to writer (no tools) to END. Each agent appends its notes to the shared state.']],
 trio:[['PATTERN','3 agents: router. A Supervisor reads the question and sends it to one specialist, Researcher or Analyst.'],
  ['WHY','Different questions need different tools. A router picks the expert instead of giving one agent every tool.'],
  ['HOW','The supervisor returns a structured Route (a Pydantic model) and a conditional edge follows it. The chosen specialist answers, then END.']],
 quartet:[['PATTERN','4 agents: supervisor loop. The Supervisor coordinates Researcher, Analyst and Writer until it says FINISH.'],
  ['WHY','Complex questions need several skills in turn. The supervisor can reuse workers, skip them, and stop when done.'],
  ['HOW','Every worker edge returns to the supervisor. Each turn it reads the shared notes and picks the next worker. A step limit prevents endless loops.']],
 flow:[['WHAT','Flow engineering: instead of one big prompt, design the whole multi-step process around the LLM. Each step has one small job, its output is validated, and a test run decides what happens next.'],
  ['WHY','One-shot code is often wrong. Tests give an objective signal, so errors are caught and fed back. Small validated steps are more reliable than one clever prompt.'],
  ['HOW','analyze, write tests, generate code, static safety check, run tests in a sandbox. If tests fail, diagnose decides code bug or test bug and loops, within a fixed attempt budget.'],
  ['SAFETY','Generated code is checked against an allowlist, then runs in a separate process with no environment variables, a timeout and memory limits. Defence in depth, not a perfect sandbox.']]
};
const MA_LAYOUT={
 duo:{nodes:{start:{t:'c',x:30,y:115},researcher:{t:'r',x:100,y:90,w:110},writer:{t:'r',x:285,y:90,w:110},end:{t:'c',x:490,y:115}},
  edges:[['start','researcher','M52,115 L100,115'],['researcher','writer','M210,115 L285,115'],['writer','end','M395,115 L468,115']]},
 trio:{nodes:{start:{t:'c',x:30,y:115},supervisor:{t:'r',x:90,y:90,w:110},researcher:{t:'r',x:275,y:25,w:110},analyst:{t:'r',x:275,y:155,w:110},end:{t:'c',x:490,y:115}},
  edges:[['start','supervisor','M52,115 L90,115'],['supervisor','researcher','M200,105 C240,105 240,50 275,50'],['supervisor','analyst','M200,125 C240,125 240,180 275,180'],
   ['researcher','end','M385,50 C440,50 480,70 484,94'],['analyst','end','M385,180 C440,180 480,160 484,136']]},
 quartet:{nodes:{start:{t:'c',x:30,y:40},supervisor:{t:'r',x:205,y:15,w:110},researcher:{t:'r',x:45,y:150,w:110},analyst:{t:'r',x:205,y:150,w:110},writer:{t:'r',x:365,y:150,w:110},end:{t:'c',x:490,y:40}},
  edges:[['start','supervisor','M52,40 L205,40'],['supervisor','end','M315,40 L468,40'],
   ['supervisor','researcher','M230,65 C200,110 130,105 115,150'],['researcher','supervisor','M135,150 C165,115 215,110 240,65'],
   ['supervisor','analyst','M250,65 L250,150'],['analyst','supervisor','M270,150 L270,65'],
   ['supervisor','writer','M290,65 C320,110 390,105 405,150'],['writer','supervisor','M385,150 C360,115 305,110 280,65']]},
 flow:{nodes:{start:{t:'c',x:26,y:70},analyze:{t:'r',x:60,y:45,w:90},write_tests:{t:'r',x:165,y:45,w:90},generate_code:{t:'r',x:270,y:45,w:90},check_code:{t:'r',x:375,y:45,w:90},
   run_tests:{t:'r',x:380,y:150,w:80},diagnose:{t:'r',x:165,y:150,w:90},end:{t:'c',x:495,y:175}},
  edges:[['start','analyze','M48,70 L60,70'],['analyze','write_tests','M150,70 L165,70'],['write_tests','generate_code','M255,70 L270,70'],['generate_code','check_code','M360,70 L375,70'],
   ['check_code','run_tests','M420,95 L420,150'],['check_code','generate_code','M400,45 C400,5 335,5 335,45'],['run_tests','end','M460,175 L473,175'],['run_tests','diagnose','M380,175 L255,175'],
   ['diagnose','generate_code','M240,150 C250,115 300,115 312,95'],['diagnose','write_tests','M190,150 C185,120 205,115 205,95'],['write_tests','run_tests','M255,88 C320,120 350,160 380,168']]}
};
let maQueue=Promise.resolve(),maVisited=new Set(),maRunKind='quartet';
function maBuild(){
  const kind=mode()==='flow'?'flow':document.getElementById('makind').value,L=MA_LAYOUT[kind],svg=document.getElementById('masvg');
  const NS='http://www.w3.org/2000/svg';
  const el=(n,a,p)=>{const e=document.createElementNS(NS,n);Object.entries(a||{}).forEach(([k,v])=>e.setAttribute(k,v));(p||svg).append(e);return e};
  svg.replaceChildren();
  const mk=el('marker',{id:'maa',markerWidth:8,markerHeight:8,refX:6,refY:4,orient:'auto'},el('defs'));
  el('path',{d:'M0,0 L8,4 L0,8 z',fill:'#999'},mk);
  L.edges.forEach(([a,b,d])=>el('path',{id:'me_'+a+'_'+b,class:'lgedge',d:d,'marker-end':'url(#maa)'}));
  (MA_LABELS[kind]||[]).forEach(([x,y,s])=>{const t=el('text',{class:'lgl',x:x,y:y});t.textContent=s});
  Object.entries(L.nodes).forEach(([name,n])=>{
    const g=el('g',{id:'mn_'+name,class:'lgnode'});
    if(n.t==='c'){el('circle',{cx:n.x,cy:n.y,r:22},g);const t=el('text',{x:n.x,y:n.y+4},g);t.textContent=name.toUpperCase()}
    else{el('rect',{x:n.x,y:n.y,width:n.w,height:50,rx:10,style:'stroke:'+MA_COLORS[name]},g);const t=el('text',{x:n.x+n.w/2,y:n.y+29},g);t.textContent=MA_NAME[name]||name}
  });
  const tok=el('circle',{id:'matok',r:6,fill:'#ff9800',opacity:0});
  const am=el('animateMotion',{id:'maanim',dur:'.7s',begin:'indefinite',fill:'freeze'},tok);
  el('mpath',{id:'mampath',href:'#'+L.edges[0][0]},am);
  const info=document.getElementById('mainfo');info.replaceChildren();
  MA_INFO[kind].forEach(([h,t],i)=>{const d=document.createElement('div'),b=document.createElement('b');d.style.setProperty('--i',i);b.textContent=h;d.append(b,t);info.append(d)});
  const ro=document.getElementById('maroster');ro.replaceChildren();
  MA_TEAM[kind].forEach((a,i)=>{const c=document.createElement('span');c.className='chip';c.style.background=MA_COLORS[a];c.style.animationDelay=(i*120)+'ms';c.textContent=a+': '+MA_ROLE[a];ro.append(c)});
  maReset();
}
document.getElementById('makind').onchange=maBuild;
function maReset(){
  maQueue=Promise.resolve();maVisited=new Set();flHasCode=false;
  document.getElementById('fltests').replaceChildren();document.getElementById('flcode').textContent='(no code yet)';
  document.getElementById('macap').textContent='Pick a team size, then send a question. Each agent step is explained here.';
}
function maSet(active,done,edge,caption){
  Object.keys(MA_LAYOUT[maRunKind].nodes).forEach(n=>{const e=document.getElementById('mn_'+n);e.classList.toggle('active',n===active);e.classList.toggle('done',done.includes(n))});
  MA_LAYOUT[maRunKind].edges.forEach(([a,b])=>document.getElementById('me_'+a+'_'+b).classList.toggle('active','me_'+a+'_'+b===edge));
  const tok=document.getElementById('matok');
  if(edge&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
    tok.setAttribute('opacity','1');document.getElementById('mampath').setAttribute('href','#'+edge);document.getElementById('maanim').beginElement();
  } else tok.setAttribute('opacity','0');
  const c=document.getElementById('macap');c.style.animation='none';c.offsetHeight;c.style.animation='';c.textContent=caption;
}
function maNext(node,entries){
  if(maRunKind==='duo')return node==='researcher'?'writer':'end';
  if(node==='supervisor'){const d=entries.find(e=>e.type==='decision');return !d||d.next==='FINISH'?'end':d.next}
  return maRunKind==='trio'?'end':'supervisor';
}
function maStep(ev){maQueue=maQueue.then(()=>maRun(ev))}
async function maRun(ev){
  const first=maRunKind==='duo'?'researcher':'supervisor';
  if(ev.type==='start'){
    maSet('start',[],'me_start_'+first,'The question enters at START and goes to the '+first+'.');
    await sleep(800);
    maSet(first,['start'],null,'The '+first+' is working...');
  }else if(ev.type==='update'){
    maVisited.add(ev.node);
    const next=maNext(ev.node,ev.entries),d=ev.entries.find(e=>e.type==='decision');
    const why=ev.node==='supervisor'?'Supervisor chose '+next+(d?': '+d.reason:''):'The '+ev.node+' finished. Its notes are added to the shared state, then control moves to '+(next==='end'?'END':'the '+next)+'.';
    maSet(ev.node,['start',...maVisited].filter(n=>n!==ev.node),'me_'+ev.node+'_'+next,why);
    await sleep(900);
    if(next!=='end')maSet(next,['start',...maVisited],null,'The '+next+' is working...');
  }else if(ev.type==='final'){
    maSet('end',['start',...maVisited],null,'Done. '+ev.agents+' agents cooperated through shared state'+(ev.supervisor_turns?' ('+ev.supervisor_turns+' supervisor decisions).':'.'));
  }else if(ev.type==='error'){
    maSet(null,[],null,'The team stopped with an error.');
  }
}
function addAgent(agent,text,cls){
  const d=document.createElement('div');d.className=cls;
  d.style.cssText='border-left:4px solid '+(MA_COLORS[agent]||'#999')+';padding-left:.5rem';
  d.textContent=text;log.append(d);log.scrollTop=log.scrollHeight;
}
function multiEvent(ev){
  maStep(ev);
  if(ev.type==='update')ev.entries.forEach(e=>{
    if(e.type==='decision')addAgent(e.agent,'Supervisor chose '+e.next+': '+e.reason,'s');
    else if(e.type==='action')addAgent(e.agent,'['+e.agent+'] tool '+e.tool+' '+JSON.stringify(e.input),'s');
    else if(e.type==='observation')addAgent(e.agent,'['+e.agent+'] result: '+String(e.output).slice(0,200),'s');
    else addAgent(e.agent,'['+e.agent+'] '+e.content,'a');
  });
  else if(ev.type==='final')add('a','FINAL ANSWER ('+ev.agents+' agents): '+ev.answer);
  else if(ev.type==='error')add('e','Error: '+ev.detail);
}
const FL_WORK={analyze:'analyze is working: restating the task, signature, requirements and edge cases.',
 write_tests:'write_tests is working: writing assert statements, each validated before it is used.',
 generate_code:'generate_code is working: writing the solution.',check_code:'check_code is working: static allowlist check of the code.',
 run_tests:'run_tests is working: running every test in a sandboxed process.',diagnose:'diagnose is working: deciding whether the code or the tests are wrong.'};
function flNext(node,e,attempts){
  if(node==='analyze')return 'write_tests';
  if(node==='write_tests')return flHasCode?'run_tests':'generate_code';
  if(node==='generate_code')return 'check_code';
  if(node==='check_code')return e.ok?'run_tests':(attempts>=flMax?'end':'generate_code');
  if(node==='run_tests')return (e.total>0&&e.passed===e.total)||attempts>=flMax?'end':'diagnose';
  return e.verdict==='test_bug'?'write_tests':'generate_code';
}
function flCaption(node,e,next,attempts){
  if(node==='analyze')return 'Analysis saved to state. Fixed edge to write_tests.';
  if(node==='write_tests')return (e.rejected&&e.rejected.length?e.rejected.length+' test(s) rejected by validation. ':'')+e.tests.length+' valid tests saved. Conditional edge after_tests: '+(flHasCode?'tests were corrected, so re-run them on the existing code.':'no code yet, so generate it.');
  if(node==='generate_code')return 'Code version '+e.version+' saved to state. Fixed edge to check_code.';
  if(node==='check_code')return e.ok?'Static check passed. Conditional edge after_check: go and run the tests.':'Static check rejected the code ('+e.problems.join('; ')+'). '+(next==='end'?'Attempt budget used up, so END.':'Back to generate_code.');
  if(node==='run_tests')return e.passed+'/'+e.total+' tests passed (attempt '+attempts+' of '+flMax+'). Conditional edge after_run: '+(next==='end'?(e.passed===e.total?'all pass, so END.':'budget used up, so END.'):'failures remain, so diagnose.');
  return 'Diagnosis: '+e.verdict+'. Conditional edge after_diagnose: '+(e.verdict==='test_bug'?'fix the tests (write_tests).':'rewrite the code (generate_code).');
}
function flStep(ev){maQueue=maQueue.then(()=>flRun(ev))}
async function flRun(ev){
  if(ev.type==='start'){
    maSet('start',[],'me_start_analyze','The problem enters the flow at START.');
    await sleep(700);
    maSet('analyze',['start'],null,FL_WORK.analyze);
  }else if(ev.type==='update'){
    maVisited.add(ev.node);if(ev.node==='generate_code')flHasCode=true;
    const e=ev.entries[0]||{},next=flNext(ev.node,e,ev.attempts),edge='me_'+ev.node+'_'+next;
    maSet(ev.node,['start',...maVisited].filter(n=>n!==ev.node),document.getElementById(edge)?edge:null,flCaption(ev.node,e,next,ev.attempts));
    await sleep(900);
    if(next!=='end')maSet(next,['start',...maVisited],null,FL_WORK[next]);
  }else if(ev.type==='final'){
    maSet('end',['start',...maVisited],null,ev.status==='passed'?'All '+ev.total+' tests pass after '+ev.attempts+' test run(s). The flow ends successfully.':'Stopped: '+ev.passed+'/'+ev.total+' tests pass and the attempt budget ('+flMax+') is used up.');
  }else if(ev.type==='error'){
    maSet(null,[],null,'The flow stopped with an error.');
  }
}
function flShowTests(items){
  const box=document.getElementById('fltests');box.replaceChildren();
  items.forEach((it,i)=>{
    const r=typeof it==='string'?{test:it,status:'pending',error:''}:{test:it.test,status:it.passed?'pass':'fail',error:it.error};
    const d=document.createElement('div');d.className='tst '+r.status;d.style.animationDelay=(i*60)+'ms';
    d.textContent=r.test+(r.error?'   -> '+r.error:'');box.append(d);
  });
}
function flowEvent(ev){
  flStep(ev);
  if(ev.type==='update')ev.entries.forEach(e=>{
    if(e.type==='analysis')addAgent(ev.node,'analyze: '+e.function_name+'  '+e.signature+'  ('+e.requirements.length+' requirements, '+e.edge_cases.length+' edge cases)','s');
    else if(e.type==='tests'){flShowTests(e.tests);addAgent(ev.node,'write_tests: '+e.tests.length+' valid tests'+(e.rejected.length?', '+e.rejected.length+' rejected by validation':''),'s')}
    else if(e.type==='code'){document.getElementById('flcode').textContent=e.code;addAgent(ev.node,'generate_code: version '+e.version+' ('+e.code.split(String.fromCharCode(10)).length+' lines)','a')}
    else if(e.type==='static')addAgent(ev.node,e.ok?'check_code: static check passed':'check_code: REJECTED - '+e.problems.join('; '),e.ok?'s':'e');
    else if(e.type==='results'){flShowTests(e.results);addAgent(ev.node,'run_tests: '+e.passed+'/'+e.total+' passed'+(e.error?' ('+e.error+')':''),e.passed===e.total?'a':'e')}
    else if(e.type==='diagnosis')addAgent(ev.node,'diagnose: '+e.verdict+' - '+e.explanation,'s');
  });
  else if(ev.type==='final')add('a','FLOW '+ev.status.toUpperCase()+': '+ev.passed+'/'+ev.total+' tests pass after '+ev.attempts+' test run(s).');
  else if(ev.type==='error')add('e','Error: '+ev.detail);
}
function reflectEvent(ev){
  lgStep(ev);
  if(ev.type==='draft')add('a','Draft '+ev.iteration+':\\n'+ev.content);
  else if(ev.type==='critique')add('s',(ev.approved?'Reviewer approved the draft.':'Reflection '+ev.iteration+':\\n'+ev.content));
  else if(ev.type==='final')add('a','Done after '+ev.drafts+' draft(s), stopped because: '+ev.stopped);
  else if(ev.type==='error')add('e','Error: '+ev.detail);
}
function addSource(s){
  const d=document.createElement('div');d.className='s';
  d.textContent='['+s.n+'] '+s.source+' (score '+s.score+'): '+s.text.slice(0,160)+'...';
  const bar=document.createElement('div');bar.className='bar';
  const fill=document.createElement('span');
  fill.style.setProperty('--w',Math.max(0,Math.min(1,s.score))*100+'%');
  bar.append(fill);d.append(bar);log.append(d);log.scrollTop=log.scrollHeight;
}
document.getElementById('f').onsubmit=async e=>{
  e.preventDefault();
  const m=document.getElementById('m');const text=m.value;m.value='';
  add('u','You: '+text);
  const agentMode=mode()==='agent';
  if(mode()==='flow'){
    maRunKind='flow';flMax=parseInt(document.getElementById('flatt').value);maReset();flStep({type:'start'});
    const r=await fetch('/flow',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({problem:text,max_attempts:flMax,temperature:parseFloat(document.getElementById('temp').value),
        model:document.getElementById('model').value})});
    if(!r.ok){const j=await r.json();add('e','Error: '+(typeof j.detail==='string'?j.detail:JSON.stringify(j.detail)));return}
    const reader=r.body.getReader(),dec=new TextDecoder(),nl=String.fromCharCode(10);let buf='';
    while(true){
      const {done,value}=await reader.read();if(done)break;
      buf+=dec.decode(value,{stream:true});
      const parts=buf.split(nl);buf=parts.pop();
      parts.filter(l=>l.trim()).forEach(l=>flowEvent(JSON.parse(l)));
    }
    refreshStats();return;
  }
  if(mode()==='multi'){
    maRunKind=document.getElementById('makind').value;maReset();maStep({type:'start'});
    const r=await fetch('/multi',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:text,kind:maRunKind,temperature:parseFloat(document.getElementById('temp').value),
        model:document.getElementById('model').value})});
    if(!r.ok){add('e','Error: '+r.status);return}
    const reader=r.body.getReader(),dec=new TextDecoder(),nl=String.fromCharCode(10);let buf='';
    while(true){
      const {done,value}=await reader.read();if(done)break;
      buf+=dec.decode(value,{stream:true});
      const parts=buf.split(nl);buf=parts.pop();
      parts.filter(l=>l.trim()).forEach(l=>multiEvent(JSON.parse(l)));
    }
    refreshStats();return;
  }
  if(mode()==='reflect'){
    add('s','Graph started: generate -> reflect -> generate ...');
    lgReset(text,parseInt(document.getElementById('maxref').value));lgStep({type:'start'});
    const r=await fetch('/reflect',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:text,max_reflections:parseInt(document.getElementById('maxref').value),
        temperature:parseFloat(document.getElementById('temp').value),model:document.getElementById('model').value})});
    if(!r.ok){add('e','Error: '+r.status);return}
    const reader=r.body.getReader(),dec=new TextDecoder();let buf='';
    while(true){
      const {done,value}=await reader.read();if(done)break;
      buf+=dec.decode(value,{stream:true});
      const parts=buf.split('\\n');buf=parts.pop();
      parts.filter(l=>l.trim()).forEach(l=>reflectEvent(JSON.parse(l)));
    }
    refreshStats();return;
  }
  if(mode()==='rag'){
    const r=await fetch('/rag/ask',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({question:text,temperature:parseFloat(document.getElementById('temp').value),
        model:document.getElementById('model').value})});
    const j=await r.json();
    if(!r.ok)add('e','Error: '+JSON.stringify(j.detail));
    else{
      j.sources.forEach(addSource);
      add('a','AI: '+j.answer);
    }
    refreshStats();return;
  }
  const body={message:text,temperature:parseFloat(document.getElementById('temp').value),
    model:document.getElementById('model').value,thread_id:tid()};
  if(!agentMode)body.system_prompt=document.getElementById('sys').value;
  const r=await fetch(agentMode?'/agent':'/chat',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)});
  const j=await r.json();
  if(!r.ok)add('e','Error: '+JSON.stringify(j.detail));
  else if(agentMode){
    j.steps.forEach(s=>add('s',s.type==='action'
      ?'Action: '+s.tool+' '+JSON.stringify(s.input):'Observation: '+s.output));
    add('a','AI: '+j.answer);
  } else add('a','AI: '+j.reply);
  refreshStats();
  if(memOpen)showMemory();
};
async function refreshStats(){
  const s=await (await fetch('/metrics')).json();
  const box=document.getElementById('stats');box.innerHTML='';
  for(const [k,v] of Object.entries(s)){
    const b=document.createElement('button');b.type='button';
    b.textContent=k+': '+(v??'-');b.onclick=()=>showDetail(k);box.append(b);
  }
  if(current)showDetail(current);
}
let current=null;
async function showDetail(name){
  current=name;
  const d=document.getElementById('detail');
  const r=await fetch('/metrics/'+name);
  if(!r.ok){d.textContent='No detail for '+name;return}
  const rows=await r.json();
  if(!rows.length){d.textContent=name+': no data yet';return}
  const cols=[...new Set(rows.flatMap(Object.keys))];
  const t=document.createElement('table');t.style.borderCollapse='collapse';
  const row=(vals,tag)=>{const tr=t.insertRow();vals.forEach(v=>{const c=document.createElement(tag);c.textContent=v??'';c.style.cssText='border:1px solid #ccc;padding:2px 6px';tr.append(c)})};
  row(cols,'th');rows.slice().reverse().forEach(x=>row(cols.map(c=>x[c]),'td'));
  d.replaceChildren(document.createTextNode('Details: '+name),t);
}
refreshStats();
const kbmsg=t=>document.getElementById('kbstatus').textContent=t;
async function kbPost(url,body){
  kbmsg('Working...');
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
  const j=await r.json();
  kbmsg(r.ok?'Done: '+JSON.stringify(j):'Error: '+JSON.stringify(j.detail));
  loadSources();
}
async function loadSources(){
  const box=document.getElementById('kbsources');
  const r=await fetch('/rag/sources');
  if(!r.ok){box.textContent='';return}
  const j=await r.json();box.replaceChildren();
  Object.entries(j).forEach(([s,n])=>{
    const d=document.createElement('div');d.textContent=s+' ('+n+' chunks) ';
    const b=document.createElement('button');b.type='button';b.textContent='delete';
    b.onclick=async()=>{await fetch('/rag/sources?source='+encodeURIComponent(s),{method:'DELETE'});loadSources()};
    d.append(b);box.append(d);
  });
  if(!Object.keys(j).length)box.textContent='No documents indexed yet.';
}
document.getElementById('kbdocs').onclick=()=>kbPost('/rag/ingest-docs');
document.getElementById('kbrefresh').onclick=loadSources;
document.getElementById('kbfile').onchange=async e=>{
  const f=e.target.files[0];if(!f)return;
  document.getElementById('kbname').value=f.name;
  document.getElementById('kbtext').value=await f.text();
};
document.getElementById('kbadd').onclick=()=>{
  const source=document.getElementById('kbname').value.trim(),text=document.getElementById('kbtext').value.trim();
  if(source&&text)kbPost('/rag/ingest',{source,text});else kbmsg('Need a source name and text.');
};
fetch('/rag/status').then(r=>r.json()).then(s=>{
  kbmsg(s.configured?'Collection: '+s.collection+' | embeddings: '+s.embedding_model:'Qdrant not configured: set QDRANT_URL and QDRANT_API_KEY in .env, then restart.');
  if(s.configured)loadSources();
});
document.getElementById('graphbox').ontoggle=async e=>{
  const pre=document.getElementById('graphsrc');
  if(e.target.open&&!pre.textContent){
    const r=await fetch('/reflect/graph');
    pre.textContent=r.ok?(await r.json()).mermaid:'Could not load the graph.';
  }
};
const TERMS=[
 ["Embedding","A list of numbers (1536 here) that captures the meaning of text. Similar meaning gives nearby numbers.","car and automobile get very close vectors."],
 ["Semantic search","Search by meaning instead of exact words.","How do I stop the app? can match a passage about shutting down the server."],
 ["Keyword search","Matches the literal words (BM25). Great for names and ids, blind to synonyms.","Combined with vector search it is called hybrid search."],
 ["Cosine similarity","Compares the angle between two vectors: 1 = same direction, 0 = unrelated, -1 = opposite. Ignores length.","Try the angle slider above."],
 ["Cosine distance","1 minus cosine similarity. Smaller means closer.",""],
 ["Dot product / Euclidean","Other ways to measure closeness. Dot product equals cosine for unit-length vectors; Euclidean is straight-line distance.",""],
 ["Score","The similarity Qdrant returns for each hit; the bar under each source shows it. Only compare scores for the same query and model.",""],
 ["Top-k","How many nearest chunks to fetch. Too low misses the answer, too high adds noise.","We default to k=4."],
 ["Chunk and overlap","Documents are cut into pieces (800 chars) that overlap (100) so a sentence on a boundary is not lost.",""],
 ["Collection and point","A collection is Qdrant's table. Each point is id + vector + payload.",""],
 ["Payload","JSON stored next to the vector: the chunk text and metadata.source. Can be used to filter.",""],
 ["ANN / HNSW","Approximate nearest-neighbour search using a graph index, so Qdrant does not compare against every vector.",""],
 ["Re-ranking","A slower second model that reorders the top hits for precision. Not used yet.",""],
 ["Grounding","Answering only from retrieved text. When the context lacks the answer, say I dont know instead of hallucinating.",""]
];
TERMS.forEach(([name,def,ex],i)=>{
  const c=document.createElement('div');c.className='term';c.style.setProperty('--i',i);
  const b=document.createElement('b');b.textContent=name;
  const p=document.createElement('p');p.textContent=def+(ex?' Example: '+ex:'');
  c.append(b,p);c.onclick=()=>c.classList.toggle('open');document.getElementById('terms').append(c);
});
const angle=document.getElementById('angle');
function updAngle(){
  const a=+angle.value,c=Math.cos(a*Math.PI/180);
  document.getElementById('ang').textContent=a;
  document.getElementById('vb').style.transform='rotate('+(-a)+'deg)';
  document.getElementById('cosv').textContent='cosine similarity = '+c.toFixed(2)+
    (a<=20?' (very similar)':a<=60?' (related)':a<=100?' (unrelated)':' (opposite)');
}
angle.oninput=updAngle;updAngle();</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    models = [llm.model_name] + [m for m in MODELS if m != llm.model_name]
    options = "".join(f'<option value="{m}">{m}</option>' for m in models)
    return PAGE.replace("__MODEL_OPTIONS__", options)
