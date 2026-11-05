# Chapter 2: Debugging and Monitoring

Git tag: `chapter-2`

## Goal
Make the app observable: see what each request and each LLM call does, how long it takes, what it costs in tokens, and trace it in LangSmith.

## What we did
1. **Logging and metrics** (`observability.py`):
   - Logging is configured once; the level comes from `LOG_LEVEL` (default `INFO`).
   - `Metrics` keeps in-memory counters: requests, errors, LLM calls, input/output tokens, and average and p95 latency over the last 100 calls.
   - It also keeps the last 50 requests and last 50 LLM calls for drill-down.
2. **LangChain callback handler**: `MonitoringHandler` hooks into `on_chat_model_start`, `on_llm_end` and `on_llm_error` to log each model call with latency and token usage (`usage_metadata`).
3. **Request middleware** (`app.py`): gives every request an id (returned in the `X-Request-ID` header), logs method, path, status and duration, and logs a traceback on crashes.
4. **Endpoints**:
   - `GET /health` returns `{"status": "ok"}`.
   - `GET /metrics` returns the counters.
   - `GET /metrics/{name}` returns the rows behind a metric (404 for unknown names).
5. **UI**: each metric is a button; clicking it shows a detail table (newest first). The table refreshes after each message.
6. **LangSmith tracing**: enabled purely through environment variables (`LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`). Calls pass `run_name`, `tags` and `metadata` so traces are easy to filter.
7. **Model dropdown**: `/chat` accepts an optional `model` (validated as `provider/model`). The UI has a dropdown fed by the `MODELS` list in `app.py`.
8. **Token cap**: `max_tokens=1024` in `main.py`. OpenRouter reserves the full output budget, so a large default fails with a 402 when credits are low.

## Concepts covered
- LangChain callbacks (`BaseCallbackHandler`)
- Per-call `config`: `callbacks`, `run_name`, `tags`, `metadata`
- FastAPI middleware and request ids
- Basic application metrics (counters, p95 latency)
- Tracing with LangSmith
- Runtime parameter overrides with `.bind(model=..., temperature=...)`

## Run it
```bash
# add to .env (not .env.example) to enable tracing
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<your key>
LANGSMITH_PROJECT=langchain-learning

uv run uvicorn app:app --reload
LOG_LEVEL=DEBUG uv run uvicorn app:app --reload   # more detail
```
Restart the server after editing `.env`; `--reload` only watches Python files.

## Files
| File | Purpose |
|---|---|
| `observability.py` | Logging, `Metrics`, `MonitoringHandler` |
| `app.py` | Middleware, `/health`, `/metrics`, model dropdown |
| `main.py` | `max_tokens` cap added |
