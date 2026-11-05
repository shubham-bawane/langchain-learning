"""
IT Service Company - Web Development Workflow
Restructured as a realistic IT service company with multiple stakeholder roles.

Workflow:
1. CLIENT (User) → Submits website requirements
2. ACCOUNT MANAGER (Agent) → Clarifies and gathers detailed requirements
3. UX/UI DESIGNER (Agent) → Creates design blueprint and user experience
4. DESIGN TEAM (Agent) → Defines visual design system, colors, fonts
5. WEB DEVELOPER (Agent) → Generates production-ready HTML code
6. QA TESTER (Agent) → Validates code quality and performance
7. PROJECT MANAGER (Agent) → Coordinates and delivers final output

This integrates with:
- LangSmith for monitoring and evaluation
- LangGraph for workflow orchestration
- Multiple LLM providers for cost/quality optimization
"""

import os
import re
import json
import random
from typing import Any, TypedDict, Optional, Literal
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.tracers.context import tracing_v2_enabled
from langgraph.graph import StateGraph, START, END
from langgraph.types import Interrupt


# ============================================================================
# LANGSMITH SETUP
# ============================================================================

# Initialize LangSmith tracing
def setup_langsmith():
    """Configure LangSmith for tracing and monitoring."""
    langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
    if langsmith_api_key:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_PROJECT"] = "IT-Service-WebDev"
        print("✅ LangSmith tracing enabled")
    else:
        print("⚠️ LangSmith API key not configured (optional)")


# ============================================================================
# IT SERVICE COMPANY STATE
# ============================================================================

class ClientRequest(TypedDict):
    """Client's initial request"""
    client_name: str
    project_description: str
    budget_tier: str  # "starter", "standard", "premium"
    timeline: str  # days


class ServiceCompanyState(TypedDict):
    """Complete state for IT service company workflow"""
    # Client Information
    client_id: str
    client_request: ClientRequest
    
    # Stakeholder Interactions
    account_manager_notes: str
    ux_designer_blueprint: str
    design_system: dict  # tailwind_config_extend, component_recipes, fonts
    creative_direction: dict  # archetype, spatial layout pattern, font pairings
    developer_code: str
    qa_test_report: str
    
    # Project Metadata
    project_status: str  # "inquiry", "requirements", "design", "development", "testing", "delivered"
    project_timeline: dict
    estimated_cost: float
    assigned_team: dict  # Team member assignments
    
    # Quality Tracking
    validation_errors: list[str]
    warnings: list[str]
    retry_count: int
    
    # Final Deliverables
    html_content: str
    design_assets: dict
    documentation: str
    
    # Framework & Tech Stack
    framework_choice: str
    tech_stack: list[str]
    
    # LLM Configuration
    llm_provider: str
    session_id: str


# ============================================================================
# LLM PROVIDER CONFIGURATION
# ============================================================================

class LLMConfig:
    """Configuration for LLM provider selection."""
    
    PROVIDERS = {
        "openrouter": "OpenRouter (cost-optimized)",
        "openai": "OpenAI GPT-4 (high quality)",
        "anthropic": "Anthropic Claude (balanced)",
    }
    
    @staticmethod
    def get_default_provider() -> str:
        """Determine the default LLM provider based on available API keys."""
        if os.getenv("OPENROUTER_API_KEY"):
            return "openrouter"
        elif os.getenv("OPENAI_API_KEY"):
            return "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            return "anthropic"
        else:
            raise ValueError("No LLM API key configured")
    
    @staticmethod
    def get_llm(
        provider: Optional[str] = None,
        model_override: Optional[str] = None,
        temperature: float = 0.7,
    ):
        """Get LLM instance for specified provider."""
        if provider is None:
            provider = LLMConfig.get_default_provider()
        
        api_key = os.getenv(f"{provider.upper()}_API_KEY")
        if not api_key:
            raise ValueError(f"API key for {provider} not found")
        
        if provider == "openrouter":
            return ChatOpenAI(
                model=model_override or os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-5.5"),
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=temperature,
                max_tokens=8192,
            )
        elif provider == "openai":
            return ChatOpenAI(
                model=model_override or "gpt-4-turbo",
                api_key=api_key,
                temperature=temperature,
                max_tokens=8192,
            )
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=model_override or "claude-3-opus-20240229",
                api_key=api_key,
                temperature=temperature,
                max_tokens=8192,
            )


# ============================================================================
# CREATIVE ARCHETYPES (anti-mode-collapse)
# ============================================================================

CREATIVE_ARCHETYPES: list[dict] = [
    {
        "archetype": "Neo-Brutalist Swiss Grids",
        "layout_pattern": "Rigid asymmetric grid, thick borders, offset hard shadows, oversized type",
        "font_pairing": {"heading": "Archivo Black", "body": "IBM Plex Mono"},
        "keywords": ["agency", "studio", "creative", "startup", "portfolio", "design", "marketing"],
    },
    {
        "archetype": "Atmospheric Dark Bento",
        "layout_pattern": "Bento grid with varying col/row spans, glowing gradient meshes, glass surfaces",
        "font_pairing": {"heading": "Space Grotesk", "body": "JetBrains Mono"},
        "keywords": ["saas", "software", "ai", "app", "platform", "tech", "data", "cloud", "api"],
    },
    {
        "archetype": "Luxury Editorial Serif",
        "layout_pattern": "Magazine-style asymmetric split screens, generous whitespace, large serif display type",
        "font_pairing": {"heading": "Playfair Display", "body": "DM Sans"},
        "keywords": ["luxury", "fashion", "jewelry", "hotel", "restaurant", "wine", "boutique", "law", "finance"],
    },
    {
        "archetype": "Kinetic Retro-Futurism",
        "layout_pattern": "Marquee tickers, sticky storytelling sections, chunky shapes and motion",
        "font_pairing": {"heading": "Syne", "body": "Plus Jakarta Sans"},
        "keywords": ["music", "event", "festival", "game", "gaming", "film", "entertainment", "youth"],
    },
    {
        "archetype": "Organic Warm Minimalist",
        "layout_pattern": "Soft rounded split sections, earthy palette, airy metric strips",
        "font_pairing": {"heading": "Instrument Serif", "body": "Inter"},
        "keywords": ["wellness", "health", "yoga", "organic", "food", "coffee", "bakery", "eco", "spa", "clinic"],
    },
    {
        "archetype": "High-Contrast Cyberpunk",
        "layout_pattern": "Neon-on-black tabbed showcases, scanline textures, angular clipped panels",
        "font_pairing": {"heading": "Space Grotesk", "body": "JetBrains Mono"},
        "keywords": ["crypto", "blockchain", "security", "cyber", "hacker", "web3", "esports"],
    },
]

_STYLE_MANDATE_PATTERN = re.compile(
    r"\b(style|aesthetic|look and feel|theme|minimali[sz]t|brutalis[tm]|retro|cyberpunk|"
    r"glassmorphi\w*|skeuomorph\w*|art deco|vintage|dark mode|color scheme|colour scheme)\b",
    re.IGNORECASE,
)


def _mandates_visual_style(description: str) -> bool:
    """True when the client explicitly dictates a visual style."""
    return bool(_STYLE_MANDATE_PATTERN.search(description or ""))


def _select_archetype(description: str) -> dict:
    """Pick the best keyword-fitting archetype, or a random one when nothing fits."""
    words = set(re.findall(r"[a-z0-9]+", (description or "").lower()))
    scored = [
        (len(words & set(a["keywords"])), a) for a in CREATIVE_ARCHETYPES
    ]
    best = max(score for score, _ in scored)
    pool = [a for score, a in scored if score == best] if best else CREATIVE_ARCHETYPES
    choice = random.choice(pool)
    return {k: v for k, v in choice.items() if k != "keywords"}


def _strip_code_fences(text: str) -> str:
    """Remove accidental ```html / ``` markdown fences around model output."""
    text = (text or "").strip()
    text = re.sub(r"^```[a-zA-Z]*\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _parse_json(text: str) -> dict:
    """Parse model JSON output, tolerating markdown fences."""
    return json.loads(_strip_code_fences(text))


# ============================================================================
# STAKEHOLDER AGENTS
# ============================================================================

class AccountManager:
    """
    ACCOUNT MANAGER - Client Interface
    Responsible for:
    - Understanding client needs
    - Asking clarifying questions
    - Gathering detailed requirements
    - Managing expectations
    """
    
    @staticmethod
    def clarify_requirements(state: ServiceCompanyState) -> ServiceCompanyState:
        """Analyze client request and ask clarifying questions if needed."""
        llm = LLMConfig.get_llm(state.get("llm_provider"))
        description = state["client_request"].get("project_description", "")

        seeded = None
        if not _mandates_visual_style(description):
            seeded = _select_archetype(description)
            state["creative_direction"] = dict(seeded)

        seed_note = (
            f"PRE-SELECTED ARCHETYPE (use it as the base of creative_direction):\n"
            f"{json.dumps(seeded, indent=2)}"
            if seeded
            else "The client mandated a visual style; derive creative_direction from their request."
        )

        system_prompt = """You are a Creative Director & Lead Account Manager at an elite digital agency. Analyze `client_request`. Alongside scope and timeline, define a bold, non-generic **Brand Archetype**, **Target Emotional Vibe**, and **Visual Anti-Patterns** (what clichés to strictly avoid for this industry). Output structured JSON into `account_manager_notes` and populate `creative_direction`.

Respond with raw JSON only, using this shape:
{
    "account_manager_notes": {
        "clarification_needed": true/false,
        "questions": ["up to 3 questions"],
        "initial_assessment": "scope and complexity assessment",
        "recommended_team_size": "number of developers",
        "estimated_timeline_days": number,
        "project_complexity": "low/medium/high",
        "brand_archetype": "bold, non-generic archetype",
        "target_emotional_vibe": "emotional vibe",
        "visual_anti_patterns": ["cliché to avoid", ...]
    },
    "creative_direction": {
        "archetype": "aesthetic archetype name",
        "layout_pattern": "spatial layout pattern",
        "font_pairing": {"heading": "font", "body": "font"}
    }
}"""

        message = llm.invoke([
            ("system", system_prompt),
            ("human", f"client_request:\n{json.dumps(state['client_request'], indent=2)}\n\n{seed_note}"),
        ])

        parsed = _parse_json(message.content)
        result = parsed.get("account_manager_notes", parsed)
        state["account_manager_notes"] = json.dumps(result, indent=2)

        direction = parsed.get("creative_direction")
        if seeded:
            # Pre-selected archetype stays authoritative; LLM details fill gaps.
            state["creative_direction"] = {**(direction or {}), **seeded}
        elif direction:
            state["creative_direction"] = direction
        state["project_status"] = "requirements"
        
        if result.get("clarification_needed"):
            raise Interrupt(f"Clarification needed: {result['questions']}")
        
        return state


class UXDesigner:
    """
    UX/UI DESIGNER - User Experience & Interface Design
    Responsible for:
    - Creating wireframes and user flows
    - Defining information architecture
    - Planning interactive elements
    - Accessibility considerations
    """
    
    @staticmethod
    def create_design_blueprint(state: ServiceCompanyState) -> ServiceCompanyState:
        """Create UX/UI blueprint based on requirements."""
        llm = LLMConfig.get_llm(state.get("llm_provider"), temperature=0.8)

        system_prompt = """You are an Principal UX/UI Architect. Read `account_manager_notes` and `creative_direction`.
**STRICT ANTI-MONOTONY RULES:**
1. You are FORBIDDEN from designing a generic template (centered hero + 3 equal feature cards + basic footer).
2. Design at least 6 rich, distinct sections using advanced spatial patterns matching the archetype: Asymmetric Split-Screens, Bento Grids with varying col-spans/row-spans (`md:col-span-2`, `md:row-span-2`), Marquee Tickers, Interactive Tabbed Showcases, Sticky Storytelling Sections, and Data/Metric Strips.
3. Specify at least 2 interactive user flows (e.g., live pricing calculator/toggle, filterable showcase tabs, interactive FAQ accordion, or modal trigger) that the developer must wire up with Vanilla JS.
Output a detailed structural blueprint in `ux_designer_blueprint`.

Respond with raw JSON only, using this shape:
{
    "sections": [
        {"name": "...", "spatial_pattern": "...", "layout_classes": "...", "content": "...", "interactions": "..."}
    ],
    "interactive_flows": [
        {"name": "...", "trigger": "...", "behavior": "...", "js_hooks": "element ids / data attributes"}
    ],
    "navigation": "mobile drawer + desktop nav description",
    "accessibility_notes": "WCAG notes",
    "responsive_strategy": "mobile / tablet / desktop behavior"
}"""

        message = llm.invoke([
            ("system", system_prompt),
            ("human", (
                f"account_manager_notes:\n{state['account_manager_notes']}\n\n"
                f"creative_direction:\n{json.dumps(state.get('creative_direction', {}), indent=2)}"
            )),
        ])

        result = _parse_json(message.content)
        state["ux_designer_blueprint"] = json.dumps(result, indent=2)
        state["project_status"] = "design"
        
        return state


class DesignTeam:
    """
    DESIGN TEAM - Visual Design & Branding
    Responsible for:
    - Defining color palette
    - Selecting typography
    - Creating design tokens
    - Brand consistency
    """
    
    @staticmethod
    def define_design_system(state: ServiceCompanyState) -> ServiceCompanyState:
        """Create comprehensive design system."""
        llm = LLMConfig.get_llm(state.get("llm_provider"), temperature=0.8)

        system_prompt = """You are an Award-Winning Art Director and Tailwind CSS Design Systems Engineer. Read `ux_designer_blueprint` and `creative_direction`.
**STRICT RULES:**
1. **BAN default `Inter` or plain `sans-serif` for headings.** Select a bespoke Google Fonts pairing that matches the archetype (e.g., `Syne` + `Plus Jakarta Sans`, `Playfair Display` + `DM Sans`, `Space Grotesk` + `JetBrains Mono`, `Instrument Serif` + `Inter`, or `Archivo Black` + `IBM Plex Mono`). Provide the exact `<link>` tag URL for Google Fonts.
2. **BAN raw hex codes without Tailwind mappings.** Output both a `tailwind_config_extend` JSON object (for custom colors, font families, and keyframe animations) AND a `component_recipes` dictionary containing exact, copy-pasteable multi-class Tailwind strings (minimum 6-10 utility classes per recipe) for:
   - `page_canvas` (including background textures, radial gradients, or grid patterns)
   - `nav_shell` (glassmorphism, floating pill, or brutalist bordered bar)
   - `hero_typography`
   - `primary_cta` & `secondary_cta` (with hover transforms, shadows, or offset borders)
   - `bento_card` / `feature_surface`
   - `badge_pill`
Save this structured dictionary in `design_system`.

Respond with raw JSON only, using this shape:
{
    "google_fonts_link": "<link href=\\"https://fonts.googleapis.com/css2?...\\" rel=\\"stylesheet\\">",
    "tailwind_config_extend": {"colors": {}, "fontFamily": {}, "keyframes": {}, "animation": {}},
    "component_recipes": {"page_canvas": "...", "nav_shell": "...", "hero_typography": "...", "primary_cta": "...", "secondary_cta": "...", "bento_card": "...", "badge_pill": "..."}
}"""

        message = llm.invoke([
            ("system", system_prompt),
            ("human", (
                f"ux_designer_blueprint:\n{state['ux_designer_blueprint']}\n\n"
                f"creative_direction:\n{json.dumps(state.get('creative_direction', {}), indent=2)}"
            )),
        ])

        result = _parse_json(message.content)
        state["design_system"] = result
        
        return state


class WebDeveloper:
    """
    WEB DEVELOPER - Frontend Development
    Responsible for:
    - Writing production-ready HTML/CSS/JS
    - Implementing design system
    - Ensuring code quality
    - Performance optimization
    """
    
    @staticmethod
    def develop_frontend(state: ServiceCompanyState) -> ServiceCompanyState:
        """Generate production-ready HTML code."""
        llm = LLMConfig.get_llm(state.get("llm_provider"), temperature=0.3)

        system_prompt = """You are a Principal Creative Frontend Developer. Read `ux_designer_blueprint`, `design_system`, and `validation_errors` (if retrying). Generate a single, complete, self-contained, production-grade `.html` file.
**MANDATORY IMPLEMENTATION RULES:**
1. Output **RAW HTML ONLY**. Never wrap in ```html markdown fences or add conversational text.
2. **Required `<head>` tags:**
   - `<script src="https://cdn.tailwindcss.com"></script>`
   - Dynamic `<script>tailwind.config = { ... }</script>` injecting the exact colors, fonts, and animations from `design_system`.
   - Exact Google Fonts `<link>` tags from `design_system`.
   - Lucide Icons CDN (`<script src="https://unpkg.com/lucide@latest"></script>`) and initialize with `lucide.createIcons();`.
   - A custom `<style>` block defining smooth scrolling, custom scrollbars, background grid/dot/noise textures, and `@keyframes` animations.
3. **High CSS & Visual Density:** Every structural element (`section`, `div`, `button`, `a`, `input`) MUST use the rich utility class recipes from `design_system`. Never output unstyled or skeleton HTML.
4. **Rich Media & Graphics:** Include inline SVG decorative elements, glowing background blurs/meshes, and realistic, high-resolution thematic Unsplash image URLs (`https://images.unsplash.com/photo-...`).
5. **Working Vanilla JavaScript:** Include a `<script>` tag before `</body>` implementing real interactivity for mobile navigation drawers, interactive tabs, pricing toggles, or accordions specified in `ux_designer_blueprint`.

**MANDATORY WORKING JAVASCRIPT ARCHITECTURE (BEFORE `</body>`):**
You are FORBIDDEN from outputting a static page or only calling `lucide.createIcons()`. You MUST write a comprehensive `<script>` block inside `DOMContentLoaded` implementing at least 4 of these working interactive systems with matching HTML `id` or `data-*` attributes:
1. **Mobile Menu Drawer Toggle:** Button (`id='mobile-menu-btn'`) toggling visibility and aria-expanded on `#mobile-menu`.
2. **Interactive Tab / Filter System:** Buttons with `data-tab-target` that filter/switch visible content panels (`data-tab-content`) and update active button Tailwind classes (`bg-...`, `text-...`).
3. **Dynamic Pricing / ROI Calculator or Toggle:** A toggle switch or range slider (`input[type='range']` or monthly/annual switch) that dynamically recalculates and animates numbers in the DOM (`[data-price]`).
4. **Interactive Accordion / Drawer:** Clicking items (`[data-accordion-btn]`) expands/collapses answer panels and rotates the chevron icon.
5. **Scroll Reveal & Navbar State:** `IntersectionObserver` that fades/slides elements in on scroll, plus a `window.addEventListener('scroll')` handler that adds glass/shadow classes to the `<header>`/`<nav>`."""

        human_prompt = (
            f"ux_designer_blueprint:\n{state.get('ux_designer_blueprint', '')}\n\n"
            f"design_system:\n{json.dumps(state.get('design_system', {}), indent=2)}\n\n"
            f"client_request:\n{json.dumps(state['client_request'], indent=2)}"
        )
        if state.get("validation_errors"):
            human_prompt += (
                "\n\nvalidation_errors (fix ALL of these in the regenerated file):\n"
                + "\n".join(f"- {e}" for e in state["validation_errors"])
            )

        message = llm.invoke([("system", system_prompt), ("human", human_prompt)])

        html_content = _strip_code_fences(message.content)
        
        # Validate HTML
        if not html_content.lower().startswith("<!doctype html"):
            html_content = "<!DOCTYPE html>\n" + html_content
        
        state["developer_code"] = html_content
        state["html_content"] = html_content
        state["project_status"] = "development"
        
        return state


class QATester:
    """
    QA TESTER - Quality Assurance
    Responsible for:
    - Code validation
    - Cross-browser testing
    - Performance checks
    - Security review
    - User experience testing
    """
    
    @staticmethod
    def validate_deliverable(state: ServiceCompanyState) -> ServiceCompanyState:
        """Perform comprehensive QA testing."""
        llm = LLMConfig.get_llm(state.get("llm_provider"))

        # Deterministic checks run first; fences are stripped before parsing.
        html_content = _strip_code_fences(state["html_content"])
        state["html_content"] = html_content
        state["developer_code"] = html_content
        errors = QATester.run_deterministic_checks(html_content)

        system_prompt = """You are a Senior QA Tester and Code Reviewer.

Review the HTML for: structure/syntax, responsive design, accessibility (WCAG 2.1), security vulnerabilities, performance, browser compatibility, CSS implementation, and broken links or missing assets. Also judge whether the design looks generic or monotonous.

Respond with raw JSON only:
{
    "validation_status": "passed/failed",
    "errors": ["error1", ...],
    "warnings": ["warning1", ...],
    "accessibility_score": "number out of 100",
    "performance_notes": "notes",
    "browser_compatibility": ["Chrome", "Firefox", "Safari", "Edge"],
    "recommendations": ["recommendation1", ...]
}"""

        message = llm.invoke([
            ("system", system_prompt),
            ("human", f"HTML GENERATED (truncated):\n{html_content[:8000]}"),
        ])

        result = _parse_json(message.content)
        if result.get("validation_status") == "failed":
            errors.extend(e for e in result.get("errors", []) if e not in errors)

        result["errors"] = errors
        result["validation_status"] = "failed" if errors else "passed"
        state["qa_test_report"] = json.dumps(result, indent=2)
        state["validation_errors"] = errors
        state["warnings"] = result.get("warnings", [])

        if errors:
            state["retry_count"] = state.get("retry_count", 0) + 1
            state["project_status"] = "development"  # Back to development for fixes
            return state
        
        state["project_status"] = "testing"
        return state

    @staticmethod
    def run_deterministic_checks(html: str) -> list[str]:
        """Structural and styling-density checks that do not need an LLM."""
        errors: list[str] = []
        soup = BeautifulSoup(html, "html.parser")
        head = soup.head or soup

        head_scripts = head.find_all("script")
        has_css_framework = any(
            "cdn.tailwindcss.com" in (s.get("src") or "")
            or "bootstrap" in (s.get("src") or "")
            for s in head_scripts
        ) or any("bootstrap" in (l.get("href") or "") for l in head.find_all("link"))
        if not has_css_framework:
            errors.append("Missing Tailwind (cdn.tailwindcss.com) or Bootstrap CDN in <head>.")

        if not any("fonts.googleapis.com" in (l.get("href") or "") for l in head.find_all("link")):
            errors.append("Missing Google Fonts <link> tag in <head>.")

        if not any("tailwind.config" in s.get_text() for s in head_scripts):
            errors.append("Missing tailwind.config script in <head>.")

        structural = soup.find_all(["div", "section", "button", "nav", "header", "footer"])
        if len(structural) < 25:
            errors.append("HTML is too sparse/skeleton-like. Build all 6 sections completely.")

        styled_targets = soup.find_all(["div", "section", "button"])
        if styled_targets:
            rich = sum(1 for t in styled_targets if len(t.get("class", [])) >= 3)
            density = rich / len(styled_targets)
        else:
            density = 0.0
        if density < 0.7:
            errors.append(
                "Low CSS styling density. Apply complete Tailwind utility recipes from design_system to all elements."
            )

        body = soup.body
        body_js = "\n".join(
            sc.get_text() for sc in (body.find_all("script") if body else []) if not sc.get("src")
        )
        errors.extend(QATester.check_js_interactivity(body_js, html))

        return errors

    @staticmethod
    def check_js_interactivity(js_text: str, html: str) -> list[str]:
        """Require real DOM-driven JS whose hooks (ids / data-*) exist in the HTML."""
        js_text = re.sub(r"lucide\.createIcons\(\s*\)\s*;?", "", js_text or "").strip()
        dom_keywords = ["addEventListener", "querySelector", "querySelectorAll", "getElementById", "classList"]
        keyword_hits = sum(1 for k in dom_keywords if k in js_text)

        hooks_ok = False
        if js_text:
            soup = BeautifulSoup(html, "html.parser")
            html_ids = {t.get("id") for t in soup.find_all(id=True)}
            data_attrs = {a for t in soup.find_all(True) for a in t.attrs if a.startswith("data-")}
            hooks_ok = any(i and i in js_text for i in html_ids) or any(
                a in js_text or a[5:] in js_text for a in data_attrs
            )

        if len(js_text) < 350 or keyword_hits < 2 or not hooks_ok:
            return [
                "Missing real Vanilla JS interactivity. Do not just call lucide.createIcons(). "
                "You MUST write complete DOM event listeners (addEventListener, classList.toggle, etc.) "
                "for at least 3 interactive features: mobile drawer menu, interactive tabs/filters, "
                "pricing/metric calculator, or FAQ accordion."
            ]
        return []


class ProjectManager:
    """
    PROJECT MANAGER - Project Coordination
    Responsible for:
    - Orchestrating team workflow
    - Managing timeline
    - Delivering final output
    - Client communication
    """
    
    @staticmethod
    def finalize_delivery(state: ServiceCompanyState) -> ServiceCompanyState:
        """Prepare final deliverables package."""
        
        # Create delivery summary
        delivery_summary = {
            "project_id": state.get("client_id"),
            "client_name": state["client_request"].get("client_name"),
            "project_status": "DELIVERED",
            "completion_date": datetime.now().isoformat(),
            "deliverables": {
                "html_file": "website.html",
                "design_system": state.get("design_system", {}),
                "qa_report": state.get("qa_test_report"),
                "documentation": "README.md"
            },
            "team_feedback": {
                "account_manager": state.get("account_manager_notes"),
                "ux_designer": state.get("ux_designer_blueprint"),
                "qa_tester": state.get("qa_test_report")
            }
        }
        
        state["documentation"] = json.dumps(delivery_summary, indent=2)
        state["project_status"] = "delivered"
        
        return state


# ============================================================================
# WORKFLOW ORCHESTRATION
# ============================================================================

MAX_QA_RETRIES = 2


def qa_decision(state: ServiceCompanyState) -> Literal["developer", "project_manager"]:
    """Route after QA. retry_count is incremented by QATester, not here."""
    if state.get("validation_errors") and state.get("retry_count", 0) <= MAX_QA_RETRIES:
        return "developer"
    return "project_manager"


def build_service_company_workflow():
    """Build the IT service company workflow graph."""
    
    workflow = StateGraph(ServiceCompanyState)
    
    # Add nodes for each team member
    workflow.add_node("account_manager", AccountManager.clarify_requirements)
    workflow.add_node("ux_designer", UXDesigner.create_design_blueprint)
    workflow.add_node("design_team", DesignTeam.define_design_system)
    workflow.add_node("developer", WebDeveloper.develop_frontend)
    workflow.add_node("qa_tester", QATester.validate_deliverable)
    workflow.add_node("project_manager", ProjectManager.finalize_delivery)
    
    # Define workflow edges
    workflow.add_edge(START, "account_manager")
    workflow.add_edge("account_manager", "ux_designer")
    workflow.add_edge("ux_designer", "design_team")
    workflow.add_edge("design_team", "developer")
    workflow.add_edge("developer", "qa_tester")
    workflow.add_edge("project_manager", END)
    
    # QA loops back to the developer until it passes or retries are exhausted
    workflow.add_conditional_edges(
        "qa_tester",
        qa_decision,
        {"developer": "developer", "project_manager": "project_manager"},
    )
    
    return workflow.compile()


# ============================================================================
# EXECUTION INTERFACE
# ============================================================================

def run_service_company_workflow(initial_state: ServiceCompanyState):
    """Execute the IT service company workflow."""
    
    # Setup LangSmith
    setup_langsmith()
    
    # Build workflow
    workflow = build_service_company_workflow()
    
    # Execute with LangSmith tracing
    with tracing_v2_enabled(project_name="IT-Service-WebDev"):
        result = workflow.invoke(initial_state)
    
    return result


if __name__ == "__main__":
    # Example usage
    test_state = ServiceCompanyState(
        client_id="CLIENT_001",
        client_request={
            "client_name": "Tech Startup Inc",
            "project_description": "Modern landing page with portfolio section",
            "budget_tier": "standard",
            "timeline": "7"
        },
        account_manager_notes="",
        ux_designer_blueprint="",
        design_system={},
        creative_direction={},
        developer_code="",
        qa_test_report="",
        project_status="inquiry",
        project_timeline={},
        estimated_cost=0.0,
        assigned_team={},
        validation_errors=[],
        warnings=[],
        retry_count=0,
        html_content="",
        design_assets={},
        documentation="",
        framework_choice="Tailwind",
        tech_stack=["HTML5", "CSS3", "JavaScript"],
        llm_provider=LLMConfig.get_default_provider(),
        session_id="SESSION_001"
    )
    
    print("🏢 Starting IT Service Company Workflow...")
    result = run_service_company_workflow(test_state)
    print("✅ Workflow completed!")
    print(f"Project Status: {result['project_status']}")
