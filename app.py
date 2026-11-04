import asyncio
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from main import llm
import rag
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
.term b::after{content:' +';color:#7c4dff}.term.open b::after{content:' \2212'}
#vb{transform-origin:100px 100px;transition:transform .25s}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style></head><body>
<h2>LangChain + OpenRouter</h2>
<input id="sys" style="width:100%;box-sizing:border-box" value="You are a helpful assistant.">
<label>Model: <select id="model">__MODEL_OPTIONS__</select></label>
<label>Mode: <select id="mode"><option value="chat">Chat</option>
<option value="agent">Agent (ReAct tools)</option><option value="rag">RAG (knowledge base)</option></select></label><br>
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
<label>Temperature: <span id="tv">0.7</span>
<input id="temp" type="range" min="0" max="2" step="0.1" value="0.7" style="width:200px;padding:0;flex:none"
 oninput="tv.textContent=this.value"></label>
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
