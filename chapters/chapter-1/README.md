# Chapter 1: LangChain + OpenRouter + FastAPI

Git tag: `chapter-1`

## Goal
Set up a Python project with `uv`, connect LangChain to OpenRouter, and expose the model through a FastAPI + Pydantic API with a small web UI.

## What we did
1. **Project setup with uv**: `uv init --bare`, then `uv add langchain langchain-openai python-dotenv fastapi "uvicorn[standard]"`. Dependencies live in `pyproject.toml` and are locked in `uv.lock`.
2. **OpenRouter as the LLM provider**: OpenRouter exposes an OpenAI-compatible API, so `ChatOpenAI` from `langchain-openai` works by pointing `base_url` at `https://openrouter.ai/api/v1` (see `main.py`).
3. **Secrets in `.env`**: `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` are loaded with `python-dotenv`. `.env` is git-ignored; `.env.example` is the committed template with empty values.
4. **FastAPI + Pydantic** (`app.py`):
   - `ChatRequest` validates input: `message` (1 to 4000 chars), `system_prompt`, `temperature` (0 to 2).
   - `ChatResponse` defines the output shape.
   - `POST /chat` calls the model with `llm.ainvoke(...)` and returns the reply. Provider errors become HTTP 502.
5. **Web UI**: a single page served at `/` with a system-prompt box, a temperature slider and a chat log.

## Concepts covered
- `ChatOpenAI` and using any OpenAI-compatible provider
- Messages as `(role, content)` tuples: `system` and `human`
- `.bind(...)` to set per-call parameters such as temperature
- Async invocation (`ainvoke`)
- Pydantic request validation (`Field`, min/max, defaults)
- Never committing API keys

## Run it
```bash
cp .env.example .env        # then add your OpenRouter key
uv run main.py              # one-off call
uv run uvicorn app:app --reload   # API + UI at http://localhost:8000
```

## Files
| File | Purpose |
|---|---|
| `main.py` | Builds the `llm` object |
| `app.py` | FastAPI app, `/chat` endpoint, HTML UI |
| `.env.example` | Template for environment variables |
