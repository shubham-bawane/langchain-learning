from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from main import llm

app = FastAPI(title="LangChain + OpenRouter")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    system_prompt: str = "You are a helpful assistant."
    temperature: float = Field(default=0.7, ge=0, le=2)


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        result = await llm.bind(temperature=req.temperature).ainvoke(
            [("system", req.system_prompt), ("human", req.message)]
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ChatResponse(reply=str(result.content))


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>LangChain Chat</title>
<style>
body{font-family:sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem}
#log{border:1px solid #ccc;border-radius:6px;padding:.5rem;height:380px;overflow:auto;white-space:pre-wrap}
.u{color:#0645ad;margin:.4rem 0}.a{margin:.4rem 0}.e{color:#b00;margin:.4rem 0}
form{display:flex;gap:.5rem;margin-top:.5rem}input{flex:1;padding:.5rem}
</style></head><body>
<h2>LangChain + OpenRouter</h2>
<input id="sys" style="width:100%;box-sizing:border-box" value="You are a helpful assistant.">
<label>Temperature: <span id="tv">0.7</span>
<input id="temp" type="range" min="0" max="2" step="0.1" value="0.7" style="width:200px;padding:0;flex:none"
 oninput="tv.textContent=this.value"></label>
<div id="log"></div>
<form id="f"><input id="m" placeholder="Type a message..." autocomplete="off" required>
<button>Send</button></form>
<script>
const log=document.getElementById('log');
function add(c,t){const d=document.createElement('div');d.className=c;d.textContent=t;log.append(d);log.scrollTop=log.scrollHeight}
document.getElementById('f').onsubmit=async e=>{
  e.preventDefault();
  const m=document.getElementById('m');const text=m.value;m.value='';
  add('u','You: '+text);
  const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:text,system_prompt:document.getElementById('sys').value,
    temperature:parseFloat(document.getElementById('temp').value)})});
  const j=await r.json();
  r.ok?add('a','AI: '+j.reply):add('e','Error: '+JSON.stringify(j.detail));
};
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return PAGE
