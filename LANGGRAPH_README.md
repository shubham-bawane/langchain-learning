# 🔗 LangGraph Workflow Documentation

This document provides deep technical details about the LangGraph multi-agent workflow that powers the IT Service Company web development system.

---

## 📋 Table of Contents

1. [LangGraph Overview](#langgraph-overview)
2. [State Management](#state-management)
3. [Agent Architecture](#agent-architecture)
4. [Workflow Graph](#workflow-graph)
5. [Edge Connections](#edge-connections)
6. [State Persistence](#state-persistence)
7. [Interrupt Handling](#interrupt-handling)
8. [Execution Flow](#execution-flow)
9. [Advanced Patterns](#advanced-patterns)
10. [Debugging](#debugging)

---

## 🔗 LangGraph Overview

**LangGraph** is a library for building stateful, multi-agent applications with complex routing and memory.

### Key Concepts

| Concept | Definition |
|---------|-----------|
| **Graph** | DAG (Directed Acyclic Graph) of nodes and edges |
| **Node** | Function that processes state and returns updated state |
| **Edge** | Connection between nodes directing workflow |
| **State** | Shared data structure passed between nodes |
| **START** | Virtual start node (graph entry point) |
| **END** | Virtual end node (graph exit point) |
| **Interrupt** | Pause workflow for human-in-the-loop interaction |

### Why LangGraph for This Project?

✅ **Multi-Agent Orchestration** - Coordinate 7 different AI agents  
✅ **State Management** - Track complete workflow state  
✅ **Conditional Routing** - Route based on conditions  
✅ **Interrupt/Resume** - Human-in-the-loop clarification  
✅ **Persistence** - Save/resume workflows  
✅ **Debugging** - Trace execution through visualizations  

---

## 📊 State Management

### ServiceCompanyState TypedDict

```python
class ServiceCompanyState(TypedDict):
    """Complete state for IT service company workflow"""
    
    # Client Information
    client_id: str
    client_request: ClientRequest  # {name, description, budget, timeline}
    
    # Stakeholder Work
    account_manager_notes: str          # Requirements analysis
    ux_designer_blueprint: str          # Design wireframes & flows
    design_system: dict                 # Colors, fonts, spacing
    developer_code: str                 # Generated HTML
    qa_test_report: str                 # Quality validation
    
    # Project Tracking
    project_status: str                 # inquiry → requirements → design → ... → delivered
    project_timeline: dict              # Timeline tracking
    estimated_cost: float               # Cost estimation
    assigned_team: dict                 # Team member assignments
    
    # Quality Metrics
    validation_errors: list[str]        # Code errors found
    warnings: list[str]                 # Warnings from QA
    retry_count: int                    # Number of retry attempts
    
    # Deliverables
    html_content: str                   # Final HTML output
    design_assets: dict                 # Design files
    documentation: str                  # Project documentation
    
    # Configuration
    framework_choice: str               # "Tailwind" or "Bootstrap"
    tech_stack: list[str]              # Technology choices
    llm_provider: str                   # Which LLM to use
    session_id: str                     # Session identifier
```

### State Flow

```
Initial State (from client request)
    ↓
Account Manager processes → Updates account_manager_notes
    ↓
UX Designer processes → Updates ux_designer_blueprint
    ↓
Design Team processes → Updates design_system
    ↓
Web Developer processes → Updates developer_code & html_content
    ↓
QA Tester processes → Updates qa_test_report, validation_errors
    ├─→ If PASSED → Project Manager
    └─→ If FAILED → Back to Web Developer
    ↓
Project Manager → Finalizes state & documentation
    ↓
Final State (with complete html_content)
```

---

## 🎭 Agent Architecture

### 1. Account Manager Agent

**Role:** Requirements clarification and analysis

```python
class AccountManager:
    @staticmethod
    def clarify_requirements(state: ServiceCompanyState) -> ServiceCompanyState:
        """
        Input: client_request (vague requirements from user)
        Process: Analyze for completeness, identify gaps
        Output: account_manager_notes (structured analysis)
        Side Effect: May raise Interrupt if clarification needed
        """
        # 1. Send requirements to LLM
        # 2. LLM analyzes for clarity
        # 3. If unclear → Extract questions → Raise Interrupt
        # 4. If clear → Continue to next agent
        # 5. Return updated state
```

**LLM Prompt Focuses:**
- Understanding project scope
- Identifying missing information
- Asking clarifying questions
- Assessing project complexity
- Estimating timeline

**State Updates:**
- `account_manager_notes` - JSON with analysis and questions
- `project_status` → "requirements"

---

### 2. UX/UI Designer Agent

**Role:** Design blueprint and user experience

```python
class UXDesigner:
    @staticmethod
    def create_design_blueprint(state: ServiceCompanyState) -> ServiceCompanyState:
        """
        Input: account_manager_notes (requirements)
        Process: Design page structure, user flows, wireframes
        Output: ux_designer_blueprint (design specification)
        """
        # 1. Read requirements from account manager notes
        # 2. Design page structure and hierarchy
        # 3. Define user flows and interactions
        # 4. Consider accessibility
        # 5. Plan responsive breakpoints
        # 6. Return updated state
```

**LLM Prompt Focuses:**
- Page structure and hierarchy
- User flows and journeys
- Component definitions
- Accessibility considerations
- Mobile responsiveness

**State Updates:**
- `ux_designer_blueprint` - JSON with wireframes and flows
- `project_status` → "design"

---

### 3. Design Team Agent

**Role:** Visual design system and aesthetics

```python
class DesignTeam:
    @staticmethod
    def define_design_system(state: ServiceCompanyState) -> ServiceCompanyState:
        """
        Input: ux_designer_blueprint (design)
        Process: Create design tokens, colors, fonts, spacing
        Output: design_system (complete design tokens)
        """
        # 1. Read UX blueprint
        # 2. Define color palette
        # 3. Select typography
        # 4. Create spacing scale
        # 5. Define component tokens
        # 6. Ensure brand consistency
        # 7. Return updated state
```

**LLM Prompt Focuses:**
- Color palette (primary, secondary, accent, neutral)
- Typography (fonts, sizes, weights)
- Spacing system (8px grid)
- Component styles
- Brand voice and identity

**State Updates:**
- `design_system` - Dict with all design tokens
- Design system example:
  ```python
  {
    "colors": {
      "primary": "#667eea",
      "secondary": "#764ba2",
      ...
    },
    "typography": {
      "heading_font": "Inter",
      "body_font": "Inter",
      "sizes": {"h1": "2.5rem", ...}
    },
    "spacing": {
      "unit": "8px",
      "scale": ["0", "8px", "16px", ...]
    }
  }
  ```

---

### 4. Web Developer Agent

**Role:** Frontend code generation

```python
class WebDeveloper:
    @staticmethod
    def develop_frontend(state: ServiceCompanyState) -> ServiceCompanyState:
        """
        Input: design_system + ux_designer_blueprint
        Process: Generate production-ready HTML/CSS
        Output: html_content (complete website code)
        """
        # 1. Read design system and UX blueprint
        # 2. Generate semantic HTML5
        # 3. Apply design system via Tailwind CSS
        # 4. Implement responsive design
        # 5. Add accessibility features
        # 6. Optimize performance
        # 7. Return updated state
```

**LLM Prompt Focuses:**
- HTML5 semantic structure
- Tailwind CSS implementation
- Responsive design patterns
- Accessibility (ARIA labels)
- Performance optimization
- SEO best practices

**State Updates:**
- `developer_code` - Raw HTML code
- `html_content` - Formatted HTML for preview
- `project_status` → "development"

---

### 5. QA Tester Agent

**Role:** Quality validation and testing

```python
class QATester:
    @staticmethod
    def validate_deliverable(state: ServiceCompanyState) -> ServiceCompanyState:
        """
        Input: html_content (generated code)
        Process: Comprehensive validation
        Output: qa_test_report (validation results)
        Decision: PASSED → continue | FAILED → retry
        """
        # 1. Validate HTML syntax
        # 2. Check responsive design
        # 3. Verify accessibility (WCAG)
        # 4. Security scan
        # 5. Performance check
        # 6. Browser compatibility
        # 7. Return results & decision
```

**LLM Prompt Focuses:**
- HTML structure validation
- CSS implementation check
- Accessibility compliance
- Performance best practices
- Browser compatibility
- Security vulnerabilities
- User experience quality

**State Updates:**
- `qa_test_report` - JSON with findings
- `validation_errors` - List of errors
- `warnings` - List of warnings
- `project_status` → "testing" or back to "development"
- `retry_count` - Incremented if retry needed

---

### 6. Project Manager Agent

**Role:** Orchestration and delivery

```python
class ProjectManager:
    @staticmethod
    def finalize_delivery(state: ServiceCompanyState) -> ServiceCompanyState:
        """
        Input: all completed work
        Process: Package deliverables
        Output: final documentation
        """
        # 1. Verify all deliverables present
        # 2. Create delivery summary
        # 3. Generate documentation
        # 4. Package all artifacts
        # 5. Return updated state
```

**State Updates:**
- `documentation` - Complete delivery package
- `project_status` → "delivered"

---

## 🔄 Workflow Graph

### Graph Structure

```python
def build_service_company_workflow():
    workflow = StateGraph(ServiceCompanyState)
    
    # Add nodes (agents)
    workflow.add_node("account_manager", AccountManager.clarify_requirements)
    workflow.add_node("ux_designer", UXDesigner.create_design_blueprint)
    workflow.add_node("design_team", DesignTeam.define_design_system)
    workflow.add_node("developer", WebDeveloper.develop_frontend)
    workflow.add_node("qa_tester", QATester.validate_deliverable)
    workflow.add_node("project_manager", ProjectManager.finalize_delivery)
    
    # Add edges (connections)
    workflow.add_edge(START, "account_manager")
    workflow.add_edge("account_manager", "ux_designer")
    workflow.add_edge("ux_designer", "design_team")
    workflow.add_edge("design_team", "developer")
    # Conditional edge from developer to qa_tester
    # Conditional edge from qa_tester
    workflow.add_edge("project_manager", END)
    
    return workflow.compile()
```

### Visual Representation

```
                    START
                      │
                      ▼
            ┌─────────────────────┐
            │  Account Manager    │
            │ (Clarify Req)       │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   UX/UI Designer    │
            │ (Design Blueprint)  │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │    Design Team      │
            │ (Design System)     │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   Web Developer     │
            │ (Generate HTML)     │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │    QA Tester        │
            │ (Validate Code)     │
            └──────┬──────────────┘
                   │
        ┌──────────┴──────────┐
        │ (PASS)  │ (FAIL)    │
        ▼         └───────────┘
    ┌─────────────────────┐   │
    │ Project Manager     │   │
    │ (Deliver)          │   │
    └─────────┬──────────┘   │
              │              │
              │    retry     │
              │ (max 2x)     │
              │              │
              └──────────────▶ Developer
                       
              ▼
           END
```

---

## 🔗 Edge Connections

### Linear Edges (Always Follow This Path)

```python
workflow.add_edge(START, "account_manager")
workflow.add_edge("account_manager", "ux_designer")
workflow.add_edge("ux_designer", "design_team")
workflow.add_edge("design_team", "developer")
workflow.add_edge("project_manager", END)
```

These edges are **unconditional** - they always execute.

### Conditional Edges (Route Based on State)

```python
def qa_decision(state: ServiceCompanyState) -> str:
    """Decide where to route based on QA results"""
    results = json.loads(state.get("qa_test_report", "{}"))
    
    if results.get("validation_status") == "passed":
        return "project_manager"  # Delivery path
    elif state.get("retry_count", 0) < 2:
        return "developer"        # Fix & retry path
    else:
        return "project_manager"  # Accept and deliver despite failures

workflow.add_conditional_edges(
    "qa_tester",
    qa_decision
)

workflow.add_edge("developer", "qa_tester")  # After fix, test again
```

### Interrupt Routing

When an agent raises `Interrupt`:

```python
try:
    result = workflow.invoke(state)
except Interrupt as e:
    # Pause workflow
    # Collect human input
    # Resume with updated state
    result = workflow.invoke(updated_state)
```

---

## 💾 State Persistence

### Session Storage

```python
# In app.py
sessions: Dict[str, Dict] = {}

# When creating session
sessions[session_id] = {
    "state": ServiceCompanyState(...),
    "messages": [],
    "created_at": datetime.now()
}

# Update state after each node
sessions[session_id]["state"] = updated_state
```

### State Transitions

```
Session Created
├─ state: ServiceCompanyState (initial)
├─ messages: []
└─ created_at: timestamp

After Account Manager
├─ state: {account_manager_notes: "..."}
├─ messages: [{user_msg, bot_response}]
└─ created_at: timestamp

After UX Designer
├─ state: {account_manager_notes: "...", ux_designer_blueprint: "..."}
├─ messages: [{...}, {...}]
└─ created_at: timestamp

... continues through all agents ...

Final State
├─ state: {all_fields_populated}
├─ messages: [{...}, ..., {...}]
└─ created_at: timestamp
```

---

## 🛑 Interrupt Handling

### When Interrupts Occur

Interrupts are raised when:
1. **Account Manager** needs clarification on vague requirements
2. **QA Tester** finds critical errors requiring developer input
3. **Human decides** to pause workflow

### Interrupt Flow

```python
# In agent code
if needs_clarification:
    questions = ["Q1", "Q2", "Q3"]
    raise Interrupt(f"Need clarification: {questions}")

# In API endpoint
try:
    result = workflow.invoke(state)
except Interrupt as e:
    # Extract questions from exception message
    return {
        "success": True,
        "response": str(e),
        "state": {
            "needs_clarification": True,
            "questions": extracted_questions
        }
    }

# UI shows form asking for answers
# User fills answers and submits

# In clarification endpoint
state["manager_clarifications"] = [
    {"question": "Q1", "answer": "User's answer 1"},
    {"question": "Q2", "answer": "User's answer 2"},
    ...
]
result = workflow.invoke(state)  # Resume from interruption
```

---

## 🔄 Execution Flow

### Example: Complete User Request

```
1. USER SUBMITS
   "Create a modern tech startup landing page"
   
2. API CREATES SESSION
   ├─ session_id: "abc123"
   ├─ initial_state: ServiceCompanyState
   └─ status: "inquiry"

3. ACCOUNT MANAGER RUNS
   ├─ Input: client_request
   ├─ Process: Analyze requirements
   ├─ Output: account_manager_notes
   └─ Status: "requirements"
   
   State: {..., account_manager_notes: "Analysis...", ...}

4. UX/UI DESIGNER RUNS
   ├─ Input: account_manager_notes
   ├─ Process: Design page layout
   ├─ Output: ux_designer_blueprint
   └─ Status: "design"
   
   State: {..., ux_designer_blueprint: "Wireframe...", ...}

5. DESIGN TEAM RUNS
   ├─ Input: ux_designer_blueprint
   ├─ Process: Create design system
   ├─ Output: design_system (dict)
   └─ Status: "design"
   
   State: {..., design_system: {colors: {...}, fonts: {...}}, ...}

6. WEB DEVELOPER RUNS
   ├─ Input: design_system + ux_designer_blueprint
   ├─ Process: Generate HTML
   ├─ Output: html_content
   └─ Status: "development"
   
   State: {..., html_content: "<html>...</html>", ...}

7. QA TESTER RUNS
   ├─ Input: html_content
   ├─ Process: Validate code
   ├─ Output: qa_test_report
   ├─ Decision: PASS or FAIL
   └─ Status: "testing"
   
   If FAIL and retry < 2:
   └─ Loop back to step 6 (Developer fixes)
   
   If PASS or retry >= 2:
   └─ Continue to step 8

8. PROJECT MANAGER RUNS
   ├─ Input: All completed work
   ├─ Process: Package deliverables
   ├─ Output: documentation
   └─ Status: "delivered"
   
   State: {..., documentation: "Package...", ...}

9. RETURN TO USER
   ├─ HTML ready for preview
   ├─ Can download as file
   └─ Can request improvements
```

---

## 🚀 Advanced Patterns

### Pattern 1: Conditional Looping

```python
def decide_retry(state):
    errors = state.get("validation_errors", [])
    retry_count = state.get("retry_count", 0)
    
    if errors and retry_count < 2:
        state["retry_count"] = retry_count + 1
        return "developer"  # Loop back
    else:
        return "project_manager"  # Continue

workflow.add_conditional_edges("qa_tester", decide_retry)
```

### Pattern 2: Dynamic Agent Selection

```python
def route_by_complexity(state):
    complexity = analyze_complexity(state["client_request"])
    
    if complexity == "high":
        return "ux_designer_advanced"  # Use advanced designer
    else:
        return "ux_designer_basic"     # Use basic designer
```

### Pattern 3: State Filtering

```python
def create_lightweight_state(state):
    """Remove unnecessary fields for downstream agents"""
    return {
        k: v for k, v in state.items()
        if k in ["ux_designer_blueprint", "design_system", ...]
    }
```

### Pattern 4: Parallel Agent Execution

```python
# LangGraph doesn't support true parallelism, but can simulate:
def run_parallel_agents(state):
    # Run multiple agents sequentially but treat as parallel
    state = agent_a(state)
    state = agent_b(state)  # Runs independently
    return state
```

---

## 🔍 Debugging

### Enable Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# In agents
logger.debug(f"Account Manager input: {state}")
logger.info(f"Requirements analysis complete")
logger.warning(f"Clarification needed: {questions}")
```

### Trace Visualization

LangSmith provides visual traces:

```
1. Open https://smith.langchain.com/projects/IT-Service-WebDev
2. Click on a trace
3. See:
   ├─ Input to each agent
   ├─ Output from each agent
   ├─ Token usage
   ├─ Execution time
   └─ Any errors
```

### State Inspection

```python
# Print state at any point
import json
print(json.dumps(state, indent=2, default=str))

# Check specific fields
print(f"HTML length: {len(state.get('html_content', ''))}")
print(f"Errors: {state.get('validation_errors', [])}")
print(f"Status: {state.get('project_status')}")
```

### Unit Testing Agents

```python
def test_account_manager():
    state = ServiceCompanyState(
        client_id="test",
        client_request={
            "client_name": "Test",
            "project_description": "Test website",
            "budget_tier": "standard",
            "timeline": "7"
        },
        # ... other fields ...
    )
    
    result = AccountManager.clarify_requirements(state)
    
    assert result.get("project_status") == "requirements"
    assert len(result.get("account_manager_notes", "")) > 0
```

---

## 📚 References

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **LangGraph Concepts**: https://langchain-ai.github.io/langgraph/concepts/
- **State Graphs**: https://langchain-ai.github.io/langgraph/concepts/state_graph/
- **Interrupts**: https://langchain-ai.github.io/langgraph/concepts/interrupts/

---

**Last Updated:** November 5, 2024
**Version:** 2.0
