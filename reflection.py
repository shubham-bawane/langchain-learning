import operator
from typing import Annotated, Any, AsyncIterator, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from main import llm

GENERATE_PROMPT = (
    "You are a skilled writer. Write the best possible response to the user's request. "
    "If you are given a critique, rewrite your previous draft and address every recommendation. "
    "Output only the new draft."
)
REFLECT_PROMPT = (
    "You are a strict reviewer. Review the draft against the user's request and reply in this format:\n"
    "Critique: <what is wrong or missing>\n"
    "Merits: <what works well>\n"
    "Recommendations: <specific changes>\n"
    "If the draft is already excellent and needs no changes, reply with exactly: APPROVED"
)


class State(TypedDict):
    request: str
    draft: str
    critique: str
    iteration: int  # number of drafts written so far
    max_reflections: int
    trace: Annotated[list[str], operator.add]  # reducer: updates are appended, not replaced


def _model(config: RunnableConfig):
    cfg = config.get("configurable", {})
    return llm.bind(model=cfg.get("model") or llm.model_name, temperature=cfg.get("temperature", 0.7))


async def generate(state: State, config: RunnableConfig) -> dict[str, Any]:
    messages = [("system", GENERATE_PROMPT), ("human", state["request"])]
    if state["critique"]:
        messages += [
            ("ai", state["draft"]),
            ("human", f"Critique of your draft:\n{state['critique']}\n\nRewrite the draft."),
        ]
    result = await _model(config).ainvoke(messages, config=config)
    n = state["iteration"] + 1
    return {"draft": str(result.content), "iteration": n, "trace": [f"generate #{n}"]}


async def reflect(state: State, config: RunnableConfig) -> dict[str, Any]:
    result = await _model(config).ainvoke(
        [("system", REFLECT_PROMPT), ("human", f"Request:\n{state['request']}\n\nDraft:\n{state['draft']}")],
        config=config,
    )
    return {"critique": str(result.content), "trace": [f"reflect #{state['iteration']}"]}


def after_generate(state: State) -> str:
    # N reflections means N+1 drafts: stop once the last allowed rewrite is written.
    return "done" if state["iteration"] > state["max_reflections"] else "reflect"


def is_approved(critique: str) -> bool:
    return critique.strip().upper().startswith("APPROVED")


def after_reflect(state: State) -> str:
    return "done" if is_approved(state["critique"]) else "generate"


def build_graph():
    g = StateGraph(State)
    g.add_node("generate", generate)
    g.add_node("reflect", reflect)
    g.add_edge(START, "generate")
    g.add_conditional_edges("generate", after_generate, {"reflect": "reflect", "done": END})
    g.add_conditional_edges("reflect", after_reflect, {"generate": "generate", "done": END})
    return g.compile()


reflection_graph = build_graph()


async def run_stream(
    request: str, max_reflections: int, model: str | None, temperature: float, callbacks: list[Any]
) -> AsyncIterator[dict[str, Any]]:
    """Run the graph and yield one event per finished node (stream_mode='updates')."""
    state: State = {
        "request": request, "draft": "", "critique": "", "iteration": 0,
        "max_reflections": max_reflections, "trace": [],
    }
    config: RunnableConfig = {
        "callbacks": callbacks,
        "run_name": "reflection-graph",
        "tags": ["chapter-6"],
        "recursion_limit": 25,
        "configurable": {"model": model, "temperature": temperature},
    }
    draft, iteration, approved = "", 0, False
    async for update in reflection_graph.astream(state, config, stream_mode="updates"):
        for node, out in update.items():
            if node == "generate":
                draft, iteration = out["draft"], out["iteration"]
                yield {"type": "draft", "iteration": iteration, "content": draft}
            elif node == "reflect":
                approved = is_approved(out["critique"])
                yield {"type": "critique", "iteration": iteration, "content": out["critique"], "approved": approved}
    yield {
        "type": "final", "content": draft, "drafts": iteration,
        "stopped": "approved" if approved else "max_reflections",
    }
