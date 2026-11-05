# Multi-Agent AI HTML Generation System

A sophisticated LangChain + LangGraph-based multi-agent system that generates fully functional, production-ready HTML files styled with Tailwind CSS or Bootstrap based on natural language prompts.

## 🏗️ Architecture Overview

### Graph State Definition
The system maintains a unified state (`AgentState`) that flows through six specialized agents:

```python
AgentState:
  - user_prompt: str                    # Initial user request
  - manager_clarifications: list        # Q&A history for vague requests
  - final_specifications: str           # Approved requirements document
  - ux_blueprint: str                   # Structural layout and user journey
  - design_system: str                  # Colors, typography, and styling rules
  - framework_choice: str               # "Tailwind" or "Bootstrap"
  - html_content: str                   # Generated HTML code
  - validation_errors: list             # Syntax/CDN validation issues
  - retry_count: int                    # Self-correction attempt counter
```

### Six Specialized Agents

#### 1. **Manager Agent** (`clarify_requirements`)
- **Purpose**: Analyzes user prompts for clarity
- **Action**: 
  - If prompt is clear → writes `final_specifications`
  - If vague → generates 3-5 clarifying questions
  - Triggers a **breakpoint interrupt** to collect user answers
- **Output**: `final_specifications` or interrupt for human input

#### 2. **UI/UX Agent** (`design_user_journey`)
- **Purpose**: Translates specifications into structural design
- **Action**: Creates detailed UX blueprint with:
  - Page structure and sections
  - User journey and interaction flow
  - Layout hierarchy (header, footer, sidebars, etc.)
  - Key components and placement
- **Constraint**: Focuses on structure only—no colors, fonts, or CSS
- **Output**: `ux_blueprint`

#### 3. **Web Designer Agent** (`define_aesthetics`)
- **Purpose**: Converts blueprint into actionable design system
- **Action**:
  - Defines color palette with hex codes
  - Specifies typography (fonts, sizes, weights)
  - Creates spacing system
  - Documents component styles with exact class names
  - Automatically selects framework: Tailwind (modern/custom) or Bootstrap (standard components)
- **Output**: `design_system`, `framework_choice`

#### 4. **Code Generator** (`generate_html`)
- **Purpose**: Generates production-ready HTML
- **Critical Requirements**:
  - ✅ Output raw HTML only (NO markdown formatting)
  - ✅ Inject official CDN links in `<head>` tag
  - ✅ Proper `<!DOCTYPE html>`, `<html>`, `<head>`, `<body>` tags
  - ✅ Semantic HTML5 with proper structure
  - ✅ Uses exact classes from design system
- **On Retry**: Receives previous validation errors as context for self-correction
- **Output**: `html_content`

#### 5. **Output Validator** (`validate_code`)
- **Purpose**: Ensures HTML quality and completeness
- **Validation Checks**:
  1. `<!DOCTYPE html>` present
  2. `<html>`, `<head>`, `<body>` tags properly closed
  3. Correct CDN links for selected framework
  4. No markdown code block remnants (```)
- **On Errors**: Increments `retry_count` and routes back to Code Generator
- **Output**: `validation_errors` list

#### 6. **File Writer** (`save_file`)
- **Purpose**: Persists validated HTML to disk
- **Action**: Writes `html_content` to `output.html`
- **Output**: File created on disk

### Execution Flow & Routing

```
START
  ↓
[Manager Agent]
  ├─→ Clear? → [UI/UX Agent]
  └─→ Vague? → 🔴 INTERRUPT (wait for user answers) → Resume
                          ↓
                     [UI/UX Agent]
                          ↓
                   [Web Designer Agent]
                          ↓
                   [Code Generator]
                          ↓
                   [Output Validator]
                          ├─→ No errors? → [File Writer] → END
                          ├─→ Errors + retry_count < 3? → [Code Generator] (retry)
                          └─→ retry_count ≥ 3? → END (fail)
```

### Human-in-the-Loop Interrupts

When the Manager Agent detects a vague requirement, the graph raises an `Interrupt` exception:
- System pauses execution
- User is prompted with clarifying questions
- User provides answers
- Specifications are regenerated incorporating answers
- Workflow resumes from UI/UX Agent

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10+
- OpenAI API key

### Installation

```bash
# Clone repository
cd /workspaces/langchain-learning

# Install dependencies
pip install langchain langgraph langchain-openai python-dotenv

# Set up environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Environment Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk_your_actual_key_here
```

## 📖 Usage

### Quick Start - Clear Requirement

```python
python html_generation_agent.py
```

The default test prompt is clear:
```
"Create a modern landing page for a tech startup that sells AI tools. Include a hero 
section, features grid, testimonials, and a contact form."
```

### Testing with Vague Requirement

Edit the test prompts in `html_generation_agent.py`:

```python
test_prompts = [
    "Make a website",  # This will trigger clarification
]
```

Then run:
```python
python html_generation_agent.py
```

The system will ask:
1. What is the primary purpose of this website?
2. Who is your target audience?
3. What key features/sections should it include?
4. Any specific color or design preferences?
5. Should this be a single-page or multi-page site?

### Programmatic Usage

```python
from html_generation_agent import run_html_generation_workflow

user_request = """
Create a portfolio website for a digital designer. 
Include: hero section, project gallery, about me, and contact form.
Dark theme with vibrant accent colors.
"""

run_html_generation_workflow(user_request)
# → Generates output.html
```

## 📊 Example Output

### Input Prompt
```
"Create a modern landing page for a tech startup that sells AI tools."
```

### Graph Execution Log
```
================================================================================
🚀 MULTI-AGENT HTML GENERATION SYSTEM
================================================================================
User Prompt: Create a modern landing page for a tech startup...

--------------------------------------------------------------------------------
Executing workflow...
--------------------------------------------------------------------------------

================================================================================
NODE 1: MANAGER AGENT - CLARIFY REQUIREMENTS
================================================================================
Manager Analysis:
CLEAR: This request provides clear direction about...
✓ Requirements are clear. Proceeding with specifications.

================================================================================
NODE 2: UI/UX AGENT - DESIGN USER JOURNEY
================================================================================
UX Blueprint Created:
# Page Structure
## Header Section
- Navigation bar with logo and menu items
...
✓ UX blueprint design complete.

================================================================================
NODE 3: WEB DESIGNER AGENT - DEFINE AESTHETICS
================================================================================
Design System Created (Framework: Tailwind):
Color Palette:
- Primary: #3B82F6 (Modern Blue)
- Accent: #10B981 (Emerald Green)
...
✓ Design system defined.

================================================================================
NODE 4: CODE GENERATOR - GENERATE HTML
================================================================================
HTML Generated (length: 4892 chars)
Preview (first 300 chars):
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Tools Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-white">
...
✓ HTML generation complete.

================================================================================
NODE 5: OUTPUT VALIDATOR - VALIDATE CODE
================================================================================
✓ All validation checks passed!

================================================================================
NODE 6: FILE WRITER - SAVE OUTPUT
================================================================================
✓ HTML file saved to: output.html
  File size: 4892 bytes
  Framework: Tailwind

================================================================================
✅ WORKFLOW COMPLETED SUCCESSFULLY
================================================================================
Generated HTML file: output.html
```

### Generated output.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Tools Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-white">
    <!-- Navigation -->
    <nav class="bg-slate-800 border-b border-slate-700">
        <div class="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
            <div class="text-2xl font-bold text-blue-400">AI Tools</div>
            <div class="space-x-6">
                <a href="#features" class="hover:text-blue-400">Features</a>
                <a href="#testimonials" class="hover:text-blue-400">Testimonials</a>
                <a href="#contact" class="hover:text-blue-400">Contact</a>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="bg-gradient-to-r from-slate-900 via-blue-900 to-slate-900 py-20">
        <div class="max-w-6xl mx-auto px-4 text-center">
            <h1 class="text-5xl font-bold mb-4 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">
                Powerful AI Tools for Your Business
            </h1>
            <p class="text-xl text-slate-300 mb-8">Transform your workflows with cutting-edge artificial intelligence</p>
            <button class="bg-blue-500 hover:bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold">
                Get Started Free
            </button>
        </div>
    </section>

    <!-- Features Grid -->
    <section id="features" class="py-16 bg-slate-800">
        <div class="max-w-6xl mx-auto px-4">
            <h2 class="text-3xl font-bold text-center mb-12">Why Choose Us?</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div class="bg-slate-700 p-6 rounded-lg">
                    <div class="text-3xl mb-4">⚡</div>
                    <h3 class="text-xl font-bold mb-2">Lightning Fast</h3>
                    <p class="text-slate-300">Process data in milliseconds with our optimized algorithms</p>
                </div>
                <div class="bg-slate-700 p-6 rounded-lg">
                    <div class="text-3xl mb-4">🔒</div>
                    <h3 class="text-xl font-bold mb-2">Secure</h3>
                    <p class="text-slate-300">Enterprise-grade security with end-to-end encryption</p>
                </div>
                <div class="bg-slate-700 p-6 rounded-lg">
                    <div class="text-3xl mb-4">📊</div>
                    <h3 class="text-xl font-bold mb-2">Scalable</h3>
                    <p class="text-slate-300">Grow from startup to enterprise without infrastructure changes</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Testimonials -->
    <section id="testimonials" class="py-16 bg-slate-900">
        <div class="max-w-6xl mx-auto px-4">
            <h2 class="text-3xl font-bold text-center mb-12">What Our Customers Say</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div class="bg-slate-800 p-6 rounded-lg border-l-4 border-blue-500">
                    <p class="text-slate-300 mb-4">"This tool has completely transformed our workflow. Highly recommended!"</p>
                    <p class="font-semibold">- Sarah Chen, CTO at TechCorp</p>
                </div>
                <div class="bg-slate-800 p-6 rounded-lg border-l-4 border-emerald-500">
                    <p class="text-slate-300 mb-4">"The best investment we made this year. ROI was immediate."</p>
                    <p class="font-semibold">- Michael Rodriguez, CEO at StartupXYZ</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Contact Form -->
    <section id="contact" class="py-16 bg-slate-800">
        <div class="max-w-2xl mx-auto px-4">
            <h2 class="text-3xl font-bold text-center mb-8">Get In Touch</h2>
            <form class="bg-slate-700 p-8 rounded-lg space-y-4">
                <input type="text" placeholder="Your Name" class="w-full bg-slate-600 text-white px-4 py-2 rounded">
                <input type="email" placeholder="Your Email" class="w-full bg-slate-600 text-white px-4 py-2 rounded">
                <textarea placeholder="Your Message" rows="5" class="w-full bg-slate-600 text-white px-4 py-2 rounded"></textarea>
                <button type="submit" class="w-full bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg font-semibold">
                    Send Message
                </button>
            </form>
        </div>
    </section>

    <!-- Footer -->
    <footer class="bg-slate-900 border-t border-slate-700 py-8 text-center text-slate-400">
        <p>&copy; 2024 AI Tools Platform. All rights reserved.</p>
    </footer>
</body>
</html>
```

## 🔄 Retry & Self-Correction Loop

The validator automatically triggers retries for code generation errors:

1. **First Attempt**: Generator creates HTML
2. **Validation**: Validator checks for structural issues
3. **If Errors Found**:
   - Error messages passed back to Generator
   - `retry_count` incremented
   - Generator retries (up to 3 times)
4. **Max Retries Reached**: Graph terminates

Example retry prompt to generator:
```
Fix these validation errors from the previous attempt:
- Missing Tailwind CDN link (https://cdn.tailwindcss.com)
- HTML contains markdown code blocks (```)
```

## 🧪 Testing Scenarios

### Scenario 1: Clear Requirement (No Interrupts)
```python
prompt = "Create a professional portfolio page with dark theme and 3 featured projects"
# Expected: Flows directly through all 6 nodes without interruption
```

### Scenario 2: Vague Requirement (With Interrupts)
```python
prompt = "Make a website"
# Expected: Manager detects vagueness → Interrupt → User answers → Resume
```

### Scenario 3: Framework Selection
The system automatically chooses:
- **Tailwind CSS**: For modern, minimalist, custom designs
- **Bootstrap**: For standard components and quick deployment

### Scenario 4: Validation Retry
If the generated HTML has issues:
- First attempt fails validation → Generator retries with error context
- If still failing → Up to 2 more retries
- After 3 failures → Graph terminates with error

## 🛠️ Customization

### Modify Agent Behaviors
Edit the prompt templates in each node function to change:
- How the Manager asks clarifying questions
- UX/Design philosophy
- Code generation style
- Validation rules

### Add New Validation Rules
In `validate_code()`:
```python
# Check for mobile responsiveness
if "viewport" not in html:
    validation_errors.append("Missing viewport meta tag")

# Check for accessibility
if "lang=" not in html:
    validation_errors.append("Missing lang attribute on <html> tag")
```

### Extend State Fields
Add new TypedDict fields to `AgentState`:
```python
class AgentState(TypedDict):
    # ... existing fields ...
    mobile_design_notes: str
    accessibility_checklist: list[str]
```

## 🐛 Debugging

### Enable Verbose Logging
Modify the graph execution:
```python
for output in compiled_graph.stream(initial_state, config, stream_mode="debug"):
    print(output)
```

### Inspect State at Each Node
Add debugging in node functions:
```python
def clarify_requirements(state: AgentState) -> AgentState:
    print(f"Current state: {state}")
    # ... rest of function
```

### Test Individual Nodes
```python
from html_generation_agent import validate_code, AgentState

test_state: AgentState = {
    "html_content": "<html></html>",
    # ... other fields
}

result = validate_code(test_state)
print(result["validation_errors"])
```

## 📝 Output File

The system generates a single file: **`output.html`**

This file is:
- ✅ Fully functional and self-contained
- ✅ Single-file deployment ready
- ✅ Styled with Tailwind or Bootstrap (includes CDN)
- ✅ Semantic HTML5 compliant
- ✅ Responsive and mobile-friendly
- ✅ Validated and production-ready

Open it in any web browser to view.

## 🔐 Security Considerations

- ⚠️ User prompts are sent to OpenAI API
- ⚠️ Ensure OPENAI_API_KEY is never committed to version control
- ⚠️ Generated HTML is not sanitized for user inputs in forms
- ✅ All HTML is server-side generated (no client-side code execution risks)

## 📚 Dependencies

- **langchain**: LLM framework and prompt engineering
- **langgraph**: Graph state management and node orchestration
- **langchain-openai**: OpenAI model integration
- **python-dotenv**: Environment variable management

## 🚀 Performance Notes

- Manager clarification: ~5-10 seconds
- UX/Design phases: ~10-15 seconds each
- Code generation: ~15-30 seconds
- Validation: ~2-5 seconds
- **Total end-to-end**: ~45-90 seconds (no interrupts)

## 🤝 Contributing

To extend the system:
1. Add new nodes to the StateGraph
2. Define new State fields as needed
3. Update routing logic in conditional edges
4. Test interrupt handling with various prompts

## 📄 License

This project is provided as-is for educational and commercial use.

## 📞 Support

For issues or questions:
1. Check `.env` configuration
2. Verify OpenAI API key is valid
3. Review generated HTML in `output.html`
4. Check validation errors in console output

---

**Happy HTML generating! 🎉**
