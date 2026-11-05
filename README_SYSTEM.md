# 🚀 Multi-Agent AI HTML Generation System

A production-ready LangChain + LangGraph-based multi-agent system that generates fully functional, styled HTML files from natural language prompts.

**Supports**: OpenAI, OpenRouter (recommended), Anthropic | **Database**: Qdrant Vector DB | **Styling**: Tailwind CSS & Bootstrap

---

## ⚡ Quick Start (2 minutes)

### 1. Install & Configure
```bash
# Install dependencies
pip install langchain langgraph langchain-openai python-dotenv

# Copy and configure environment
cp .env.example .env
# Edit .env and add ONE of:
#   OPENROUTER_API_KEY=sk_... (recommended - cheapest)
#   OPENAI_API_KEY=sk_...
#   ANTHROPIC_API_KEY=sk_ant_...
```

### 2. Run With Mock Data (No API Key Needed)
```bash
python test_html_generation.py
# ✓ Generates output.html with sample content
```

### 3. Run With Real LLM (Requires API Key)
```bash
python html_generation_agent.py
# Follow prompts and get generated HTML in output.html
```

---

## 📁 Project Structure

```
langchain-learning/
├── html_generation_agent.py        # Main system (6 agents orchestrated by LangGraph)
├── test_html_generation.py         # Mock test runner (no API key needed)
├── examples.py                     # Advanced usage patterns
├── output.html                     # Generated output file
├── .env.example                    # Environment template
├── .env                            # Your configuration (git-ignored)
│
├── HTML_GENERATION_SYSTEM.md       # Detailed architecture guide
├── MULTI_PROVIDER_GUIDE.md         # Provider setup & database integration
└── README.md                       # This file
```

---

## 🏗️ System Architecture

### Six-Agent Pipeline

```
                    START
                      ↓
        ┌─────────────────────────────┐
        │  1. MANAGER AGENT           │ ← Clarify requirements
        │     (clarify_requirements)  │
        └─────────────────────────────┘
              ↓                     ↓
          CLEAR?              VAGUE?
              ↓                     ↓
        Continue              🔴 INTERRUPT
                         (Wait for user answers)
                                     ↓
        ┌─────────────────────────────────────────┐
        │  2. UI/UX AGENT (design_user_journey)   │ ← Structural design
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  3. WEB DESIGNER (define_aesthetics)    │ ← Colors, fonts, framework
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  4. CODE GENERATOR (generate_html)      │ ← Raw HTML production
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  5. VALIDATOR (validate_code)           │ ← Quality checks
        └─────────────────────────────────────────┘
              ↓         ↓              ↓
          VALID?   ERRORS+    RETRY ≥ 3?
                  RETRIES<3
              ↓         ↓              ↓
         [6] FILE  [4] RETRY      ERROR
           WRITER    (Loop back)
              ↓
        ┌─────────────────────────────────────────┐
        │  6. FILE WRITER (save_file)             │ ← Save + DB storage
        │     Saves to output.html                │
        │     Stores metadata in Qdrant           │
        └─────────────────────────────────────────┘
              ↓
            END ✓
```

### State Flow

```python
AgentState = {
    'user_prompt': str,              # User's initial request
    'manager_clarifications': list,  # Q&A history
    'final_specifications': str,     # Approved requirements
    'ux_blueprint': str,             # Structural design
    'design_system': str,            # Colors, typography, classes
    'framework_choice': str,         # "Tailwind" or "Bootstrap"
    'html_content': str,             # Generated HTML
    'validation_errors': list,       # Issues found
    'retry_count': int,              # Self-correction attempts
    'llm_provider': str,             # Which LLM provider was used
    'session_id': str,               # Unique identifier
}
```

---

## 🔌 LLM Provider Setup

### Automatic Detection
The system automatically selects the first available provider:
1. **OpenRouter** (if `OPENROUTER_API_KEY` is set) ⭐ Recommended
2. **OpenAI** (if `OPENAI_API_KEY` is set)
3. **Anthropic** (if `ANTHROPIC_API_KEY` is set)

### Manual Selection
```python
# Force OpenRouter (most cost-effective)
run_html_generation_workflow(prompt, llm_provider="openrouter")

# Force OpenAI
run_html_generation_workflow(prompt, llm_provider="openai")

# Force Anthropic
run_html_generation_workflow(prompt, llm_provider="anthropic")
```

### Provider Comparison

| Feature | OpenRouter | OpenAI | Anthropic |
|---------|-----------|--------|-----------|
| **Cost/Gen** | ~$0.02 | ~$0.30 | ~$0.08 |
| **Speed** | Very Fast | Fast | Very Fast |
| **Quality** | Excellent | Excellent | Excellent |
| **Recommended** | ✅ YES | ✓ Good | ✓ Good |

**👉 Use OpenRouter for production (cheapest, fastest)**

---

## 📦 Database Integration (Optional)

### Store Metadata in Qdrant
When configured, the system stores generation metadata for analytics:

```env
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_api_key
QDRANT_COLLECTION=langchain-learning
```

### What Gets Stored
- Timestamp & Session ID
- User prompt & specifications
- Framework choice & LLM provider
- HTML size & generation success

### Setup Qdrant
```bash
# Local Docker
docker run -p 6333:6333 qdrant/qdrant:latest

# Or use cloud: https://qdrant.tech/cloud/
```

### Check Connection
```python
from html_generation_agent import DatabaseConfig
if DatabaseConfig.is_configured():
    print("✓ Qdrant connected!")
```

---

## 👥 Agent Details

### 1️⃣ Manager Agent
**Purpose**: Clarify user intent

- Analyzes prompt for clarity
- If clear → writes specifications
- If vague → asks 3-5 clarifying questions
- Triggers interrupt for human input

### 2️⃣ UI/UX Agent
**Purpose**: Create structural blueprint

- Defines page layout and sections
- Maps user journey and interactions
- Specifies component placement
- ⚠️ NO colors or CSS (structure only)

### 3️⃣ Web Designer Agent
**Purpose**: Create design system

- Chooses Tailwind or Bootstrap
- Defines color palette with hex codes
- Specifies typography (fonts, sizes)
- Lists exact CSS classes to use

### 4️⃣ Code Generator
**Purpose**: Produce HTML

- ✅ Raw HTML only (NO markdown)
- ✅ Injects official CDN links
- ✅ Semantic HTML5 structure
- ✅ Uses design system classes exactly
- On retry: Receives previous errors for self-correction

### 5️⃣ Output Validator
**Purpose**: Quality assurance

**Checks**:
- `<!DOCTYPE html>` present
- Proper HTML/head/body tags
- Correct CDN links for framework
- No markdown remnants (```)
- Mobile responsiveness meta tags

**Retry Logic**:
- Error + retries < 3 → Back to Code Generator
- No errors → Proceed to File Writer
- retries ≥ 3 → Fail with errors

### 6️⃣ File Writer
**Purpose**: Persist output

- Writes to `output.html`
- Stores metadata in Qdrant (if configured)
- Logs session information

---

## 📖 Usage Examples

### Example 1: Basic Generation (Clear Requirements)
```python
from html_generation_agent import run_html_generation_workflow

prompt = """Create a modern landing page for an AI startup.
Include:
- Hero section with headline and CTA
- Features grid (3 items)
- Customer testimonials (2)
- Contact form
- Dark theme with blue accents
- Use Tailwind CSS"""

run_html_generation_workflow(prompt)
# → Generates output.html
```

### Example 2: Vague Requirement (Triggers Clarification)
```python
# This will ask clarifying questions
run_html_generation_workflow("Make a website")

# System will ask:
# 1. What is the primary purpose?
# 2. Who is your target audience?
# 3. What key sections/features?
# 4. Color or design preferences?
# 5. Mobile or desktop first?

# You answer, system resumes...
```

### Example 3: Explicit Provider
```python
# Use OpenRouter (cheapest)
run_html_generation_workflow(prompt, llm_provider="openrouter")

# Use specific model
os.environ["OPENROUTER_MODEL"] = "anthropic/claude-3-sonnet"
run_html_generation_workflow(prompt, llm_provider="openrouter")
```

### Example 4: With Database Tracking
```python
run_html_generation_workflow(
    prompt,
    llm_provider="openrouter",
    use_database=True  # Store in Qdrant
)
```

### Example 5: Batch Generation
```python
prompts = [
    "Create a portfolio website...",
    "Create a restaurant website...",
    "Create a SaaS landing page...",
]

for prompt in prompts:
    run_html_generation_workflow(
        prompt,
        llm_provider="openrouter",  # Cost-effective
        use_database=True,           # Track all
    )
```

### Example 6: Check Provider Status
```python
from html_generation_agent import LLMConfig, DatabaseConfig

# Check LLM providers
print(f"Default provider: {LLMConfig.get_default_provider()}")

# Check database
print(f"Qdrant configured: {DatabaseConfig.is_configured()}")
```

---

## 🧪 Testing Without API Keys

### Mock Test (No API Required)
```bash
python test_html_generation.py
# Generates output.html with sample content
# Shows validation workflow
```

### Advanced Examples
```bash
python examples.py
# Shows 10 different usage patterns
# Provider configuration, batch processing, etc.
```

---

## 📊 Generated HTML Example

The system generates complete, self-contained HTML files:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Tools Platform</title>
    <script src="https://cdn.tailwindcss.com"></script> <!-- CDN injected -->
</head>
<body class="bg-slate-900 text-white">
    <!-- Navigation -->
    <nav class="bg-slate-800 border-b border-slate-700">
        ...
    </nav>
    
    <!-- Hero Section -->
    <section class="bg-gradient-to-b from-slate-900 via-blue-900">
        ...
    </section>
    
    <!-- Features -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-8">
        ...
    </section>
    
    <!-- Contact Form -->
    <section class="py-20">
        <form class="space-y-4">
            ...
        </form>
    </section>
    
    <!-- Footer -->
    <footer class="border-t border-slate-700">
        ...
    </footer>
</body>
</html>
```

**Characteristics**:
- ✅ Single file (no dependencies except CDN CSS)
- ✅ Responsive design (mobile-first)
- ✅ Semantic HTML5
- ✅ Production-ready
- ✅ Accessible structure
- ✅ Modern styling (Tailwind or Bootstrap)

---

## 🔄 Retry & Self-Correction

The validation loop automatically fixes errors:

```
Generation Attempt 1
    ↓ Validate
    ├─ Error: Missing CDN link
    ├─ Error: Incomplete body tag
    ↓
Generation Attempt 2 (with error context)
    ↓ Validate
    ├─ Error: Still missing viewport meta
    ↓
Generation Attempt 3 (final attempt)
    ↓ Validate
    ├─ Success! → Save file
    └─ Still failing → Report failure
```

**Max retries**: 3 attempts before giving up

---

## ⚙️ Configuration Files

### .env (Your Configuration)
```env
# Choose ONE LLM provider
OPENROUTER_API_KEY=sk_...
# OPENAI_API_KEY=sk_...
# ANTHROPIC_API_KEY=sk_ant_...

# Optional: Database
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...
QDRANT_COLLECTION=langchain-learning

# Optional: LangSmith tracing
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=...
```

### .env.example (Template)
Shows all available options with descriptions

---

## 🛠️ Advanced Customization

### Modify Agent Prompts
Edit prompt templates in each node function to change behavior:

```python
def clarify_requirements(state: AgentState) -> AgentState:
    prompt = ChatPromptTemplate.from_template("""
        YOUR CUSTOM PROMPT HERE
        Can customize clarification style, depth, etc.
    """)
    # ... rest of function
```

### Add Custom Validation Rules
```python
def validate_code(state: AgentState) -> AgentState:
    # ... existing checks ...
    
    # Add new check
    if len(state["html_content"]) < 1000:
        validation_errors.append("HTML too short")
    
    state["validation_errors"] = validation_errors
    return state
```

### Extend State with New Fields
```python
class AgentState(TypedDict):
    # ... existing fields ...
    seo_score: int          # Add new tracking
    performance_metrics: dict
    accessibility_level: str
```

---

## 📈 Performance & Costs

### Timing (Approximate)
- Manager clarification: 5-10s
- UX/Design phases: 10-15s each
- Code generation: 15-30s
- Validation: 2-5s
- **Total**: 45-90s (without human interrupts)

### Cost Comparison (Per Page)
| Provider | Cost | Speed | Quality |
|----------|------|-------|---------|
| OpenRouter | $0.02 | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ |
| Anthropic | $0.08 | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ |
| OpenAI | $0.30 | ⚡⚡ | ⭐⭐⭐⭐⭐ |

**Cost to generate 100 pages**:
- OpenRouter: $2
- Anthropic: $8
- OpenAI: $30

👉 **Use OpenRouter for production!**

---

## 🔐 Security Best Practices

✅ **Do**:
- Store API keys in `.env` (git-ignored)
- Use environment variables
- Rotate keys periodically
- Monitor API usage

❌ **Don't**:
- Commit `.env` to version control
- Share API keys
- Use keys in client-side code
- Store keys in logs

**Generated HTML**: Safe to deploy anywhere (no embedded secrets)

---

## 🧠 System Capabilities

| Feature | Support | Details |
|---------|---------|---------|
| **LLM Providers** | 3 | OpenAI, OpenRouter, Anthropic |
| **Framework Choices** | 2 | Tailwind CSS, Bootstrap |
| **Database** | Qdrant | Optional metadata storage |
| **Human-in-Loop** | Yes | Interrupt for clarifications |
| **Self-Correction** | 3 retries | Auto-fix validation errors |
| **Single File Output** | Yes | Fully self-contained HTML |
| **Responsive Design** | Yes | Mobile-first by default |
| **Accessible HTML** | Yes | Semantic tags, proper structure |

---

## 📚 Documentation

1. **HTML_GENERATION_SYSTEM.md** - Complete architecture (agents, state, flows)
2. **MULTI_PROVIDER_GUIDE.md** - Provider setup, database, advanced usage
3. **examples.py** - 10 runnable examples with patterns
4. **html_generation_agent.py** - Source code with inline comments
5. **test_html_generation.py** - Mock test runner
6. **README.md** - This file (quick start & overview)

---

## 🤝 Contributing

To extend the system:

1. **Add New Agent**: Create node function, add to graph
2. **Modify Validation**: Edit validation rules in validator node
3. **New Database**: Implement in `DatabaseConfig` class
4. **Custom Routing**: Update conditional edges

---

## 🐛 Troubleshooting

### "No LLM API key configured"
**Fix**: Set one of `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`

### "Generation fails after retries"
**Fix**: Check validation errors in console, modify prompts

### "Can't connect to Qdrant"
**Fix**: Start Docker container or set `QDRANT_URL` correctly

### "Import errors"
**Fix**: Install all dependencies:
```bash
pip install langchain langgraph langchain-openai python-dotenv
```

---

## 📞 Quick Reference

### Common Commands
```bash
# Test without API key
python test_html_generation.py

# Generate with auto-detected provider
python html_generation_agent.py

# Run advanced examples
python examples.py

# Check provider status
python -c "from html_generation_agent import LLMConfig; \
           print(LLMConfig.get_default_provider())"
```

### Environment Setup
```bash
# Install
pip install langchain langgraph langchain-openai python-dotenv

# Configure
cp .env.example .env
nano .env  # Add your API key

# Run
python html_generation_agent.py
```

### Python API
```python
from html_generation_agent import run_html_generation_workflow

# Simple usage
run_html_generation_workflow("Your prompt here")

# Advanced usage
run_html_generation_workflow(
    "Your prompt here",
    llm_provider="openrouter",  # Specify provider
    use_database=True            # Store metadata
)
```

---

## 📄 License

This project is provided as-is for educational and commercial use.

---

## 🎉 Summary

This system demonstrates:
- ✅ **LangGraph orchestration** - Multi-agent coordination
- ✅ **Human-in-the-loop AI** - Interrupt/resume patterns
- ✅ **LLM provider flexibility** - Easy provider switching
- ✅ **Production-ready output** - Self-contained HTML
- ✅ **Error recovery** - Automatic self-correction
- ✅ **Database integration** - Metadata tracking

Perfect for: Rapid prototyping, batch generation, education, automation.

**Start generating HTML now!** 🚀

```bash
# No API key needed
python test_html_generation.py

# With API key
python html_generation_agent.py
```

---

**Questions?** Check the detailed guides or inline code comments.

**Ready to deploy?** Generated `output.html` is production-ready!
