import asyncio
import json
import operator
import os
from typing import Annotated, Any, AsyncIterator, Literal, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

import sandbox
from main import llm

ANALYZE_PROMPT = (
    "You are a senior engineer. Analyse the programming task. Give the function name (snake_case), its Python "
    "signature, the requirements, and the tricky edge cases. The solution will use only the standard library."
)
TESTS_PROMPT = (
    "You write tests. Given the task and analysis, write 6 to 10 test cases as single-line Python assert "
    "statements that call the function, for example: assert is_palindrome('abba') == True. "
    "Cover normal cases and the edge cases. Use only literals and the function; no imports, no helper code. "
    "Only write an expected value if you can verify it by hand from the task (small inputs, well-known results). "
    "Never guess large computed numbers. For large inputs write property checks instead, for example "
    "assert 0 <= f(10**6) < 1000000007 or assert f(10**5) == f(10**5)."
)
CODE_PROMPT = (
    "You write Python. Implement the function so that it passes all the tests. Rules: standard library only, and "
    "only these modules: " + ", ".join(sorted(sandbox.ALLOWED_IMPORTS)) + ". No file, network or OS access, no "
    "eval/exec/open/input/getattr, no dunder attributes. Return only the code, with no tests and no prints."
)
DIAGNOSE_PROMPT = (
    "You debug. Some tests failed. Decide whether the CODE is wrong or the TESTS are wrong (for example a test "
    "with an incorrect expected value). Work out the correct behaviour from the task, not from the code. "
    "Be suspicious of tests with large expected numbers you cannot verify by hand, and of a test that keeps "
    "failing with the same result after the code was rewritten differently: that usually means the test is wrong. "
    "Answer with verdict code_bug or test_bug and a short explanation with the concrete fix."
)


class Analysis(BaseModel):
    function_name: str = Field(description="snake_case name of the function")
    signature: str = Field(description="The def line, e.g. def f(x: int) -> bool:")
    requirements: list[str]
    edge_cases: list[str]


class Tests(BaseModel):
    asserts: list[str] = Field(description="Single-line assert statements")


class Solution(BaseModel):
    code: str = Field(description="Complete Python source of the solution")


class Diagnosis(BaseModel):
    verdict: Literal["code_bug", "test_bug"]
    explanation: str


class FlowState(TypedDict):
    problem: str
    analysis: dict[str, Any]
    tests: list[str]
    code: str
    results: list[dict[str, Any]]
    problems: list[str]
    verdict: str
    diagnosis: str
    attempts: int  # counts test runs and rejected code; bounds every loop
    max_attempts: int
    log: Annotated[list[dict[str, Any]], operator.add]


def enabled() -> bool:
    """Running generated code is opt-in: set FLOW_ALLOW_CODE_EXEC=true in .env."""
    return os.getenv("FLOW_ALLOW_CODE_EXEC", "").lower() == "true"


def _model(config: RunnableConfig):
    cfg = config.get("configurable", {})
    return llm.model_copy(
        update={"model_name": cfg.get("model") or llm.model_name, "temperature": cfg.get("temperature", 0.2)}
    )


def _structured(config: RunnableConfig, schema: type[BaseModel]):
    return _model(config).with_structured_output(schema, method="function_calling")


def _strip_fences(code: str) -> str:
    code = code.strip()
    if code.startswith("```"):
        code = code.split("\n", 1)[1] if "\n" in code else ""
        code = code.rsplit("```", 1)[0]
    return code.strip()


def _failures(results: list[dict[str, Any]]) -> str:
    return "\n".join(f"- {r['test']}  ->  {r['error']}" for r in results if not r["passed"]) or "(none)"


def _all_passed(state: FlowState) -> bool:
    results = state["results"]
    return bool(results) and len(results) == len(state["tests"]) and all(r["passed"] for r in results)


async def analyze(state: FlowState, config: RunnableConfig) -> dict[str, Any]:
    out = await _structured(config, Analysis).ainvoke(
        [("system", ANALYZE_PROMPT), ("human", state["problem"])], config=config
    )
    data = out.model_dump()
    return {"analysis": data, "log": [{"type": "analysis", **data}]}


async def write_tests(state: FlowState, config: RunnableConfig) -> dict[str, Any]:
    human = f"Task:\n{state['problem']}\n\nAnalysis:\n{json.dumps(state['analysis'])}"
    if state["verdict"] == "test_bug":
        human += (
            "\n\nYour previous tests contained mistakes. Previous tests:\n" + "\n".join(state["tests"])
            + f"\n\nFailures:\n{_failures(state['results'])}\n\nDiagnosis: {state['diagnosis']}\n\nWrite corrected tests."
        )
    out = await _structured(config, Tests).ainvoke([("system", TESTS_PROMPT), ("human", human)], config=config)
    valid: list[str] = []
    rejected: list[dict[str, Any]] = []
    for src in (a.strip() for a in out.asserts[:15]):
        problems = sandbox.validate_assert(src)
        if problems or src in valid:
            rejected.append({"test": src, "why": "; ".join(problems) or "duplicate"})
        else:
            valid.append(src)
    return {"tests": valid, "verdict": "", "log": [{"type": "tests", "tests": valid, "rejected": rejected}]}


async def generate_code(state: FlowState, config: RunnableConfig) -> dict[str, Any]:
    human = (
        f"Task:\n{state['problem']}\n\nAnalysis:\n{json.dumps(state['analysis'])}\n\n"
        "Tests the code must pass:\n" + "\n".join(state["tests"])
    )
    if state["code"]:
        human += f"\n\nYour previous code:\n{state['code']}"
        if state["problems"]:
            human += "\n\nIt was rejected: " + "; ".join(state["problems"])
        if state["results"]:
            human += f"\n\nFailing tests:\n{_failures(state['results'])}"
        if state["diagnosis"]:
            human += f"\n\nDiagnosis: {state['diagnosis']}"
        human += "\n\nReturn a corrected version."
    out = await _structured(config, Solution).ainvoke([("system", CODE_PROMPT), ("human", human)], config=config)
    code = _strip_fences(out.code)
    return {"code": code, "problems": [], "log": [{"type": "code", "code": code, "version": state["attempts"] + 1}]}


async def check_code(state: FlowState, config: RunnableConfig) -> dict[str, Any]:
    problems = sandbox.check_source(state["code"])
    update: dict[str, Any] = {
        "problems": problems, "log": [{"type": "static", "ok": not problems, "problems": problems}],
    }
    if problems:
        update["attempts"] = state["attempts"] + 1
    return update


async def run_tests(state: FlowState, config: RunnableConfig) -> dict[str, Any]:
    if not enabled():
        raise RuntimeError("Code execution is disabled. Set FLOW_ALLOW_CODE_EXEC=true in .env.")
    res = await asyncio.to_thread(sandbox.run_tests, state["code"], state["tests"])
    results = res["results"]
    passed = sum(r["passed"] for r in results)
    entry = {
        "type": "results", "passed": passed, "total": len(results), "results": results,
        "error": res.get("error", ""), "stdout": res.get("stdout", ""),
    }
    return {
        "results": results, "attempts": state["attempts"] + 1, "log": [entry],
        "problems": [res["error"]] if res.get("error") else [],
    }


async def diagnose(state: FlowState, config: RunnableConfig) -> dict[str, Any]:
    human = (
        f"Task:\n{state['problem']}\n\nTests:\n" + "\n".join(state["tests"])
        + f"\n\nCode:\n{state['code']}\n\nFailing tests:\n{_failures(state['results'])}"
        + f"\n\nThis is test run number {state['attempts']}."
    )
    out = await _structured(config, Diagnosis).ainvoke([("system", DIAGNOSE_PROMPT), ("human", human)], config=config)
    return {
        "verdict": out.verdict, "diagnosis": out.explanation,
        "log": [{"type": "diagnosis", "verdict": out.verdict, "explanation": out.explanation}],
    }


def after_tests(state: FlowState) -> str:
    # With no code yet this is the first pass; otherwise the tests were just corrected.
    return "generate_code" if not state["code"] else "run_tests"


def after_check(state: FlowState) -> str:
    if not state["problems"]:
        return "run_tests"
    return "end" if state["attempts"] >= state["max_attempts"] else "generate_code"


def after_run(state: FlowState) -> str:
    if _all_passed(state) or state["attempts"] >= state["max_attempts"]:
        return "end"
    return "diagnose"


def after_diagnose(state: FlowState) -> str:
    return "write_tests" if state["verdict"] == "test_bug" else "generate_code"


def build_graph():
    g = StateGraph(FlowState)
    for name, fn in [
        ("analyze", analyze), ("write_tests", write_tests), ("generate_code", generate_code),
        ("check_code", check_code), ("run_tests", run_tests), ("diagnose", diagnose),
    ]:
        g.add_node(name, fn)
    g.add_edge(START, "analyze")
    g.add_edge("analyze", "write_tests")
    g.add_conditional_edges("write_tests", after_tests, {"generate_code": "generate_code", "run_tests": "run_tests"})
    g.add_edge("generate_code", "check_code")
    g.add_conditional_edges(
        "check_code", after_check, {"run_tests": "run_tests", "generate_code": "generate_code", "end": END}
    )
    g.add_conditional_edges("run_tests", after_run, {"diagnose": "diagnose", "end": END})
    g.add_conditional_edges("diagnose", after_diagnose, {"write_tests": "write_tests", "generate_code": "generate_code"})
    return g.compile()


flow_graph = build_graph()


async def run_stream(
    problem: str, max_attempts: int, model: str | None, temperature: float, callbacks: list[Any]
) -> AsyncIterator[dict[str, Any]]:
    state: FlowState = {
        "problem": problem, "analysis": {}, "tests": [], "code": "", "results": [], "problems": [],
        "verdict": "", "diagnosis": "", "attempts": 0, "max_attempts": max_attempts, "log": [],
    }
    config: RunnableConfig = {
        "callbacks": callbacks, "run_name": "flow-engineering", "tags": ["chapter-6", "flow"],
        "recursion_limit": 40, "configurable": {"model": model, "temperature": temperature},
    }
    code, results, attempts = "", [], 0
    async for update in flow_graph.astream(state, config, stream_mode="updates"):
        for node, out in update.items():
            code = out.get("code", code)
            results = out.get("results", results)
            attempts = out.get("attempts", attempts)
            yield {
                "type": "update", "node": node, "entries": out.get("log", []),
                "attempts": attempts, "max_attempts": max_attempts,
            }
    passed = sum(r["passed"] for r in results)
    yield {
        "type": "final", "status": "passed" if results and passed == len(results) else "failed",
        "code": code, "passed": passed, "total": len(results), "attempts": attempts,
    }
