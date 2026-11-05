# Chapter 4: Memory

## Goal
LLMs are stateless: each call only knows what is in the messages it receives. This chapter adds short-term memory so the app remembers earlier turns of a conversation.

## What we did
1. **Threads**: every conversation has a `thread_id`. Requests with the same id share history; a different id starts fresh. `thread_id` is validated (`^[\w\-]{1,64}$`) and optional. Without it a request is stateless, as before.
2. **Agent memory** (`agent.py`): `create_agent(..., checkpointer=InMemorySaver())`. The checkpointer saves the agent's message state per `thread_id`, including tool calls and results. One shared checkpointer is used so that agents built per request still see the same threads.
3. **Chat memory** (`app.py`): `/chat` has no graph, so it keeps a plain `chat_history` dict per thread and sends `system + history + new message` to the model. History is capped at the last 20 messages (`MAX_HISTORY`) to limit context growth.
4. **Latest-turn steps**: with memory, the agent's message list contains earlier turns. `extract_steps` now only reads from the last human message, so the UI shows only the current turn's Actions and Observations.
5. **UI**: the page generates a thread id per tab and sends it with every request (separate prefixes for chat and agent mode). A **New chat** button creates a new id and clears the log.
6. **Tracing**: the agent passes `thread_id` as run metadata, so LangSmith traces can be filtered by conversation.
7. **Inspecting memory**:
   - `GET /memory` lists all threads with their message counts (agent and chat).
   - `GET /memory/{thread_id}` returns what is stored: role, content, and for the agent also tool calls and tool results.
   - `DELETE /memory/{thread_id}` forgets a thread.
   - The UI has **Memory** (shows the current thread's stored messages as a table, kept up to date after each message) and **Clear memory** buttons.
   - These endpoints are not counted in `/metrics` so viewing memory does not skew the numbers.

## Concepts covered
- Why LLMs need memory to be supplied by the application
- Short-term memory = message history per thread
- Checkpointers (`InMemorySaver`) and `config={"configurable": {"thread_id": ...}}`
- Simple manual history for plain model calls
- Context window growth and trimming history
- Short-term vs long-term memory (stores, covered in theory only)

## Try it
```bash
uv run uvicorn app:app --reload
```
In the UI, with Agent mode on:
1. `My name is Shubham and I live in Pune.`
2. `What is my name and what is the weather where I live?` (uses memory, then the weather tool)
3. Click **New chat** and ask `What is my name?`; it no longer knows.

With `curl`:
```bash
curl -s -X POST localhost:8000/agent -H 'Content-Type: application/json' \
  -d '{"message":"My name is Shubham","thread_id":"t1"}'
curl -s -X POST localhost:8000/agent -H 'Content-Type: application/json' \
  -d '{"message":"What is my name?","thread_id":"t1"}'
```

## Limits
- Memory is in process RAM: it is lost on restart (including `--reload`) and is not shared between server processes. For persistence, use a database checkpointer such as SQLite or Postgres.
- Threads are never deleted, so memory grows. Real apps need expiry.
- The agent thread keeps the full history; for long conversations add trimming or summarisation.
- There is no long-term memory (facts remembered across threads). That needs a LangGraph store.
- `thread_id` comes from the browser and is not authenticated. Do not treat it as a user identity.

## Files
| File | Purpose |
|---|---|
| `agent.py` | `InMemorySaver` checkpointer, latest-turn `extract_steps` |
| `app.py` | `thread_id` on requests, `chat_history`, New chat button |
