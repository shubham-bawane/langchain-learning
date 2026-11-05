"""
Website Studio - Parallel Map-Reduce LangGraph workflow.

Generates a single-file, highly interactive `.html` web app
(Tailwind CSS + Alpine.js reactive state + GSAP motion + Lucide icons, all via CDN).

Graph:
    START
      -> requirements_analyst   judges the brief; vague briefs get 3-5 clarifying questions
      -> await_answers          (only if vague) pauses via interrupt() until the client answers
      -> creative_director      archetype, global Alpine state map, 6 section specs
      -> design_architect       fonts, tailwind.config, component recipes, custom CSS
      -> (Send x N) section_builder   one parallel LLM call per section
      -> master_assembler       <head> + <body x-data="appState()"> + JS engine
      -> ast_qa_validator       BeautifulSoup gate; loops back to master_assembler
      -> END

Usage:
    python website_studio_workflow.py "A SaaS for AI-powered invoice automation"
    python website_studio_workflow.py --provider openai --output site.html "..."
    python website_studio_workflow.py --no-clarify "..."   # never ask questions

Programmatic use (what app.py does): `start_studio(...)` runs until the graph finishes
or pauses for answers; `resume_studio(thread_id, answers)` continues a paused run.
"""

import argparse
import json
import operator
import os
import re
import uuid
from pathlib import Path
from typing import Annotated, Any, Callable, Literal, Optional, TypedDict

from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send, interrupt

MAX_TOKENS = int(os.getenv("STUDIO_MAX_TOKENS", "8192"))
MIN_AFFORDABLE_TOKENS = 2048  # below this, section output would be truncated mid-HTML
TOKEN_SAFETY_MARGIN = 64
MAX_QA_RETRIES = 2
OUTPUT_FILE = Path(os.getenv("STUDIO_OUTPUT", "website.html"))


# ============================================================================
# LANGSMITH MONITORING
# ============================================================================

def setup_langsmith() -> bool:
    """Turn on LangSmith tracing when LANGSMITH_API_KEY is set.

    Opt out with LANGSMITH_TRACING=false. Must run before the first traced call, so it is
    invoked at import time (after load_dotenv). LangGraph then traces every node, Send
    branch and LLM call (with token usage) automatically.
    """
    key = (os.getenv("LANGSMITH_API_KEY") or "").strip()
    if not key or key.startswith("your_"):
        print("⚠️ LangSmith: no LANGSMITH_API_KEY set - tracing off (optional)")
        return False
    if os.getenv("LANGSMITH_TRACING", "").strip().lower() in ("false", "0", "no", "off"):
        print("⚠️ LangSmith: disabled by LANGSMITH_TRACING=false (set it to true to monitor runs)")
        return False
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ.setdefault("LANGSMITH_PROJECT", "Website-Studio")
    print(f"✅ LangSmith tracing enabled (project: {os.environ['LANGSMITH_PROJECT']})")
    return True


LANGSMITH_ENABLED = setup_langsmith()


def _log_run_feedback(run_id: uuid.UUID, values: dict, paused: bool) -> None:
    """Attach QA outcome as LangSmith feedback scores so runs can be filtered/charted."""
    if not LANGSMITH_ENABLED:
        return
    try:
        from langchain_core.tracers.langchain import wait_for_all_tracers
        from langsmith import Client

        wait_for_all_tracers()  # the root run must exist before feedback can reference it
        client = Client()
        if paused:
            client.create_feedback(run_id, key="needs_clarification", score=1)
        elif values.get("final_html"):
            errors = values.get("validation_errors") or []
            client.create_feedback(
                run_id, key="qa_passed", score=0 if errors else 1, comment="; ".join(errors)[:500] or None
            )
            client.create_feedback(run_id, key="qa_retries", score=values.get("retry_count", 0))
            client.create_feedback(run_id, key="sections_built", score=len(values.get("completed_sections", [])))
    except Exception as exc:  # monitoring must never break a build
        print(f"⚠️ LangSmith feedback not recorded: {exc}")

MIN_DIRECTIVES = 12
MIN_JS_CHARS = 500
MIN_STRUCTURAL_ELEMENTS = 45
MIN_CLASS_DENSITY = 0.75


# ============================================================================
# STATE
# ============================================================================

class SectionSpec(TypedDict):
    id: str
    name: str
    spatial_layout: str  # e.g. "Bento Grid", "Sticky Split-Screen", "Interactive Dashboard"
    interactive_features: list[str]
    alpine_state_keys: list[str]  # global state variables this section reads/mutates


class CompletedSection(TypedDict):
    id: str
    order: int
    html_fragment: str


class StudioState(TypedDict):
    # Input & clarification
    user_prompt: str
    clarifications: list[dict]
    is_clarified: bool

    # Architecture & creative direction
    app_blueprint: dict
    global_alpine_store: dict  # {"state": {...}, "methods": {...}, "computed": {...}}
    design_system: dict
    section_specs: list[SectionSpec]

    # Parallel map-reduce output (reducer concatenates results from every Send branch)
    completed_sections: Annotated[list[CompletedSection], operator.add]

    # Final assembly & QA
    final_html: str
    validation_errors: list[str]
    retry_count: int
    llm_provider: str


class SectionBuilderInput(TypedDict):
    """Payload of each `Send("section_builder", ...)` branch."""
    section_spec: SectionSpec
    order: int
    app_blueprint: dict
    design_system: dict
    global_alpine_store: dict
    llm_provider: str


# ============================================================================
# LLM CONFIG
# ============================================================================

class _BudgetAwareLLM:
    """Wraps a chat model; if the provider rejects max_tokens as unaffordable (HTTP 402,
    "can only afford N"), lower the shared token ceiling to N and retry once."""

    _ceiling = MAX_TOKENS  # shared so later nodes/parallel sections start at the lowered cap

    def __init__(self, factory: Callable[[int], Any]):
        self._factory = factory
        self._llm = factory(type(self)._ceiling)

    @property
    def token_budget(self) -> int:
        return type(self)._ceiling

    def invoke(self, *args, **kwargs):
        try:
            return self._llm.invoke(*args, **kwargs)
        except Exception as exc:
            match = re.search(r"can only afford (\d+)", str(exc))
            if not match:
                raise
            affordable = int(match.group(1)) - TOKEN_SAFETY_MARGIN
            if affordable < MIN_AFFORDABLE_TOKENS:
                raise RuntimeError(
                    f"Your LLM account can only afford ~{affordable} "
                    f"output tokens per request, too few to generate a page section. Add credits, raise the key's "
                    f"limit, or set a cheaper OPENROUTER_MODEL (e.g. openai/gpt-4o-mini)."
                ) from exc
            if affordable < type(self)._ceiling:
                type(self)._ceiling = affordable
                print(f"⚠️ Credits limit max_tokens to {affordable} (wanted {MAX_TOKENS}); output may be shorter.")
            self._llm = self._factory(type(self)._ceiling)
            return self._llm.invoke(*args, **kwargs)


class LLMConfig:
    """LLM provider selection. Clients use max_tokens=8192 (override: STUDIO_MAX_TOKENS),
    lowered automatically if the provider reports the account can't afford that many."""

    @staticmethod
    def get_default_provider() -> str:
        if os.getenv("OPENROUTER_API_KEY"):
            return "openrouter"
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        if os.getenv("ANTHROPIC_API_KEY"):
            return "anthropic"
        raise ValueError("No LLM API key configured (OPENROUTER_API_KEY, OPENAI_API_KEY or ANTHROPIC_API_KEY)")

    @staticmethod
    def get_llm(provider: Optional[str] = None, temperature: float = 0.7, model_override: Optional[str] = None):
        provider = provider or LLMConfig.get_default_provider()
        api_key = os.getenv(f"{provider.upper()}_API_KEY")
        if not api_key:
            raise ValueError(f"API key for {provider} not found")

        if provider == "openrouter":
            return _BudgetAwareLLM(
                lambda max_tokens: ChatOpenAI(
                    model=model_override or os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-5.5"),
                    api_key=api_key,
                    base_url="https://openrouter.ai/api/v1",
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
        if provider == "openai":
            return _BudgetAwareLLM(
                lambda max_tokens: ChatOpenAI(
                    model=model_override or "gpt-4-turbo",
                    api_key=api_key,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=model_override or "claude-3-opus-20240229",
                api_key=api_key,
                temperature=temperature,
                max_tokens=MAX_TOKENS,
            )
        raise ValueError(f"Unknown provider: {provider}")


# ============================================================================
# HELPERS
# ============================================================================

def _strip_code_fences(text: Any) -> str:
    """Remove markdown fence lines (``` / ```html / ```js) anywhere in model output."""
    if isinstance(text, list):  # content blocks
        text = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in text)
    text = re.sub(r"^[ \t]*```[a-zA-Z]*[ \t]*$", "", str(text or ""), flags=re.M)
    return text.strip()


def _parse_json(text: Any) -> dict:
    """Parse model JSON, tolerating fences, surrounding prose and raw newlines in strings."""
    cleaned = _strip_code_fences(text)
    try:
        return json.loads(cleaned, strict=False)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(cleaned[start : end + 1], strict=False)


def _was_truncated(message: Any) -> bool:
    """True if the provider stopped because the output token limit was hit."""
    meta = getattr(message, "response_metadata", None) or {}
    return meta.get("finish_reason") == "length" or meta.get("stop_reason") == "max_tokens"


def _invoke_json(llm, system: str, human: str, attempts: int = 3) -> dict:
    """Invoke the LLM and parse JSON; retries tell the model *why* the last reply failed."""
    budget = getattr(llm, "token_budget", MAX_TOKENS)
    base = (
        f"{human}\n\nOUTPUT LIMIT: at most ~{budget} tokens in total. Emit COMPACT minified JSON "
        "(no indentation or blank lines). Inside JSON strings never use double quotes - use single "
        "quotes (e.g. in CSS or HTML) - and never put raw line breaks."
    )
    last_err: Optional[Exception] = None
    prompt = base
    for _ in range(attempts):
        message = llm.invoke([("system", system), ("human", prompt)])
        try:
            return _parse_json(message.content)
        except json.JSONDecodeError as exc:
            last_err = exc
            if _was_truncated(message):
                prompt = (
                    base + "\n\nYour previous reply was CUT OFF by the output limit. Return the complete JSON again, "
                    "much shorter: fewer items in every list/map, shorter strings, no optional detail."
                )
            else:
                prompt = base + (
                    f"\n\nYour previous reply was not valid JSON ({exc}). Return the complete, valid JSON "
                    "again; escape or avoid double quotes inside strings."
                )
    raise ValueError(f"LLM did not return valid JSON after {attempts} attempts: {last_err}")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "section"


def _js_safe(text: str) -> str:
    """Prevent a `</script>` sequence inside inline script content."""
    return re.sub(r"</(script)", r"<\\/\1", text, flags=re.I)


def _clean_fragment(text: Any) -> str:
    """Reduce model output to a body fragment: no doc wrapper, no <script> tags."""
    html = _strip_code_fences(text)
    body = re.search(r"<body[^>]*>(.*)</body>", html, flags=re.S | re.I)
    if body:
        html = body.group(1)
    html = re.sub(r"<!doctype[^>]*>", "", html, flags=re.I)
    html = re.sub(r"</?(html|head|body)[^>]*>", "", html, flags=re.I)
    html = re.sub(r"<script\b.*?</script>", "", html, flags=re.S | re.I)
    return html.strip()


# Words that are not state identifiers when scanning Alpine expressions.
_JS_RESERVED = {
    "true", "false", "null", "undefined", "this", "new", "typeof", "in", "of", "if", "else",
    "return", "function", "let", "const", "var", "window", "document", "console", "Math", "Date",
    "JSON", "Object", "Array", "Number", "String", "Boolean", "parseInt", "parseFloat", "isNaN",
    "event", "navigator", "localStorage", "setTimeout", "clearTimeout", "Intl", "gsap", "lucide",
}
_EXPR_ATTR_PREFIXES = ("x-show", "x-text", "x-html", "x-model", "x-if", "x-for", "x-effect",
                       "x-init", "x-bind", "x-on", "@", ":")


def _alpine_identifiers(html: str) -> list[str]:
    """Identifiers used by Alpine expressions that must be provided by appState()."""
    soup = BeautifulSoup(html, "html.parser")
    local_scope: set[str] = set()
    for tag in soup.find_all(attrs={"x-data": True}):
        local_scope.update(re.findall(r"[A-Za-z_$][\w$]*", str(tag.get("x-data"))))

    used: set[str] = set()
    for tag in soup.find_all(True):
        for name, value in tag.attrs.items():
            if name.startswith("x-transition") or not name.startswith(_EXPR_ATTR_PREFIXES):
                continue
            expr = " ".join(value) if isinstance(value, list) else str(value)
            if name == "x-for":
                loop = re.match(r"\s*\(?([\w\s,$]+?)\)?\s+(?:in|of)\s+(.+)", expr, flags=re.S)
                if loop:
                    local_scope.update(re.findall(r"[A-Za-z_$][\w$]*", loop.group(1)))
                    expr = loop.group(2)
            expr = re.sub(r"'[^']*'|\"[^\"]*\"|`[^`]*`", "", expr)
            used.update(re.findall(r"(?<![\w$.])([A-Za-z_$][\w$]*)", expr))

    names = {n for n in used - local_scope - _JS_RESERVED if not n.startswith("$")}
    return sorted(names)[:80]


# ============================================================================
# NODES 0a/0b: REQUIREMENTS ANALYST + HUMAN-IN-THE-LOOP PAUSE
# ============================================================================

MAX_QUESTIONS = 5

REQUIREMENTS_ANALYST_PROMPT = f"""You are an Account Manager at a web agency. Decide whether the client's brief has enough detail to design a distinctive, on-brand website.

A brief is CLEAR when it states most of: what the business sells/does, who the audience is, the brand name or tone/style, and the key features or goals. Short one-liners such as "build a website for my mushroom business" are NOT clear.

If NOT clear, ask 3-{MAX_QUESTIONS} concise, high-impact questions (business offering and products, target audience, brand name + style/mood, must-have interactive features, goal such as selling online vs. leads). Give each question 2-4 short `suggestions` to make answering easy.
If clear, return no questions.

Respond with RAW JSON ONLY:
{{"is_clear": true, "questions": [{{"question": "", "suggestions": [""]}}]}}"""


def _format_qa(clarifications: list[dict]) -> str:
    lines = []
    for c in clarifications:
        answer = (c.get("answer") or "").strip() or "(no answer - use your best judgement)"
        lines.append(f"Q: {c.get('question', '')}\nA: {answer}")
    return "\n".join(lines)


def format_question(c: dict) -> str:
    """Human-readable question text, with suggestions appended."""
    suggestions = [str(s) for s in c.get("suggestions") or []]
    return f"{c['question']} (e.g. {' / '.join(suggestions)})" if suggestions else c["question"]


def requirements_analyst_node(state: StudioState) -> dict:
    if state.get("is_clarified"):  # revisions / --no-clarify / already answered
        return {}
    print("🧐 Requirements Analyst: checking the brief...")
    llm = LLMConfig.get_llm(state.get("llm_provider"), temperature=0.2)
    result = _invoke_json(llm, REQUIREMENTS_ANALYST_PROMPT, f"Client brief:\n{state['user_prompt']}")

    questions = [
        {
            "question": str(q.get("question", "")).strip(),
            "suggestions": [str(s) for s in (q.get("suggestions") or [])][:4],
            "answer": "",
        }
        for q in (result.get("questions") or [])
        if isinstance(q, dict) and str(q.get("question", "")).strip()
    ][:MAX_QUESTIONS]

    needs_questions = not result.get("is_clear", False) and bool(questions)
    return {"clarifications": questions if needs_questions else [], "is_clarified": not needs_questions}


def _merge_answers(clarifications: list[dict], raw: Any) -> list[dict]:
    """Apply client answers (list of strings, or one free-text reply) to the questions."""
    merged = [dict(c) for c in clarifications]
    if isinstance(raw, (list, tuple)):
        for c, answer in zip(merged, raw):
            c["answer"] = str(answer or "").strip()
        return merged

    text = str(raw or "").strip()
    if not text:
        return merged

    # "1. answer\n2. answer" style replies map to their questions; anything else is free text.
    parts = re.split(r"(?m)^\s*(\d+)\s*[.):\-]\s*", text)
    numbered = {int(n): a.strip() for n, a in zip(parts[1::2], parts[2::2]) if 1 <= int(n) <= len(merged)}
    if numbered:
        for n, answer in numbered.items():
            merged[n - 1]["answer"] = answer
    else:
        merged.append({"question": "Client's reply (free text)", "suggestions": [], "answer": text})
    return merged


def await_answers_node(state: StudioState) -> dict:
    """Pause the graph until the client answers (resume with Command(resume=answers))."""
    questions = [format_question(c) for c in state["clarifications"]]
    answers = interrupt({"questions": questions})
    return {"clarifications": _merge_answers(state["clarifications"], answers), "is_clarified": True}


def route_after_analyst(state: StudioState) -> Literal["await_answers", "creative_director"]:
    return "creative_director" if state.get("is_clarified") else "await_answers"


# ============================================================================
# NODE 1: CREATIVE DIRECTOR
# ============================================================================

ARCHETYPES = [
    "Linear-style Dark Atmospheric UI",
    "Neo-Brutalist Swiss Grid",
    "Apple-style Bento Showcase",
    "Editorial Luxury",
    "Interactive SaaS Command Center",
]

CREATIVE_DIRECTOR_PROMPT = f"""You are a Creative Director and Lead Solutions Architect for an elite web agency.
From the client's brief, plan a complex, highly interactive single-page web application.

1. Pick ONE high-craft visual archetype that fits the brief (not always the first): {", ".join(ARCHETYPES)}.
2. Honour the client's answers to the clarifying questions (provided with the brief); an unanswered question means "designer's choice". Record every remaining guess you make for details the client never specified as a short string in `assumptions`.
3. Design the GLOBAL REACTIVE STATE MAP (`global_alpine_store`) - real data models for one Alpine.js root `appState()`:
   - `state`: key -> realistic initial value (e.g. activeTab, pricingAnnual, roiSliderValue, modalOpen, cmdOpen, mobileMenuOpen, toastMessage, filterCategory, searchQuery, cartItems, faqOpen, themeMode). Include the real data arrays/objects the sections will render (plans, features, products, testimonials, faqs) but keep each to 3-4 short items.
   - `methods`: name -> one-line description of behaviour (e.g. showToast, toggleTheme, openCmd, addToCart).
   - `computed`: name -> one-line description (e.g. filteredItems, monthlyPrice, roiResult, cartTotal).
4. Break the site into EXACTLY 6 distinct `section_specs`, in page order:
   1. Floating Command Navbar + Mobile Drawer + Cmd+K command palette modal
   2. Hero with a Live Interactive Preview Widget
   3. Asymmetric Bento Feature Grid with hover micro-interactions
   4. Interactive Playground / Live Calculator / Filterable Showcase
   5. Social Proof marquee + Interactive Comparison Table
   6. Interactive FAQ Accordion + Newsletter signup with Toast + Rich Footer
   Adapt names/content to the brief, but keep this interactive intent. Each spec has:
   `id` (kebab-case), `name`, `spatial_layout`, `interactive_features` (3-5 concrete behaviours), `alpine_state_keys` (keys from `global_alpine_store.state` it reads or mutates).

Respond with RAW JSON ONLY (no prose, no fences):
{{
  "assumptions": ["..."],
  "app_blueprint": {{"project_name": "", "tagline": "", "industry": "", "target_persona": "", "archetype": "", "tone": "", "layout_principles": "", "copy_notes": ""}},
  "global_alpine_store": {{"state": {{}}, "methods": {{}}, "computed": {{}}}},
  "section_specs": [{{"id": "", "name": "", "spatial_layout": "", "interactive_features": [""], "alpine_state_keys": [""]}}]
}}"""


def creative_director_node(state: StudioState) -> dict:
    print("🎬 Creative Director: choosing archetype, state map and section specs...")
    llm = LLMConfig.get_llm(state.get("llm_provider"), temperature=0.9)
    human = f"Client brief:\n{state['user_prompt']}"
    qa = _format_qa(state.get("clarifications", []))
    if qa:
        human += f"\n\nClarifying questions and the client's answers:\n{qa}"
    result = _invoke_json(llm, CREATIVE_DIRECTOR_PROMPT, human)

    raw_specs = result.get("section_specs") or []
    if len(raw_specs) < 5:
        raise ValueError(f"Creative director returned {len(raw_specs)} sections; expected 6.")

    store = result.get("global_alpine_store") or {}
    store.setdefault("state", {})
    store.setdefault("methods", {})
    store.setdefault("computed", {})

    specs: list[SectionSpec] = []
    seen: set[str] = set()
    for i, raw in enumerate(raw_specs[:7]):
        sid = _slug(raw.get("id") or raw.get("name") or f"section-{i + 1}")
        if sid in seen:
            sid = f"{sid}-{i + 1}"
        seen.add(sid)
        specs.append(
            SectionSpec(
                id=sid,
                name=raw.get("name", sid),
                spatial_layout=raw.get("spatial_layout", "Asymmetric Grid"),
                interactive_features=list(raw.get("interactive_features") or []),
                alpine_state_keys=list(raw.get("alpine_state_keys") or []),
            )
        )

    blueprint = result.get("app_blueprint", {})
    blueprint["assumptions"] = list(result.get("assumptions") or [])

    return {
        "is_clarified": True,
        "app_blueprint": blueprint,
        "global_alpine_store": store,
        "section_specs": specs,
        "completed_sections": [],
        "validation_errors": [],
        "retry_count": 0,
    }


# ============================================================================
# NODE 2: DESIGN ARCHITECT
# ============================================================================

DESIGN_ARCHITECT_PROMPT = """You are a Staff Design Systems Engineer. Produce the design tokens for the site described below.

Rules:
- Font pairing must be bespoke and match the archetype. NEVER use Inter, Roboto, Arial or system fonts for headings. Use real Google Fonts names.
- `tailwind_config` is the object placed under `theme.extend`. Keep it COMPACT: custom `colors` with ONLY the shades 100, 300, 500, 700, 900 for brand and accent plus a few surface/ink tokens, `fontFamily` (heading/body/mono), 2-3 `boxShadow` entries (glow, hard-offset), and 4-5 `animation` entries with matching `keyframes` (float, marquee, shimmer, fade-up, pulse-glow).
- `component_recipes`: reusable, multi-class Tailwind strings using ONLY the tokens above. Required keys: glass_surface, glow_border, btn_primary, btn_secondary, btn_ghost, input, badge, card, heading_xl, heading_lg, eyebrow, link.
- `custom_css`: compact raw CSS (no <style> tags), written with SINGLE quotes only, covering: mesh gradient background, noise texture, custom scrollbar, selection colour, marquee helper, smooth scrolling, `.reveal` initial state (opacity 0, translateY) with `.reveal.is-visible` final state, and `[x-cloak] { display: none !important; }`.
- `body_classes`: Tailwind classes for <body> (background, text colour, font-body, antialiased).

Respond with RAW JSON ONLY:
{
  "fonts": {"heading": "", "body": "", "mono": ""},
  "google_fonts_url": "https://fonts.googleapis.com/css2?family=...&display=swap",
  "tailwind_config": {},
  "component_recipes": {},
  "custom_css": "",
  "body_classes": ""
}"""


def _google_fonts_href(design: dict) -> str:
    url = str(design.get("google_fonts_url") or "")
    if url.startswith("https://fonts.googleapis.com/"):
        return url
    families = {f for f in (design.get("fonts") or {}).values() if f}
    query = "&".join(f"family={f.replace(' ', '+')}:wght@400;500;600;700" for f in sorted(families))
    return f"https://fonts.googleapis.com/css2?{query}&display=swap" if query else ""


def design_architect_node(state: StudioState) -> dict:
    print("🎨 Design Architect: generating tokens, tailwind.config and CSS...")
    llm = LLMConfig.get_llm(state.get("llm_provider"), temperature=0.8)
    human = (
        f"Client brief:\n{state['user_prompt']}\n\n"
        f"app_blueprint:\n{json.dumps(state.get('app_blueprint', {}), indent=2)}"
    )
    design = _invoke_json(llm, DESIGN_ARCHITECT_PROMPT, human)

    design["google_fonts_url"] = _google_fonts_href(design)
    design.setdefault("tailwind_config", {})
    design.setdefault("component_recipes", {})
    design.setdefault("body_classes", "bg-neutral-950 text-neutral-100 font-body antialiased")
    css = str(design.get("custom_css") or "")
    if "[x-cloak]" not in css:
        css += "\n[x-cloak] { display: none !important; }"
    design["custom_css"] = css
    return {"design_system": design}


# ============================================================================
# MAP: fan-out one section_builder per spec (LangGraph Send API)
# ============================================================================

def map_sections(state: StudioState) -> list[Send]:
    return [
        Send(
            "section_builder",
            SectionBuilderInput(
                section_spec=spec,
                order=index,
                app_blueprint=state.get("app_blueprint", {}),
                design_system=state["design_system"],
                global_alpine_store=state["global_alpine_store"],
                llm_provider=state.get("llm_provider", ""),
            ),
        )
        for index, spec in enumerate(state["section_specs"])
    ]


# ============================================================================
# NODE 3: SECTION BUILDER (parallel worker)
# ============================================================================

SECTION_BUILDER_PROMPT = """You are a Senior UI Component Developer. Build ONE section of a larger Tailwind CSS + Alpine.js single-page app. Other developers build the other sections in parallel; a separate assembler wires <head> and the JavaScript.

OUTPUT: a raw HTML fragment of 150-250 lines. No markdown fences, no <html>/<head>/<body>, NO <script> tags (they are stripped), no prose.

RULES:
1. The root element has `id="<section id>"` (e.g. <section id="pricing">, or <header> for the navbar) and uses the section's `spatial_layout`.
2. Alpine.js v3 is already mounted on <body x-data="appState()">. Your markup inherits that scope. Read/mutate ONLY the global state keys, methods and computed names from `global_alpine_store`; never invent new global names and never redeclare them. Purely local UI state may use a small local `x-data="{ ... }"`.
3. Make it genuinely interactive with real directives on real elements: `@click`, `x-on:`, `x-show` + `x-transition`, `:class` / `x-bind:class`, `x-model`, `x-text`, `x-for` (only on <template>), `x-if`. Implement every item in `interactive_features` visibly and functionally. Add `x-cloak` to anything hidden initially.
4. Use the design system ONLY: custom colour/font/shadow tokens from `tailwind_config`, and paste the `component_recipes` class strings into buttons, inputs, badges, cards and surfaces. Every div/section/button/input needs 3+ Tailwind classes - no skeleton or unstyled elements.
5. High density: realistic copy and data (names, prices, metrics - no lorem ipsum), inline SVG illustrations/graphs, hover/focus/active micro-interactions, group-hover effects, tooltips, focus rings, responsive breakpoints (sm/md/lg), aria attributes (aria-expanded, aria-controls, role, aria-label).
6. Icons: `<i data-lucide="icon-name" class="w-5 h-5"></i>`. Images: real Unsplash URLs (https://images.unsplash.com/photo-...?auto=format&fit=crop&w=1200&q=80) with alt text and loading="lazy".
7. Add the class `reveal` to major blocks for scroll-reveal (handled by the assembler).
8. Section-specific: navbar = sticky/floating, desktop links, mobile drawer toggled by global state, and a Cmd+K command palette modal (search input filtering items). Footer/FAQ section = accordion, newsletter form with validation that calls the toast method, and a rich multi-column footer."""


def section_builder_node(payload: SectionBuilderInput) -> dict:
    spec = payload["section_spec"]
    print(f"🧱 Section Builder [{payload['order'] + 1}]: {spec['name']}")
    llm = LLMConfig.get_llm(payload.get("llm_provider") or None, temperature=0.7)

    design = payload["design_system"]
    human = (
        f"Section spec:\n{json.dumps(spec, indent=2)}\n\n"
        f"Section position: {payload['order'] + 1} of the page\n\n"
        f"app_blueprint:\n{json.dumps(payload.get('app_blueprint', {}), indent=2)}\n\n"
        f"global_alpine_store:\n{json.dumps(payload['global_alpine_store'], indent=2)}\n\n"
        f"tailwind_config (theme.extend):\n{json.dumps(design.get('tailwind_config', {}), indent=2)}\n\n"
        f"component_recipes:\n{json.dumps(design.get('component_recipes', {}), indent=2)}\n\n"
        f"fonts: {json.dumps(design.get('fonts', {}))}"
    )

    html = _clean_fragment(llm.invoke([("system", SECTION_BUILDER_PROMPT), ("human", human)]).content)
    if len(html) < 1500:  # truncated/refused output: ask once more
        html = _clean_fragment(
            llm.invoke(
                [("system", SECTION_BUILDER_PROMPT), ("human", human + "\n\nYour previous output was far too short. Write the FULL 150-250 line section.")]
            ).content
        )
    if not html:
        raise ValueError(f"Section '{spec['id']}' produced no HTML")

    return {"completed_sections": [CompletedSection(id=spec["id"], order=payload["order"], html_fragment=html)]}


# ============================================================================
# NODE 4: MASTER ASSEMBLER
# ============================================================================

ASSEMBLER_PROMPT = """You are a Principal Frontend Architect and Creative Technologist. The page markup is already assembled from section fragments inside <body x-data="appState()">. Write the JavaScript engine that makes it work.

OUTPUT FORMAT (exact markers, no fences, no <script> tags, no prose):
===SCRIPT===
function appState() {
  return { ... }
}
// other helpers (IntersectionObserver reveal, keyboard shortcuts) ...
===EXTRA_HTML===
(optional HTML appended after the sections, e.g. a toast region or an element the markup/script needs but is missing; leave empty if nothing is missing)

REQUIREMENTS for `function appState()`:
- Returns an object containing EVERY key in `global_alpine_store.state` with realistic initial values (arrays/objects fully populated with the real data the markup renders), EVERY method in `methods` fully implemented, and every `computed` entry as a JS getter (`get filteredItems() { ... }`).
- Every identifier in `markup_identifiers` MUST be defined on the returned object (unless it is clearly an x-for alias).
- Include `init()`: starts IntersectionObserver scroll-reveal (add class `is-visible` to `.reveal`), a passive `window.addEventListener('scroll')` handler for a `scrolled` flag (declare it in state), keyboard shortcuts (Cmd/Ctrl+K opens the command palette, `Escape` closes modals/drawers/palette), and `this.$nextTick(() => window.lucide && lucide.createIcons())`.
- `showToast(message)` sets the toast state and auto-dismisses with setTimeout. Persist the theme choice in localStorage if a theme key exists. Animate numbers (ROI/price/metrics) with `window.gsap` when available, falling back to plain assignment.
- Use gsap defensively (`if (window.gsap)`). Plain modern JavaScript only, no imports. Real logic, no TODOs or placeholders.

If `validation_errors` and the previous script are provided, FIX exactly those problems (missing bindings, undefined identifiers, missing elements) and return the complete corrected SCRIPT and EXTRA_HTML."""

_SCRIPT_RE = re.compile(r'<script id="app-state-script">(.*?)</script>', re.S)
_EXTRA_RE = re.compile(r"<!-- studio:extra-html -->(.*?)<!-- /studio:extra-html -->", re.S)


def _split_assembler_output(text: Any) -> tuple[str, str]:
    raw = _strip_code_fences(text)
    extra = ""
    marker = re.search(r"===EXTRA_HTML===", raw)
    if marker:
        extra, raw = raw[marker.end():], raw[: marker.start()]
    script = re.sub(r"^\s*===SCRIPT===", "", raw)
    script = re.sub(r"</?script[^>]*>", "", script, flags=re.I).strip()
    return script, _clean_fragment(extra)


def _render_document(state: StudioState, sections_html: str, extra_html: str, script: str) -> str:
    design = state["design_system"]
    cfg = design.get("tailwind_config") or {}
    if "theme" in cfg:
        cfg = (cfg["theme"] or {}).get("extend", cfg["theme"])
    tailwind_config = _js_safe(json.dumps({"theme": {"extend": cfg}}, indent=2))

    fonts = _google_fonts_href(design)
    font_tags = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'  <link href="{fonts}" rel="stylesheet">'
        if fonts
        else ""
    )
    blueprint = state.get("app_blueprint", {})
    title = f"{blueprint.get('project_name', 'Website')} - {blueprint.get('tagline', '')}".strip(" -")
    description = str(blueprint.get("tagline") or blueprint.get("industry") or "").replace('"', "&quot;")

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>tailwind.config = {tailwind_config}</script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
  {font_tags}
  <style>
{_js_safe(design.get("custom_css", ""))}
  </style>
</head>
<body x-data="appState()" class="{design.get("body_classes", "")}">
{sections_html}
<!-- studio:extra-html -->
{extra_html}
<!-- /studio:extra-html -->
<script id="app-state-script">
{_js_safe(script)}
</script>
<script id="studio-bootstrap">
(function () {{
  var pending = false;
  function icons() {{ if (window.lucide) lucide.createIcons(); }}
  document.addEventListener('alpine:initialized', icons);
  window.addEventListener('load', icons);
  new MutationObserver(function () {{
    if (pending) return;
    pending = true;
    requestAnimationFrame(function () {{ pending = false; icons(); }});
  }}).observe(document.body, {{ childList: true, subtree: true }});
}})();
</script>
</body>
</html>
"""


def master_assembler_node(state: StudioState) -> dict:
    attempt = state.get("retry_count", 0)
    print(f"🛠️  Master Assembler: wiring document{f' (fix pass {attempt})' if attempt else ''}...")
    sections = sorted(state.get("completed_sections", []), key=lambda s: s["order"])
    if not sections:
        raise ValueError("No completed sections to assemble")
    sections_html = "\n\n".join(s["html_fragment"] for s in sections)

    llm = LLMConfig.get_llm(state.get("llm_provider"), temperature=0.3)
    human = (
        f"app_blueprint:\n{json.dumps(state.get('app_blueprint', {}), indent=2)}\n\n"
        f"global_alpine_store:\n{json.dumps(state['global_alpine_store'], indent=2)}\n\n"
        f"section_specs:\n{json.dumps(state['section_specs'], indent=2)}\n\n"
        f"markup_identifiers (used by Alpine expressions in the markup):\n{json.dumps(_alpine_identifiers(sections_html))}"
    )

    errors = state.get("validation_errors") or []
    previous = state.get("final_html", "")
    if errors and previous:
        prev_script = _SCRIPT_RE.search(previous)
        prev_extra = _EXTRA_RE.search(previous)
        human += (
            "\n\nvalidation_errors (fix ALL):\n" + "\n".join(f"- {e}" for e in errors)
            + f"\n\nprevious SCRIPT:\n{prev_script.group(1).strip() if prev_script else '(none)'}"
            + f"\n\nprevious EXTRA_HTML:\n{prev_extra.group(1).strip() if prev_extra else '(none)'}"
        )

    script, extra_html = _split_assembler_output(llm.invoke([("system", ASSEMBLER_PROMPT), ("human", human)]).content)
    return {"final_html": _render_document(state, sections_html, extra_html, script)}


# ============================================================================
# NODE 5: AST QA VALIDATOR
# ============================================================================

STRUCTURAL_TAGS = ["div", "section", "button", "nav", "header", "footer", "article", "aside", "form", "input"]
DIRECTIVE_PREFIXES = ("x-on:", "@", "x-show", "x-model", "x-bind:", ":", "x-transition")


def run_qa_checks(html: str) -> list[str]:
    """Deterministic structure + interactivity checks. Returns a list of error strings."""
    errors: list[str] = []
    soup = BeautifulSoup(html, "html.parser")
    head = soup.head
    if head is None:
        return ["Missing <head>."]

    # 1. CDN + tailwind.config in <head>
    srcs = [s.get("src") or "" for s in head.find_all("script")]
    if not any("cdn.tailwindcss.com" in s for s in srcs):
        errors.append("Missing Tailwind CDN script in <head>.")
    if not any("alpinejs" in s for s in srcs):
        errors.append("Missing Alpine.js CDN script in <head>.")
    if not any("lucide" in s for s in srcs):
        errors.append("Missing Lucide CDN script in <head>.")
    if not any("tailwind.config" in s.get_text() for s in head.find_all("script") if not s.get("src")):
        errors.append("Missing tailwind.config script in <head>.")

    body = soup.body
    if body is None:
        return errors + ["Missing <body>."]

    # 2. Alpine root + directive count
    has_root = body.has_attr("x-data") or any(t.has_attr("x-data") for t in body.find_all(True, recursive=True))
    if not has_root:
        errors.append("Missing x-data on <body> or a root container.")
    directives = sum(1 for t in soup.find_all(True) for a in t.attrs if a.startswith(DIRECTIVE_PREFIXES))
    if directives < MIN_DIRECTIVES:
        errors.append(
            f"Only {directives} interactive Alpine directives found (need >= {MIN_DIRECTIVES}). "
            "Add real @click, x-show, x-model, :class and x-transition bindings."
        )

    # 3. Real JS logic (ignore tailwind.config and the Lucide bootstrap)
    js = "\n".join(
        s.get_text()
        for s in soup.find_all("script")
        if not s.get("src") and s.get("id") != "studio-bootstrap" and "tailwind.config" not in s.get_text()
    )
    js = re.sub(r"lucide\.createIcons\(\s*\)\s*;?", "", js).strip()
    has_logic = any(k in js for k in ("function appState", "Alpine.data", "addEventListener"))
    if len(js) <= MIN_JS_CHARS or not has_logic:
        errors.append(
            f"Missing real JavaScript logic: need function appState/Alpine.data/addEventListener "
            f"with > {MIN_JS_CHARS} characters (found {len(js)})."
        )
    elif "appState(" in str(body.get("x-data", "")) and "appState" not in js:
        errors.append("<body x-data=\"appState()\"> is used but appState() is not defined in any <script>.")

    # 4. DOM richness
    structural = soup.find_all(STRUCTURAL_TAGS)
    if len(structural) < MIN_STRUCTURAL_ELEMENTS:
        errors.append(f"HTML too sparse: {len(structural)} structural elements (need >= {MIN_STRUCTURAL_ELEMENTS}).")
    if structural:
        density = sum(1 for t in structural if len(t.get("class", [])) >= 3) / len(structural)
        if density <= MIN_CLASS_DENSITY:
            errors.append(
                f"Low Tailwind class density: {density:.0%} of structural elements have 3+ classes (need > {MIN_CLASS_DENSITY:.0%})."
            )

    return errors


def ast_qa_validator_node(state: StudioState) -> dict:
    html = state.get("final_html", "")
    errors = run_qa_checks(html)
    retry_count = state.get("retry_count", 0)

    if errors:
        retry_count += 1
        print(f"❌ QA failed (attempt {retry_count}): " + " | ".join(errors))
    else:
        print("✅ QA passed")

    # Persist the passing result, or the best effort once retries are exhausted.
    if not errors or retry_count > MAX_QA_RETRIES:
        OUTPUT_FILE.write_text(html, encoding="utf-8")
        print(f"💾 Wrote {OUTPUT_FILE}")

    return {"validation_errors": errors, "retry_count": retry_count}


def qa_decision(state: StudioState) -> Literal["master_assembler", "__end__"]:
    if state.get("validation_errors") and state.get("retry_count", 0) <= MAX_QA_RETRIES:
        return "master_assembler"
    return END


# ============================================================================
# GRAPH
# ============================================================================

def build_studio_workflow(checkpointer=None):
    graph = StateGraph(StudioState)
    graph.add_node("requirements_analyst", requirements_analyst_node)
    graph.add_node("await_answers", await_answers_node)
    graph.add_node("creative_director", creative_director_node)
    graph.add_node("design_architect", design_architect_node)
    graph.add_node("section_builder", section_builder_node)
    graph.add_node("master_assembler", master_assembler_node)
    graph.add_node("ast_qa_validator", ast_qa_validator_node)

    graph.add_edge(START, "requirements_analyst")
    graph.add_conditional_edges(
        "requirements_analyst",
        route_after_analyst,
        {"await_answers": "await_answers", "creative_director": "creative_director"},
    )
    graph.add_edge("await_answers", "creative_director")
    graph.add_edge("creative_director", "design_architect")
    # Fan-out: one parallel section_builder per spec; the fan-in edge waits for all of them.
    graph.add_conditional_edges("design_architect", map_sections, ["section_builder"])
    graph.add_edge("section_builder", "master_assembler")
    graph.add_edge("master_assembler", "ast_qa_validator")
    graph.add_conditional_edges(
        "ast_qa_validator", qa_decision, {"master_assembler": "master_assembler", END: END}
    )
    # interrupt() needs a checkpointer to persist the paused run.
    return graph.compile(checkpointer=checkpointer or MemorySaver())


# ============================================================================
# RUN API (used by the CLI below and by app.py)
# ============================================================================

# One process-wide graph + in-memory checkpointer so a paused run can be resumed by thread_id.
# Paused runs are lost on process restart; swap MemorySaver for a persistent saver if needed.
_GRAPH = None

NODE_LABELS = {
    "requirements_analyst": "🧐 Reviewing your brief...",
    "await_answers": "💬 Got your answers.",
    "creative_director": "🎬 Creative direction, reactive state and section plan ready.",
    "design_architect": "🎨 Design system (fonts, Tailwind config, CSS) ready.",
    "section_builder": "🧱 Built a section.",
    "master_assembler": "🛠️ Assembled the page and JavaScript engine.",
    "ast_qa_validator": "🔍 QA check complete.",
}


def get_studio_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_studio_workflow()
    return _GRAPH


def _execute(
    graph_input: Any,
    thread_id: str,
    on_progress: Optional[Callable[[str], None]],
    session_id: Optional[str] = None,
) -> dict:
    graph = get_studio_graph()
    config: dict = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}

    run_id = uuid.uuid4()
    is_resume = isinstance(graph_input, Command)
    provider = (
        graph.get_state(config).values.get("llm_provider") if is_resume else graph_input.get("llm_provider")
    )
    config.update(
        run_id=run_id,
        run_name="website_studio",
        tags=["website-studio", f"provider:{provider}", "resume" if is_resume else "start"],
        metadata={"session_id": session_id or thread_id, "studio_thread_id": thread_id},
    )

    for update in graph.stream(graph_input, config, stream_mode="updates"):
        if on_progress:
            for node in update:
                if node in NODE_LABELS:
                    on_progress(NODE_LABELS[node])

    snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
    values = dict(snapshot.values)
    paused = any(task.interrupts for task in snapshot.tasks)
    _log_run_feedback(run_id, values, paused)
    questions = [format_question(c) for c in values.get("clarifications", [])] if paused else []
    return {**values, "thread_id": thread_id, "needs_clarification": paused, "questions": questions}


def start_studio(
    user_prompt: str,
    provider: Optional[str] = None,
    thread_id: Optional[str] = None,
    clarify: bool = True,
    on_progress: Optional[Callable[[str], None]] = None,
    session_id: Optional[str] = None,
) -> dict:
    """Run until the site is built, or until the graph pauses to ask clarifying questions.

    Returns the final state plus `thread_id`, `needs_clarification` and `questions`.
    With clarify=False the analyst is skipped and the director decides everything.
    `session_id` (e.g. the chat session) is recorded as LangSmith metadata.
    """
    initial = StudioState(
        user_prompt=user_prompt,
        clarifications=[],
        is_clarified=not clarify,
        app_blueprint={},
        global_alpine_store={},
        design_system={},
        section_specs=[],
        completed_sections=[],
        final_html="",
        validation_errors=[],
        retry_count=0,
        llm_provider=provider or LLMConfig.get_default_provider(),
    )
    return _execute(initial, thread_id or uuid.uuid4().hex, on_progress, session_id)


def resume_studio(
    thread_id: str,
    answers: Any,
    on_progress: Optional[Callable[[str], None]] = None,
    session_id: Optional[str] = None,
) -> dict:
    """Continue a paused run. `answers` is a list (one per question) or a single free-text reply."""
    return _execute(Command(resume=answers), thread_id, on_progress, session_id)


def run_studio_workflow(
    user_prompt: str,
    provider: Optional[str] = None,
    clarify: bool = True,
    ask: Optional[Callable[[list[str]], Any]] = None,
    on_progress: Optional[Callable[[str], None]] = None,
) -> dict:
    """Blocking helper: answers clarifying questions through `ask(questions) -> answers`."""
    result = start_studio(user_prompt, provider, clarify=clarify and ask is not None, on_progress=on_progress)
    while result["needs_clarification"]:
        result = resume_studio(result["thread_id"], ask(result["questions"]), on_progress)
    return result


def _cli_ask(questions: list[str]) -> list[str]:
    print("\n🤔 A few quick questions (press Enter to let the designer decide):")
    answers = []
    for i, question in enumerate(questions, 1):
        try:
            answers.append(input(f"\n{i}. {question}\n> ").strip())
        except EOFError:
            answers.append("")
    return answers


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an interactive single-file website with LangGraph.")
    parser.add_argument("prompt", nargs="?", default="A modern AI-powered project management SaaS for design agencies")
    parser.add_argument("--provider", choices=["openrouter", "openai", "anthropic"], default=None)
    parser.add_argument("--output", default=None, help="Output file (default: website.html or $STUDIO_OUTPUT)")
    parser.add_argument("--no-clarify", action="store_true", help="Never ask questions; the designer decides")
    args = parser.parse_args()
    if args.output:
        OUTPUT_FILE = Path(args.output)

    print("🏢 Starting Website Studio workflow...")
    result = run_studio_workflow(
        args.prompt, args.provider, clarify=not args.no_clarify, ask=_cli_ask, on_progress=print
    )
    assumptions = (result.get("app_blueprint") or {}).get("assumptions") or []
    if assumptions:
        print("\n📝 Assumptions the designer made:\n" + "\n".join(f"  - {a}" for a in assumptions))
    status = "passed QA" if not result["validation_errors"] else f"finished with {len(result['validation_errors'])} QA issue(s)"
    print(f"\n🏁 Done: {status}; {len(result['completed_sections'])} sections -> {OUTPUT_FILE}")
