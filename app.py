import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from main import llm
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


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>LangChain Chat</title>
<style>
body{font-family:sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem}
#log{border:1px solid #ccc;border-radius:6px;padding:.5rem;height:380px;overflow:auto;white-space:pre-wrap}
.u{color:#0645ad;margin:.4rem 0}.a{margin:.4rem 0}.e{color:#b00;margin:.4rem 0}.s{color:#666;font-size:13px;margin:.2rem 0 .2rem 1rem}
form{display:flex;gap:.5rem;margin-top:.5rem}input{flex:1;padding:.5rem}
</style></head><body>
<h2>LangChain + OpenRouter</h2>
<input id="sys" style="width:100%;box-sizing:border-box" value="You are a helpful assistant.">
<label>Model: <select id="model">__MODEL_OPTIONS__</select></label>
<label><input type="checkbox" id="agent" style="flex:none"> Agent mode (ReAct: calculator, time, word count, web search, weather)</label><br>
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
const tid=()=>(document.getElementById('agent').checked?'agent-':'chat-')+threadId;
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
document.getElementById('f').onsubmit=async e=>{
  e.preventDefault();
  const m=document.getElementById('m');const text=m.value;m.value='';
  add('u','You: '+text);
  const agentMode=document.getElementById('agent').checked;
  const body={message:text,temperature:parseFloat(document.getElementById('temp').value),
    model:document.getElementById('model').value,thread_id:(agentMode?'agent-':'chat-')+threadId};
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
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    models = [llm.model_name] + [m for m in MODELS if m != llm.model_name]
    options = "".join(f'<option value="{m}">{m}</option>' for m in models)
    return PAGE.replace("__MODEL_OPTIONS__", options)
