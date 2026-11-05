"""
Multi-Agent AI System for HTML Generation using LangChain and LangGraph.

This system uses a state graph to orchestrate multiple agents that collaborate to:
1. Clarify user requirements
2. Design UI/UX blueprints
3. Define aesthetic design systems
4. Generate production-ready HTML
5. Validate the generated code
6. Save the output to a file

The system includes human-in-the-loop capability for requirement clarification.
Supports multiple LLM providers: OpenAI, OpenRouter, Anthropic.
Integrates with Qdrant vector DB for future RAG capabilities.
"""

import os
import re
import json
from typing import Any, TypedDict, Optional, Literal
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.types import Interrupt


# ============================================================================
# 1. GRAPH STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """State maintained across all nodes in the LangGraph."""
    user_prompt: str
    manager_clarifications: list[dict]  # List of {question, answer} dicts
    final_specifications: str
    ux_blueprint: str
    design_system: str
    framework_choice: str  # "Tailwind" or "Bootstrap"
    html_content: str
    validation_errors: list[str]
    retry_count: int
    llm_provider: str  # Track which LLM provider is being used
    session_id: str  # For database tracking


# ============================================================================
# 2. LLM PROVIDER CONFIGURATION
# ============================================================================

class LLMConfig:
    """Configuration for LLM provider selection."""
    
    PROVIDERS = {
        "openai": "OpenAI GPT-4",
        "openrouter": "OpenRouter (cost-optimized)",
        "anthropic": "Anthropic Claude",
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
            raise ValueError(
                "No LLM API key configured. Please set one of:\n"
                "  - OPENAI_API_KEY\n"
                "  - OPENROUTER_API_KEY\n"
                "  - ANTHROPIC_API_KEY"
            )
    
    @staticmethod
    def get_llm(provider: Optional[str] = None) -> ChatOpenAI:
        """
        Get LLM instance based on provider.
        
        Args:
            provider: One of "openai", "openrouter", "anthropic". 
                     If None, auto-detects from available keys.
        
        Returns:
            ChatOpenAI instance configured for the provider.
        """
        if provider is None:
            provider = LLMConfig.get_default_provider()
        
        print(f"📡 Using LLM Provider: {LLMConfig.PROVIDERS.get(provider, provider)}")
        
        if provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY not set")
            return ChatOpenAI(
                model=model,
                temperature=0.7,
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
            )
        
        elif provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not set")
                return ChatAnthropic(
                    model="claude-3-5-sonnet-20241022",
                    temperature=0.7,
                    api_key=api_key,
                )
            except ImportError:
                raise ImportError(
                    "langchain-anthropic not installed. "
                    "Run: pip install langchain-anthropic"
                )
        
        else:  # openai (default)
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            return ChatOpenAI(
                model="gpt-4",
                temperature=0.7,
                api_key=api_key,
            )


# ============================================================================
# 3. DATABASE INTEGRATION (Qdrant)
# ============================================================================

class DatabaseConfig:
    """Configuration for vector database (Qdrant)."""
    
    @staticmethod
    def is_configured() -> bool:
        """Check if Qdrant is configured."""
        return bool(os.getenv("QDRANT_URL") and os.getenv("QDRANT_API_KEY"))
    
    @staticmethod
    def get_client():
        """
        Get Qdrant client if configured.
        
        Returns:
            Qdrant client or None if not configured.
        """
        if not DatabaseConfig.is_configured():
            return None
        
        try:
            from qdrant_client import QdrantClient
            
            qdrant_url = os.getenv("QDRANT_URL")
            qdrant_key = os.getenv("QDRANT_API_KEY")
            
            client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_key,
            )
            print(f"✓ Connected to Qdrant at {qdrant_url}")
            return client
        except ImportError:
            print("⚠️  qdrant-client not installed. Skipping vector DB.")
            return None
        except Exception as e:
            print(f"⚠️  Qdrant connection failed: {e}")
            return None
    
    @staticmethod
    def store_generation_metadata(
        html_content: str,
        metadata: dict,
        client=None,
    ):
        """
        Store HTML generation metadata in Qdrant for future retrieval.
        
        Args:
            html_content: Generated HTML
            metadata: Generation context (prompt, framework, etc.)
            client: Qdrant client instance
        """
        if not client:
            return
        
        try:
            collection_name = os.getenv("QDRANT_COLLECTION", "langchain-learning")
            
            # Prepare payload
            payload = {
                "timestamp": datetime.now().isoformat(),
                "html_length": len(html_content),
                "framework": metadata.get("framework_choice", "unknown"),
                "user_prompt": metadata.get("user_prompt", ""),
                "specifications": metadata.get("final_specifications", ""),
            }
            
            print(f"📦 Storing metadata in Qdrant collection: {collection_name}")
            # Note: Full implementation would include embeddings and vector operations
            
        except Exception as e:
            print(f"⚠️  Failed to store metadata: {e}")


# ============================================================================
# 4. UTILITY FUNCTIONS
# ============================================================================


def _get_llm(provider: Optional[str] = None) -> ChatOpenAI:
    """
    Initialize and return the LLM.
    
    Args:
        provider: Optional LLM provider ("openai", "openrouter", "anthropic")
    """
    return LLMConfig.get_llm(provider)


def _extract_text(content: Any) -> str:
    """Extract string content from various message formats."""
    if isinstance(content, str):
        return content
    if hasattr(content, "content"):
        return content.content
    return str(content)


def _parse_clarifications(text: str) -> tuple[list[str], str]:
    """
    Parse manager response to extract questions and clarification summary.
    
    Returns:
        (questions, clarification_summary)
    """
    lines = text.split("\n")
    questions = []
    summary_lines = []
    in_questions = False

    for line in lines:
        if "question" in line.lower() and ":" in line:
            in_questions = True
            # Extract question text
            question = re.sub(r"^.*?:\s*", "", line).strip()
            if question:
                questions.append(question)
        elif in_questions and line.strip() and not line.startswith("-"):
            in_questions = False
            summary_lines.append(line)
        elif in_questions and line.startswith("-"):
            q = line.replace("-", "").strip()
            if q:
                questions.append(q)
        elif not in_questions and line.strip():
            summary_lines.append(line)

    return questions or ["Do you want to proceed with the requirements as stated?"], "\n".join(
        summary_lines
    )


# ============================================================================
# 3. NODE DEFINITIONS (AGENTS)
# ============================================================================

def clarify_requirements(state: AgentState) -> AgentState:
    """
    Node 1: Manager Agent - Clarify user requirements.
    
    If the user prompt is clear, write final_specifications.
    If vague, generate clarifying questions and trigger a breakpoint.
    """
    print("\n" + "=" * 80)
    print("NODE 1: MANAGER AGENT - CLARIFY REQUIREMENTS")
    print("=" * 80)

    llm = _get_llm()
    prompt = ChatPromptTemplate.from_template(
        """You are a product manager reviewing a user's request for an HTML website.

User's Initial Request:
{user_prompt}

Analyze this request. If it's clear and detailed enough to proceed (has specific features, 
layout ideas, color preferences, or purpose), write "CLEAR" followed by a summary of 
final_specifications.

If the request is vague or missing key details, write "UNCLEAR" followed by a numbered 
list of 3-5 specific clarifying questions.

Guidelines for "CLEAR":
- The user has given enough detail about what they want
- They've specified purpose, layout, or style preferences
- Examples: "landing page with hero section, features list, and contact form" or 
  "e-commerce product page with dark theme"

Guidelines for "UNCLEAR":
- The request is too generic ("create a website")
- Missing critical details (no mention of purpose, features, or style)
- Ambiguous requirements
"""
    )

    chain = prompt | llm
    result = chain.invoke({"user_prompt": state["user_prompt"]})
    response_text = _extract_text(result)

    print(f"Manager Analysis:\n{response_text}\n")

    if "CLEAR" in response_text.upper():
        # Extract specifications
        spec_text = response_text.split("CLEAR", 1)[1].strip()
        state["final_specifications"] = spec_text
        state["manager_clarifications"] = []
        print("✓ Requirements are clear. Proceeding with specifications.")
        return state

    else:
        # Extract questions and trigger interrupt
        questions, summary = _parse_clarifications(response_text)
        state["manager_clarifications"] = [
            {"question": q, "answer": None} for q in questions
        ]

        print(f"⚠ Requirements need clarification. Questions generated:\n")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q}")

        # Create interrupt message
        interrupt_msg = f"""
Please provide answers to the following clarifying questions:

{chr(10).join(f'{i}. {q}' for i, q in enumerate(questions, 1))}

The system will wait for your input before proceeding.
"""
        print(f"\n{interrupt_msg}")

        # Trigger interrupt to get user input
        raise Interrupt(
            f"Clarification needed. Please answer the following questions:\n\n"
            + "\n".join(f"{i}. {q}" for i, q in enumerate(questions, 1))
        )


def design_user_journey(state: AgentState) -> AgentState:
    """
    Node 2: UI/UX Agent - Design structural layout and user journey.
    
    Creates a blueprint describing layout, sections, and user flow.
    Ignores colors and code details.
    """
    print("\n" + "=" * 80)
    print("NODE 2: UI/UX AGENT - DESIGN USER JOURNEY")
    print("=" * 80)

    llm = _get_llm()
    prompt = ChatPromptTemplate.from_template(
        """You are a UX/UI designer. Based on the following specifications, 
create a detailed UX blueprint describing:
1. Page structure and main sections
2. User journey and interaction flow
3. Layout hierarchy (header, main content, footer, sidebars, etc.)
4. Key components and their placement
5. User interactions and navigation paths

Do NOT include color schemes, fonts, or CSS details. Focus purely on structure and flow.

Final Specifications:
{final_specifications}

Previous Clarifications:
{clarifications}

Write the blueprint as a structured outline with clear sections.
"""
    )

    clarifications_text = (
        "\n".join(
            [
                f"Q: {c['question']}\nA: {c.get('answer', 'N/A')}"
                for c in state["manager_clarifications"]
            ]
        )
        if state["manager_clarifications"]
        else "None"
    )

    chain = prompt | llm
    result = chain.invoke(
        {
            "final_specifications": state["final_specifications"],
            "clarifications": clarifications_text,
        }
    )
    blueprint = _extract_text(result)
    state["ux_blueprint"] = blueprint

    print(f"UX Blueprint Created:\n{blueprint[:500]}...\n")
    print("✓ UX blueprint design complete.")

    return state


def define_aesthetics(state: AgentState) -> AgentState:
    """
    Node 3: Web Designer Agent - Define design system with specific styling rules.
    
    Converts the UX blueprint into a design system with exact Tailwind or Bootstrap classes.
    """
    print("\n" + "=" * 80)
    print("NODE 3: WEB DESIGNER AGENT - DEFINE AESTHETICS")
    print("=" * 80)

    llm = _get_llm()
    prompt = ChatPromptTemplate.from_template(
        """You are a web designer creating a design system. Based on the UX blueprint 
and specifications, define a comprehensive design system including:

1. Color Palette: List specific hex colors and their semantic meanings
2. Typography: Font choices, sizes, and weights
3. Spacing System: Margin/padding units
4. Component Styles: How buttons, inputs, cards, etc. should look
5. Framework Choice: Should this use Tailwind CSS or Bootstrap? 
   - Use Tailwind if the design is modern, minimalist, or needs custom utilities
   - Use Bootstrap if the design needs quick, standard components

Provide exact CSS class names or Tailwind utility classes to be used throughout.

Specifications:
{final_specifications}

UX Blueprint:
{ux_blueprint}

Output the design system as a structured guide that a developer can follow exactly.
"""
    )

    chain = prompt | llm
    result = chain.invoke(
        {
            "final_specifications": state["final_specifications"],
            "ux_blueprint": state["ux_blueprint"],
        }
    )
    design_system = _extract_text(result)
    state["design_system"] = design_system

    # Determine framework from design system response
    if "bootstrap" in design_system.lower():
        state["framework_choice"] = "Bootstrap"
    else:
        state["framework_choice"] = "Tailwind"

    print(f"Design System Created (Framework: {state['framework_choice']}):")
    print(design_system[:500] + "...\n")
    print("✓ Design system defined.")

    return state


def generate_html(state: AgentState) -> AgentState:
    """
    Node 4: Code Generator - Generate production-ready HTML.
    
    CRITICAL: Must output raw HTML only, with proper CDN links injected.
    No markdown code blocks or backticks.
    """
    print("\n" + "=" * 80)
    print("NODE 4: CODE GENERATOR - GENERATE HTML")
    print("=" * 80)

    if state["retry_count"] > 0:
        print(f"Retry attempt {state['retry_count']} - Fixing validation errors...")
        error_context = f"\n\nFix these validation errors from the previous attempt:\n" + "\n".join(
            state["validation_errors"]
        )
    else:
        error_context = ""

    llm = _get_llm()
    prompt = ChatPromptTemplate.from_template(
        """You are an expert HTML developer. Generate a complete, single-file HTML page 
based on the following design system and specifications.

CRITICAL REQUIREMENTS:
1. Output ONLY raw HTML code. NO markdown formatting. NO ```html``` backticks. NO explanations.
2. Include the official CDN link for {framework_choice} in the <head> tag.
3. Ensure proper <!DOCTYPE html>, <html>, <head>, and <body> tags.
4. Make the page fully functional and visually complete.
5. Use semantic HTML5 tags where appropriate.
6. Ensure all utility classes or component classes match the design system.

Framework: {framework_choice}

CDN Links:
- Tailwind CSS: <script src="https://cdn.tailwindcss.com"></script> (in <head>)
- Bootstrap: <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
           AND <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script> (at end of <body>)

Design System:
{design_system}

Specifications:
{final_specifications}

UX Blueprint:
{ux_blueprint}
{error_context}

Generate the HTML now. Output ONLY the code, starting with <!DOCTYPE html> and ending with </html>.
"""
    )

    chain = prompt | llm
    result = chain.invoke(
        {
            "framework_choice": state["framework_choice"],
            "design_system": state["design_system"],
            "final_specifications": state["final_specifications"],
            "ux_blueprint": state["ux_blueprint"],
            "error_context": error_context,
        }
    )

    html_content = _extract_text(result)

    # Remove markdown code blocks if present
    html_content = re.sub(r"```html\s*\n?", "", html_content)
    html_content = re.sub(r"```\s*\n?", "", html_content)
    html_content = html_content.strip()

    state["html_content"] = html_content

    print(f"HTML Generated (length: {len(html_content)} chars)")
    print(f"Preview (first 300 chars):\n{html_content[:300]}...\n")
    print("✓ HTML generation complete.")

    return state


def validate_code(state: AgentState) -> AgentState:
    """
    Node 5: Output Validator - Validate generated HTML.
    
    Checks for:
    - Proper DOCTYPE and HTML tags
    - Valid CDN links
    - Absence of markdown code blocks
    """
    print("\n" + "=" * 80)
    print("NODE 5: OUTPUT VALIDATOR - VALIDATE CODE")
    print("=" * 80)

    validation_errors = []
    html = state["html_content"]

    # Check 1: DOCTYPE
    if not re.search(r"<!DOCTYPE\s+html>", html, re.IGNORECASE):
        validation_errors.append("Missing <!DOCTYPE html>")

    # Check 2: HTML tags
    if not re.search(r"<html[^>]*>", html, re.IGNORECASE):
        validation_errors.append("Missing opening <html> tag")
    if not re.search(r"</html>", html, re.IGNORECASE):
        validation_errors.append("Missing closing </html> tag")

    # Check 3: Head and Body
    if not re.search(r"<head[^>]*>", html, re.IGNORECASE):
        validation_errors.append("Missing <head> tag")
    if not re.search(r"<body[^>]*>", html, re.IGNORECASE):
        validation_errors.append("Missing <body> tag")

    # Check 4: CDN Links
    if state["framework_choice"] == "Tailwind":
        if "cdn.tailwindcss.com" not in html:
            validation_errors.append(
                "Missing Tailwind CDN link (https://cdn.tailwindcss.com)"
            )
    elif state["framework_choice"] == "Bootstrap":
        if "bootstrap" not in html.lower():
            validation_errors.append("Missing Bootstrap CDN link")

    # Check 5: Markdown code blocks
    if "```" in html:
        validation_errors.append("HTML contains markdown code blocks (```)")

    state["validation_errors"] = validation_errors
    state["retry_count"] += 1

    if validation_errors:
        print(f"❌ Validation failed. {len(validation_errors)} error(s) found:")
        for error in validation_errors:
            print(f"  - {error}")
    else:
        print("✓ All validation checks passed!")

    return state


def save_file(state: AgentState) -> AgentState:
    """
    Node 6: File Writer - Save validated HTML to output.html.
    Also stores metadata in database if configured.
    """
    print("\n" + "=" * 80)
    print("NODE 6: FILE WRITER - SAVE OUTPUT")
    print("=" * 80)

    output_path = "output.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(state["html_content"])

    print(f"✓ HTML file saved to: {output_path}")
    print(f"  File size: {len(state['html_content'])} bytes")
    print(f"  Framework: {state['framework_choice']}")
    print(f"  LLM Provider: {state['llm_provider']}")
    print(f"  Session ID: {state['session_id']}")

    # Store metadata in database if configured
    if DatabaseConfig.is_configured():
        db_client = DatabaseConfig.get_client()
        if db_client:
            DatabaseConfig.store_generation_metadata(
                state["html_content"],
                {
                    "user_prompt": state["user_prompt"],
                    "final_specifications": state["final_specifications"],
                    "framework_choice": state["framework_choice"],
                    "llm_provider": state["llm_provider"],
                    "session_id": state["session_id"],
                },
                db_client,
            )

    return state


# ============================================================================
# 4. ROUTING LOGIC (Edges)
# ============================================================================

def should_retry_validation(state: AgentState) -> str:
    """
    Conditional edge from validator.
    
    Returns:
        - "generate_html": Retry code generation if errors exist and retry_count < 3
        - "save_file": Proceed to save if no errors
        - "end": Stop if retry limit exceeded
    """
    if not state["validation_errors"]:
        return "save_file"

    if state["retry_count"] >= 3:
        print(
            f"\n❌ VALIDATION FAILED: Retry limit (3) exceeded. Stopping graph execution."
        )
        return "end"

    print(
        f"\n🔄 Retrying code generation (attempt {state['retry_count']} of 3)..."
    )
    return "generate_html"


def should_clarify_or_proceed(state: AgentState) -> str:
    """
    Conditional edge after manager agent.
    
    Returns:
        - "design_user_journey": If requirements are clear
        - "end": If clarification was needed and will use interrupt
    """
    # This is handled by the interrupt mechanism in clarify_requirements
    return "design_user_journey"


# ============================================================================
# 5. GRAPH COMPILATION
# ============================================================================

def build_graph():
    """
    Build and compile the LangGraph StateGraph.
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("clarify_requirements", clarify_requirements)
    graph.add_node("design_user_journey", design_user_journey)
    graph.add_node("define_aesthetics", define_aesthetics)
    graph.add_node("generate_html", generate_html)
    graph.add_node("validate_code", validate_code)
    graph.add_node("save_file", save_file)

    # Add edges
    graph.add_edge(START, "clarify_requirements")
    graph.add_edge("clarify_requirements", "design_user_journey")
    graph.add_edge("design_user_journey", "define_aesthetics")
    graph.add_edge("define_aesthetics", "generate_html")
    graph.add_edge("generate_html", "validate_code")

    # Conditional edge from validator
    graph.add_conditional_edges(
        "validate_code",
        should_retry_validation,
        {
            "generate_html": "generate_html",
            "save_file": "save_file",
            "end": END,
        },
    )

    graph.add_edge("save_file", END)

    return graph.compile()


# ============================================================================
# 6. EXECUTION & HUMAN-IN-THE-LOOP HANDLER
# ============================================================================

def run_html_generation_workflow(
    user_prompt,
    llm_provider: Optional[str] = None,
    use_database: bool = True,
):
    """
    Execute the HTML generation workflow with human-in-the-loop support.
    
    Args:
        user_prompt: Either a string (initial request) or AgentState dict
        llm_provider: Optional LLM provider ("openai", "openrouter", "anthropic")
        use_database: Whether to store metadata in Qdrant if configured
    
    Returns:
        Completed AgentState
    """
    # Handle both string and dict inputs
    if isinstance(user_prompt, dict):
        initial_state = user_prompt
        prompt_text = initial_state.get("user_prompt", "")
    else:
        prompt_text = user_prompt
        initial_state = None
    
    print("\n" + "=" * 80)
    print("🚀 MULTI-AGENT HTML GENERATION SYSTEM")
    print("=" * 80)
    print(f"User Prompt: {prompt_text}\n")

    # Determine LLM provider
    if llm_provider is None:
        try:
            llm_provider = LLMConfig.get_default_provider()
        except ValueError as e:
            print(f"❌ Error: {e}")
            raise

    print(f"Selected Provider: {LLMConfig.PROVIDERS.get(llm_provider, llm_provider)}\n")

    # Generate session ID
    session_id = f"session_{int(datetime.now().timestamp() * 1000)}"

    # Initialize or use provided state
    if initial_state is None:
        initial_state: AgentState = {
            "user_prompt": prompt_text,
            "manager_clarifications": [],
            "final_specifications": "",
            "ux_blueprint": "",
            "design_system": "",
            "framework_choice": "Tailwind",
            "html_content": "",
            "validation_errors": [],
            "retry_count": 0,
            "llm_provider": llm_provider,
            "session_id": session_id,
        }
    else:
        # Update provider in existing state
        initial_state["llm_provider"] = llm_provider
        if not initial_state.get("session_id"):
            initial_state["session_id"] = session_id

    # Compile graph
    compiled_graph = build_graph()

    # Run with interrupt handling
    config = {"configurable": {"thread_id": "main"}}

    try:
        while True:
            print("\n" + "-" * 80)
            print("Executing workflow...")
            print("-" * 80 + "\n")

            try:
                # Stream events from the graph
                for output in compiled_graph.stream(initial_state, config):
                    # Process output from each node
                    for key, value in output.items():
                        if key != "__end__":
                            initial_state = value

            except BaseException as e:
                # Handle interrupt for clarifying questions
                if isinstance(e, Interrupt):
                    print(f"\n{e.value}\n")

                    # Collect user answers
                    questions = [
                        c["question"] for c in initial_state["manager_clarifications"]
                    ]

                    answers = []
                    for i, question in enumerate(questions, 1):
                        answer = input(f"\nAnswer {i}: ").strip()
                        if not answer:
                            answer = "No specific preference"
                        answers.append(answer)
                        initial_state["manager_clarifications"][i - 1]["answer"] = answer

                    # Build final specifications from answers
                    spec_builder = f"""Based on the clarifying questions and answers:

Questions & Answers:
"""
                    for q, a in zip(questions, answers):
                        spec_builder += f"\nQ: {q}\nA: {a}\n"

                    spec_builder += f"""

Original user request: {initial_state['user_prompt']}

Create detailed final specifications for the HTML page that incorporate all these answers.
"""

                    llm = _get_llm(llm_provider)
                    prompt = ChatPromptTemplate.from_template(spec_builder)
                    chain = prompt | llm
                    result = chain.invoke({})
                    initial_state["final_specifications"] = _extract_text(result)

                    print("\n✓ Specifications updated. Resuming workflow...\n")

                    # Resume from next node
                    continue
                else:
                    # Re-raise if it's not an Interrupt
                    raise

            # If we get here without interrupt, workflow completed
            break

    except Exception as e:
        print(f"\n❌ Workflow error: {e}")
        raise

    print("\n" + "=" * 80)
    print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print(f"Generated HTML file: output.html")
    print(f"Session ID: {initial_state.get('session_id')}")
    print(f"LLM Provider: {LLMConfig.PROVIDERS.get(llm_provider, llm_provider)}")
    
    return initial_state


# ============================================================================
# 7. MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Example usage with different prompts and LLM providers
    test_prompts = [
        "Create a modern landing page for a tech startup that sells AI tools. Include a hero section, features grid, testimonials, and a contact form.",
    ]

    print("\n" + "=" * 80)
    print("Available LLM Providers:")
    print("=" * 80)
    for provider, description in LLMConfig.PROVIDERS.items():
        configured = False
        if provider == "openai":
            configured = bool(os.getenv("OPENAI_API_KEY"))
        elif provider == "openrouter":
            configured = bool(os.getenv("OPENROUTER_API_KEY"))
        elif provider == "anthropic":
            configured = bool(os.getenv("ANTHROPIC_API_KEY"))
        
        status = "✓ Configured" if configured else "✗ Not configured"
        print(f"  - {provider:12} : {description:40} [{status}]")
    
    print("\nDatabase Configuration:")
    print("=" * 80)
    if DatabaseConfig.is_configured():
        print(f"  ✓ Qdrant configured at {os.getenv('QDRANT_URL')}")
    else:
        print(f"  ✗ Qdrant not configured (set QDRANT_URL and QDRANT_API_KEY)")
    
    print("\n")

    for prompt in test_prompts:
        try:
            # Auto-detect provider or specify manually:
            # run_html_generation_workflow(prompt, llm_provider="openrouter")
            # run_html_generation_workflow(prompt, llm_provider="openai")
            # run_html_generation_workflow(prompt, llm_provider="anthropic")
            
            run_html_generation_workflow(prompt)  # Auto-detect
            print("\n✓ Test completed successfully!\n")
            break
        except KeyboardInterrupt:
            print("\n\n⏹ Workflow interrupted by user.")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            break
