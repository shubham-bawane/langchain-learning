# Chapter 3: ReAct Agent with Tools

Git tag: `chapter-3`

## Goal
Move from a single model call to an agent that can decide to use tools, read the results, and keep going until it can answer.

## The ReAct loop
```
Query -> Thinking -> Action (call a tool) -> Observation (tool result) -> Thinking -> ... -> Answer
```
The model reasons about the question, picks a tool and arguments (Action), receives the tool output (Observation), and repeats until it has enough to give the final answer.

## What we did
1. **Agent** (`agent.py`): `create_agent` from `langchain.agents` builds the loop around the OpenRouter model and a list of tools, with a system prompt telling it when to use them.
2. **Tools**: functions decorated with `@tool`. The docstring is what the model reads to decide when to call them.
   - `calculator`: arithmetic through a safe `ast` parser (no `eval`).
   - `current_time`: current UTC time.
   - `word_count`: counts words in text.
   - `web_search`: DuckDuckGo search through the `ddgs` package (no API key).
   - `get_weather`: Open-Meteo geocoding + current weather (no API key), with connection retries.
3. **Steps extraction**: `extract_steps` turns the message history into `action` and `observation` steps plus the final answer, so the UI can show the loop.
4. **API**: `POST /agent` takes `message`, optional `model` and `temperature` (default 0) and returns `{answer, steps}`. The loop is capped with `recursion_limit=12`.
5. **UI**: an "Agent mode" checkbox. When on, each Action and Observation is shown in grey above the answer.
6. **Monitoring carried over**: agent calls go through `MonitoringHandler`, show up in `/metrics`, and are traced in LangSmith as `react-agent` with the tag `chapter-3`.

## Concepts covered
- Agents vs. plain chains: the model chooses the next step
- Tool calling and the `@tool` decorator
- Tool messages and the `AIMessage.tool_calls` / `ToolMessage` history
- Safe tool design (restricted expression evaluator, timeouts, error strings returned to the model)
- Guarding against runaway loops with a recursion limit
- Calling free external APIs from tools

## Try it
Turn on Agent mode and ask:
- `What is (123*45)+7, and how many words are in: the quick brown fox jumps?`
- `Is it warmer in Pune or Tokyo right now?`
- `Search the web for what LangGraph is, in one sentence.`

```bash
uv run uvicorn app:app --reload
curl -s -X POST localhost:8000/agent -H 'Content-Type: application/json' \
  -d '{"message":"Weather in Tokyo?"}'
```
The model must support tool calling (the default `openai/gpt-4o-mini` does).

## Files
| File | Purpose |
|---|---|
| `agent.py` | Tools, `build_agent`, `extract_steps` |
| `app.py` | `/agent` endpoint and Agent mode UI |
| `pyproject.toml` | New dependencies: `httpx`, `ddgs` |

## Ideas for next
Conversation memory, streaming the steps live, custom tools for your own data, a RAG tool over documents.
