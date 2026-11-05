# Multi-Agent AI HTML Generation System - Complete Guide

A sophisticated LangChain + LangGraph-based multi-agent system that generates fully functional, production-ready HTML files styled with Tailwind CSS or Bootstrap based on natural language prompts.

**Now with support for multiple LLM providers (OpenAI, OpenRouter, Anthropic) and Qdrant vector database integration!**

## 🎯 Quick Start

### 1. Install Dependencies
```bash
cd /workspaces/langchain-learning
pip install langchain langgraph langchain-openai python-dotenv
```

### 2. Configure LLM Provider

Choose ONE of these LLM providers:

#### Option A: OpenRouter (Recommended for cost optimization)
```env
# .env
OPENROUTER_API_KEY=sk_your_openrouter_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
```

#### Option B: OpenAI (GPT-4)
```env
# .env
OPENAI_API_KEY=sk_your_openai_key_here
```

#### Option C: Anthropic (Claude)
```env
# .env
ANTHROPIC_API_KEY=sk_ant_your_anthropic_key_here
```

### 3. (Optional) Configure Qdrant Vector Database
```env
# .env
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_api_key_here
QDRANT_COLLECTION=langchain-learning
```

### 4. Run the System

**With Mock Data (No API Key Required):**
```bash
python test_html_generation.py
```

**With Real LLM (Requires API Key):**
```bash
python html_generation_agent.py
```

---

## 🏗️ Architecture Overview

### Six-Agent Orchestration Pipeline

```
User Prompt
    ↓
[1] Manager Agent (Requirement Clarification)
    ├─→ Clear? → Proceed
    └─→ Vague? → 🔴 INTERRUPT (Wait for user clarification)
         ↓
    [2] UI/UX Agent (Design Blueprint)
         ↓
    [3] Web Designer Agent (Aesthetics & Framework Selection)
         ↓
    [4] Code Generator (HTML Production)
         ↓
    [5] Output Validator (Quality Checks)
         ├─→ Valid? → [6] File Writer
         ├─→ Errors + Retries < 3? → [4] Code Generator (Retry)
         └─→ Retries ≥ 3? → END (Fail)
              ↓
         [6] File Writer (Save + Database Storage)
              ↓
         output.html + Qdrant Metadata
```

### State Flow Across Agents

```python
AgentState:
  user_prompt              # "Create a modern landing page..."
  manager_clarifications   # [{question, answer}, ...]
  final_specifications     # Approved requirements doc
  ux_blueprint            # Structural layout + journey
  design_system           # Colors, typography, classes
  framework_choice        # "Tailwind" or "Bootstrap"
  html_content            # Generated HTML code
  validation_errors       # List of issues found
  retry_count             # Self-correction attempts
  llm_provider            # "openai" | "openrouter" | "anthropic"
  session_id              # Unique session identifier
```

---

## 🔌 LLM Provider Configuration

### Automatic Provider Detection

The system automatically selects the first available provider in this order:
1. **OpenRouter** (if `OPENROUTER_API_KEY` is set)
2. **OpenAI** (if `OPENAI_API_KEY` is set)
3. **Anthropic** (if `ANTHROPIC_API_KEY` is set)

### Manual Provider Selection

Specify the provider explicitly:

```python
from html_generation_agent import run_html_generation_workflow

# Use OpenRouter
run_html_generation_workflow(
    "Create a landing page...",
    llm_provider="openrouter"
)

# Use OpenAI
run_html_generation_workflow(
    "Create a landing page...",
    llm_provider="openai"
)

# Use Anthropic
run_html_generation_workflow(
    "Create a landing page...",
    llm_provider="anthropic"
)
```

### Provider Comparison

| Feature | OpenAI | OpenRouter | Anthropic |
|---------|--------|-----------|-----------|
| Model | GPT-4 | GPT-4o-mini (default) | Claude 3.5 Sonnet |
| Cost | $$$ | $ | $$ |
| Speed | Fast | Very Fast | Very Fast |
| Quality | Excellent | Excellent | Excellent |
| Setup | Simple | Simple | Simple |

**Recommendation**: Use **OpenRouter** for production (best cost-quality balance).

---

## 📦 Database Integration (Qdrant)

### What Gets Stored?

When Qdrant is configured, the system stores:
- **Timestamp**: When the page was generated
- **Session ID**: Unique identifier for tracing
- **User Prompt**: Original user request
- **Final Specifications**: Approved requirements
- **Framework Choice**: Tailwind or Bootstrap
- **LLM Provider**: Which provider was used
- **HTML Metadata**: Length, structure info

### Why Use It?

1. **Audit Trail**: Track all generated pages
2. **Pattern Recognition**: Find what works well
3. **Quick Retrieval**: Search previous generations
4. **Quality Metrics**: Analyze generation success rates
5. **Cost Analysis**: Track usage by provider

### Set Up Qdrant

#### Local Docker Setup
```bash
docker run -p 6333:6333 qdrant/qdrant:latest
```

#### Cloud Qdrant
```bash
# Sign up at https://qdrant.tech/
# Get your cluster URL and API key
```

#### Configure in .env
```env
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_api_key_here
QDRANT_COLLECTION=langchain-learning
```

#### Verify Connection
```python
from html_generation_agent import DatabaseConfig

if DatabaseConfig.is_configured():
    client = DatabaseConfig.get_client()
    print("✓ Qdrant connected!")
else:
    print("⚠️  Qdrant not configured")
```

---

## 👥 Agent Specifications

### 1. Manager Agent (`clarify_requirements`)
**Role**: Understand and validate user intent

**Process**:
- Analyzes user prompt for clarity
- Extracts key requirements
- Identifies missing information

**Decision Tree**:
```
Is the prompt CLEAR and SPECIFIC?
├─→ YES: Write final_specifications
└─→ NO: Generate 3-5 clarifying questions
         ↓
         🔴 Interrupt: Wait for user answers
         ↓
         Resume with updated specifications
```

**Example Clarifications**:
- "What is the primary purpose of this website?"
- "Who is your target audience?"
- "What key sections/features should it include?"
- "Any specific color or design preferences?"
- "Mobile-first or desktop-first design?"

### 2. UI/UX Agent (`design_user_journey`)
**Role**: Create structural blueprint without styling

**Output**: Document with:
- Page structure and sections
- User journey and flows
- Layout hierarchy
- Component placement
- Navigation paths

**Key Constraint**: Pure structure (NO colors, fonts, or CSS)

### 3. Web Designer Agent (`define_aesthetics`)
**Role**: Create production-ready design system

**Output**: Design system including:
- **Color Palette**: Hex codes with semantic meanings
- **Typography**: Font selections, sizes, weights
- **Spacing System**: Margin/padding units
- **Component Styles**: How each element should look
- **Framework Decision**:
  - Tailwind: For modern, custom, minimalist designs
  - Bootstrap: For standard components, quick deployment

**Example Design System**:
```
Color Palette:
- Primary: #3B82F6 (Blue for main CTAs)
- Success: #10B981 (Green for positive actions)
- Warning: #F59E0B (Orange for alerts)

Typography:
- Headlines: Bold, sans-serif
- Hero H1: 3rem (48px)
- Body: Regular, 1rem (16px)

Components:
- Button: bg-blue-500 hover:bg-blue-600 px-8 py-3 rounded-lg
- Card: bg-white shadow-md p-6 rounded-lg
```

### 4. Code Generator (`generate_html`)
**Role**: Produce production-ready HTML

**Critical Constraints**:
✅ Raw HTML only (NO markdown)
✅ Official CDN links in `<head>`
✅ Proper DOCTYPE, html, head, body tags
✅ Semantic HTML5 structure
✅ Responsive design
✅ Exact classes from design system

**On Retry**: Receives previous validation errors as context

**CDN Links Injected**:
- **Tailwind**: `<script src="https://cdn.tailwindcss.com"></script>`
- **Bootstrap**: CDN CSS and JS bundles

### 5. Output Validator (`validate_code`)
**Role**: Ensure code quality and completeness

**Validation Checks**:
1. ✓ `<!DOCTYPE html>` present
2. ✓ `<html>`, `<head>`, `<body>` tags exist
3. ✓ Correct CDN links for framework
4. ✓ No markdown code block remnants
5. ✓ Proper tag closure
6. ✓ Viewport meta tag (mobile responsiveness)
7. ✓ Character encoding declared

**Retry Logic**:
- Error + `retry_count < 3` → Back to Code Generator
- No errors → Proceed to File Writer
- `retry_count ≥ 3` → Fail and report errors

### 6. File Writer (`save_file`)
**Role**: Persist HTML and metadata

**Actions**:
1. Write HTML to `output.html`
2. Store metadata in Qdrant (if configured)
3. Log session information

**Session Info**:
- File size and byte count
- Framework used
- LLM provider used
- Session ID for tracing

---

## 🧪 Testing & Examples

### Example 1: Basic Generation (Clear Requirement)
```python
from html_generation_agent import run_html_generation_workflow

prompt = """
Create a professional portfolio website for a digital designer.
Include: hero section, project gallery (6 items), about me section, and contact form.
Dark theme with gold accents. Use Tailwind CSS.
"""

run_html_generation_workflow(prompt)
```

**Expected Flow**: Smooth progression through all 6 nodes without interrupts.

### Example 2: With Clarification (Vague Requirement)
```python
prompt = "Make a website"

run_html_generation_workflow(prompt)
```

**Expected Flow**:
1. Manager detects vagueness
2. 🔴 System interrupts and asks questions
3. User provides answers
4. System resumes with clarified specifications

### Example 3: Specific Provider Selection
```python
# Force OpenRouter
run_html_generation_workflow(
    "Create a landing page for a fitness app",
    llm_provider="openrouter"
)

# Force Anthropic
run_html_generation_workflow(
    "Create a landing page for a fitness app",
    llm_provider="anthropic"
)
```

### Example 4: With Database Tracking
```python
run_html_generation_workflow(
    "Create a landing page for a fitness app",
    use_database=True  # Store metadata in Qdrant
)
```

---

## 🔄 Retry & Self-Correction

The validation loop automatically corrects generation errors:

```
Attempt 1: Generate HTML
    ↓
Validate: Check for errors
    ├─→ No errors? → Save file ✓
    └─→ Errors found?
         ├─→ Error 1: Missing CDN link
         ├─→ Error 2: Incomplete HTML structure
         ↓
Attempt 2: Retry with error context
    "Fix these errors from attempt 1:
     - Missing Tailwind CDN link
     - Missing </html> closing tag"
    ↓
Validate: Check again
    ├─→ Success? → Save file ✓
    └─→ Still errors?
         ↓
Attempt 3: Final retry
    ↓
If still failing after attempt 3: Report failure
```

**Max Retries**: 3 attempts before giving up

---

## 📊 Generated Output Example

### Input Prompt
```
Create a modern landing page for a tech startup that sells AI tools. 
Include a hero section, features grid, testimonials, and a contact form.
```

### Generated Output Structure
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Tools - Modern AI Solutions</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <!-- Navigation with Tailwind -->
    <nav class="bg-slate-800 border-b border-slate-700">...</nav>
    
    <!-- Hero Section -->
    <section class="bg-gradient-to-b from-slate-900 via-blue-900 to-slate-900">...</section>
    
    <!-- Features Grid -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-8">...</section>
    
    <!-- Testimonials -->
    <section class="bg-slate-900">...</section>
    
    <!-- Contact Form -->
    <section class="py-20 bg-slate-800">
        <form class="space-y-4">...</form>
    </section>
    
    <!-- Footer -->
    <footer class="bg-slate-900 border-t border-slate-700">...</footer>
</body>
</html>
```

**Characteristics**:
- ✅ Self-contained single file
- ✅ Responsive mobile design
- ✅ Semantic HTML5
- ✅ Production-ready
- ✅ Zero dependencies (CSS via CDN)
- ✅ Accessible structure

---

## 🛠️ Configuration & Customization

### Modify Node Behaviors

Edit prompt templates to change agent behavior:

```python
# In clarify_requirements() function
prompt = ChatPromptTemplate.from_template("""
    Custom system prompt for Manager Agent.
    Can modify clarification question style, depth, etc.
""")
```

### Add Custom Validation Rules

```python
def validate_code(state: AgentState) -> AgentState:
    # ... existing checks ...
    
    # Add new check
    if "lang=" not in state["html_content"]:
        validation_errors.append("Missing lang attribute")
    
    if len(state["html_content"]) < 1000:
        validation_errors.append("HTML too short (< 1KB)")
    
    state["validation_errors"] = validation_errors
    return state
```

### Extend State with New Fields

```python
class AgentState(TypedDict):
    # ... existing fields ...
    performance_metrics: dict  # Add new field
    accessibility_score: int   # Add new field
    seo_checklist: list        # Add new field
```

### Change Retry Limit

```python
def should_retry_validation(state: AgentState) -> str:
    if state["retry_count"] >= 5:  # Increase from 3 to 5
        return "end"
    return "generate_html"
```

---

## 🐛 Debugging & Troubleshooting

### Check Provider Configuration
```bash
python -c "
from html_generation_agent import LLMConfig
print('Available providers:', LLMConfig.PROVIDERS)
print('Default provider:', LLMConfig.get_default_provider())
"
```

### Verify Database Connection
```python
from html_generation_agent import DatabaseConfig

print("Qdrant configured:", DatabaseConfig.is_configured())
if DatabaseConfig.is_configured():
    client = DatabaseConfig.get_client()
    print("✓ Connected to database")
```

### Inspect Generated State
Add debugging to node functions:
```python
def clarify_requirements(state: AgentState) -> AgentState:
    print(f"DEBUG - State at entry: {list(state.keys())}")
    print(f"DEBUG - User prompt: {state['user_prompt'][:100]}")
    # ... rest of function
```

### View Raw HTML Output
```bash
cat output.html | head -100
```

### Validate HTML Offline
```bash
# Install HTML validator
pip install html5lib

python -c "
import html5lib
with open('output.html') as f:
    html5lib.parse(f)
print('✓ Valid HTML5')
"
```

---

## 🚀 Performance Considerations

### Timing Breakdown
- Manager clarification: 5-10 seconds
- UX/Design phases: 10-15 seconds each
- Code generation: 15-30 seconds
- Validation: 2-5 seconds
- **Total end-to-end**: 45-90 seconds (no interrupts)

With clarification interrupts: Add human response time

### Cost Comparison by Provider

| Provider | Model | Est. Cost/Generation |
|----------|-------|---------------------|
| OpenAI | GPT-4 | ~$0.30 |
| OpenRouter | GPT-4o-mini | ~$0.02 |
| Anthropic | Claude 3.5 | ~$0.08 |

**OpenRouter is most cost-effective** for production use.

---

## 🔐 Security & Best Practices

### ⚠️ Security Considerations
- 🔒 Never commit `.env` to version control
- 🔒 Keep API keys in environment variables only
- 🔒 User prompts are sent to LLM provider
- 🔒 Qdrant database should be secured/private
- ⚠️ Generated HTML is not sanitized (no client-side validation)

### ✅ Best Practices
1. Use environment variables for all secrets
2. Regularly rotate API keys
3. Monitor API usage and costs
4. Use OpenRouter for cost control
5. Validate generated HTML before deployment
6. Consider adding CSP headers for security

---

## 📚 Dependencies

```
langchain           # LLM framework
langgraph          # Graph orchestration
langchain-openai   # OpenAI integration
langchain-anthropic # Anthropic integration
python-dotenv      # Environment management
qdrant-client      # Vector database client (optional)
```

### Installation
```bash
pip install langchain langgraph langchain-openai python-dotenv
pip install langchain-anthropic  # If using Anthropic
pip install qdrant-client         # If using Qdrant
```

---

## 🎯 Use Cases

1. **Rapid Prototyping**: Generate landing pages in seconds
2. **Template Generation**: Create baseline websites for customization
3. **Multi-variant Testing**: Generate different versions for A/B testing
4. **Educational**: Learn LangGraph agent orchestration patterns
5. **Automation**: Batch generate pages from specifications
6. **Cost Optimization**: Use OpenRouter for affordable generation

---

## 🤝 Extending the System

### Add New Agent Node
```python
def optimize_performance(state: AgentState) -> AgentState:
    """Add lighthouse performance optimization."""
    # Implementation
    return state

# Add to graph
graph.add_node("optimize_performance", optimize_performance)
graph.add_edge("validate_code", "optimize_performance")
```

### Add Multi-Language Support
```python
# Extend state
class AgentState(TypedDict):
    language: str  # "en", "es", "fr", etc.

# Modify prompts to include language
```

### Add SEO Agent
```python
def optimize_seo(state: AgentState) -> AgentState:
    """Add meta tags, structured data, sitemap."""
    # Implementation
    return state
```

---

## 📄 Output Files

### Main Output
- **`output.html`** - Generated website (single file, fully functional)

### Session Files (Optional with Qdrant)
- Metadata stored in Qdrant collection
- Queryable by timestamp, prompt, framework, etc.

---

## 🎓 Learning Resources

### LangGraph Concepts Used
- **StateGraph**: Multi-node orchestration
- **Conditional Edges**: Dynamic routing
- **Interrupts**: Human-in-the-loop
- **Message Streaming**: Event-driven updates

### Example Patterns
- Agent collaboration
- State management
- Error recovery
- Database integration

---

## 📞 Support & FAQ

### Q: No API keys configured?
**A**: Set OPENROUTER_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY in `.env`

### Q: How do I use a specific LLM provider?
**A**: Pass `llm_provider="openrouter"` to `run_html_generation_workflow()`

### Q: Can I store results in a database?
**A**: Yes! Configure QDRANT_URL and QDRANT_API_KEY in `.env`

### Q: What if generation fails after 3 retries?
**A**: Check validation errors, modify prompts, try with different provider

### Q: Can I use this in production?
**A**: Yes! Generated HTML is production-ready. Consider using OpenRouter for cost.

### Q: How do I modify the generated design?
**A**: Edit the `design_system` prompt in the Web Designer agent node

---

## 📈 Roadmap

- [ ] Add SEO optimization agent
- [ ] Add accessibility checker agent
- [ ] Multi-page site generation
- [ ] Component library export
- [ ] Design system persistence
- [ ] Analytics integration
- [ ] A/B test variant generation
- [ ] Performance optimization

---

**Happy HTML generating! 🚀**

*For questions or contributions, refer to the inline documentation in `html_generation_agent.py`*
