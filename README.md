# 🏢 Website Generator AI - IT Service Company Edition

> A complete AI-powered web development system that simulates a real IT service company, complete with multi-agent workflows, LangSmith monitoring, and a beautiful modern UI.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Features](#features)
5. [Getting Started](#getting-started)
6. [System Structure](#system-structure)
7. [API Reference](#api-reference)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Usage](#advanced-usage)

---

## 🎯 Overview

This project is a **complete AI-driven web development platform** that mimics a real IT service company. When you submit a website requirement, multiple AI agents with different specializations collaborate to deliver a production-ready website.

### The Workflow
```
CLIENT (You)
    ↓
ACCOUNT MANAGER → Clarifies requirements
    ↓
UX/UI DESIGNER → Creates design blueprint
    ↓
DESIGN TEAM → Defines visual system
    ↓
WEB DEVELOPER → Generates HTML/CSS
    ↓
QA TESTER → Validates quality
    ↓
PROJECT MANAGER → Delivers result
    ↓
WEBSITE READY ✅
```

### Key Innovation
Each step is **traced in LangSmith** for full visibility into:
- Token usage and costs
- Execution times
- Quality metrics
- Error debugging
- AI decision-making

---

## 🚀 Quick Start (2 Minutes)

### 1. Setup
```bash
# Clone and install
pip install -r requirements.txt

# Configure .env
echo "OPENROUTER_API_KEY=your_key_here" >> .env
echo "LANGSMITH_API_KEY=your_key_here" >> .env  # Optional but recommended

# Start server
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 2. Access
```
Open: http://localhost:8000
```

### 3. Create Website
```
1. Type: "Create a beautiful portfolio website for a designer"
2. Press Enter
3. Watch the AI team work in real-time
4. Download the result when done!
```

**That's it!** ⚡

---

## 🏗️ Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | FastAPI | REST API server |
| **Orchestration** | LangGraph | Multi-agent workflow |
| **AI Framework** | LangChain | LLM integrations |
| **Monitoring** | LangSmith | Tracing & evaluation |
| **Frontend** | React-like HTML/JS | Modern web UI |
| **Styling** | Tailwind CSS | Responsive design |
| **LLM Providers** | OpenRouter/OpenAI/Claude | AI models |

### System Flow

```
┌─────────────┐
│   Web UI    │
│  (Browser)  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│     FastAPI Server          │
├─────────────────────────────┤
│  Session Management         │
│  API Routing                │
│  Response Formatting        │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Service Company Workflow  │
├─────────────────────────────┤
│  Account Manager            │
│  UX/UI Designer             │
│  Design Team                │
│  Web Developer              │
│  QA Tester                  │
│  Project Manager            │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   LLM Providers             │
├─────────────────────────────┤
│  OpenRouter (default)       │
│  OpenAI GPT-4               │
│  Anthropic Claude           │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   LangSmith Dashboard       │
├─────────────────────────────┤
│  Real-time tracing          │
│  Cost tracking              │
│  Performance metrics        │
│  Error debugging            │
└─────────────────────────────┘
```

---

## ✨ Features

### 🎭 Multi-Agent System
- **7 Specialized Agents** - Each with specific role and expertise
- **State Management** - Complete workflow state tracking
- **Interrupt Handling** - Human-in-the-loop clarification
- **Error Recovery** - Automatic retry mechanism (up to 2 times)

### 💻 Modern UI
- **Glassmorphism Design** - Beautiful frosted glass effects
- **Animated Gradients** - Smooth color transitions
- **Real-time Updates** - Live preview as content generates
- **Progress Indicators** - Visual feedback for each step
- **Responsive Layout** - Works on desktop, tablet, mobile

### 🔍 LangSmith Integration
- **Complete Tracing** - Every AI call is logged
- **Cost Breakdown** - Token usage by provider
- **Performance Metrics** - Execution times and latency
- **Quality Evaluation** - Success rates and error patterns
- **Debug Console** - Inspect agent decisions

### 📊 Quality Assurance
- **Automated Testing** - QA agent validates HTML
- **Accessibility Checking** - WCAG compliance verification
- **Performance Review** - Optimization suggestions
- **Browser Compatibility** - Cross-browser testing
- **Security Audit** - Vulnerability scanning

### 🔄 Continuous Improvement
- **Multi-turn Workflow** - Iterate through multiple generations
- **Improvement Requests** - Ask for specific changes
- **State Persistence** - Session data preserved across requests
- **Learning Capability** - Track improvements over time

---

## 📖 Getting Started

### Installation

```bash
# 1. Navigate to project
cd /workspaces/langchain-learning

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file with API keys
cat > .env << EOF
# LLM Provider (choose at least one)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx

# Optional: LangSmith Monitoring
LANGSMITH_API_KEY=ls_xxxxxxxxxxxx

# Optional: Qdrant Vector DB
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=xxxxxxxxxxxx
EOF
```

### Starting the Server

```bash
# Development mode (with auto-reload)
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Production mode (4 workers)
python -m uvicorn app:app --workers 4 --host 0.0.0.0 --port 8000

# Custom port
python -m uvicorn app:app --port 3000
```

### Using the System

#### Via Web UI (Easiest)
1. Open browser: `http://localhost:8000`
2. Type your website description
3. Press Enter and watch the magic happen
4. Download when complete

#### Via API (Programmatic)

```python
import requests

BASE_URL = "http://localhost:8000/api"

# 1. Create session
session = requests.post(f"{BASE_URL}/session/create").json()
session_id = session['session_id']

# 2. Send message
response = requests.post(
    f"{BASE_URL}/chat/message",
    json={
        "session_id": session_id,
        "message": "Create a modern portfolio website"
    }
).json()

# 3. Get generated HTML
preview = requests.get(
    f"{BASE_URL}/preview/html",
    params={"session_id": session_id}
).json()

print(preview['html_content'])
```

#### Via cURL

```bash
# Create session
curl -X POST http://localhost:8000/api/session/create

# Send message
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "message": "Create a flower shop website"
  }'

# Download HTML
curl http://localhost:8000/api/preview/html?session_id=YOUR_SESSION_ID
```

---

## 📁 System Structure

```
langchain-learning/
├── 📘 README.md                          ← THIS FILE (Main docs)
├── 📘 LANGGRAPH_README.md               ← LangGraph workflow docs
├── 📘 .env                              ← Configuration (your secrets)
│
├── 🔧 Backend
│   ├── app.py                           ← FastAPI server (7 endpoints)
│   ├── service_company_workflow.py      ← Multi-agent orchestration
│   ├── service_company_api_bridge.py    ← API integration layer
│   └── html_generation_agent.py         ← Legacy single-agent system
│
├── 🎨 Frontend
│   ├── templates/
│   │   ├── index_modern.html            ← Modern UI template (ACTIVE)
│   │   ├── index_advanced.html          ← Alternative template
│   │   └── index.html                   ← Legacy template
│   └── static/
│       ├── app_modern.js                ← Modern UI logic (ACTIVE)
│       ├── style_modern.css             ← Modern styling (ACTIVE)
│       ├── app.js                       ← Legacy JavaScript
│       └── style.css                    ← Legacy CSS
│
├── 🧪 Testing
│   ├── test_app.py                      ← 34 unit tests
│   ├── test_system.py                   ← End-to-end test
│   └── pytest.ini
│
├── 📦 Configuration
│   ├── requirements.txt                 ← Python dependencies
│   ├── pyproject.toml
│   └── .gitignore
│
├── 📁 Assets
│   ├── chapters/                        ← Learning materials
│   ├── examples.py                      ← Example usage
│   ├── output.html                      ← Sample output
│   └── QUICK_REFERENCE.txt
│
└── 🗂️ Git
    └── .git/
```

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `app.py` | FastAPI backend | 500+ |
| `service_company_workflow.py` | Multi-agent workflow | 600+ |
| `service_company_api_bridge.py` | API integration | 200+ |
| `templates/index_modern.html` | Web UI | 200+ |
| `static/app_modern.js` | UI logic | 400+ |
| `static/style_modern.css` | Styling | 800+ |

---

## 🔌 API Reference

### Health Check
```http
GET /api/health

Response:
{
  "status": "healthy",
  "timestamp": "2024-11-05T09:00:00",
  "sessions_active": 5
}
```

### Create Session
```http
POST /api/session/create

Response:
{
  "session_id": "abc123def456"
}
```

### Send Message (Main Endpoint)
```http
POST /api/chat/message
Content-Type: application/json

Body:
{
  "session_id": "abc123def456",
  "message": "Create a portfolio website"
}

Response:
{
  "success": true,
  "response": "🏢 Project status: development...",
  "state": {
    "html_content": "<html>...</html>",
    "validation_errors": [],
    "project_status": "development",
    "stakeholder_responses": {...},
    "design_system": {...}
  }
}
```

### Get Preview
```http
GET /api/preview/html?session_id=abc123def456

Response:
{
  "html_content": "<html>...</html>"
}
```

### Download HTML
```http
POST /api/download/html?session_id=abc123def456

Response:
Binary HTML file download
```

### Get Messages
```http
GET /api/session/{session_id}/messages

Response:
{
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ]
}
```

### Get State
```http
GET /api/session/{session_id}/state

Response:
{
  "state": {
    "project_status": "development",
    "design_system": {...},
    "validation_errors": [...]
  }
}
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# === LLM Providers (Choose at least one) ===

# OpenRouter (Recommended - lowest cost)
OPENROUTER_API_KEY=sk-or-v1-xxxxx

# OpenAI (High quality)
OPENAI_API_KEY=sk-xxxxx

# Anthropic (Balanced)
ANTHROPIC_API_KEY=sk-ant-xxxxx

# === Monitoring (Optional but recommended) ===

# LangSmith - Full workflow tracing
LANGSMITH_API_KEY=ls_xxxxx
LANGSMITH_PROJECT=IT-Service-WebDev

# === Vector Database (Optional) ===

# Qdrant for RAG capabilities
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=xxxxx
```

### Getting API Keys

#### OpenRouter (Recommended)
1. Go to https://openrouter.ai
2. Sign up for free account
3. Copy API key from settings
4. Cost: ~$0.001 per 1K tokens (cheapest)

#### OpenAI
1. Go to https://platform.openai.com
2. Create account or sign in
3. Copy API key from API keys section
4. Cost: ~$0.03-0.06 per 1K tokens (most expensive)

#### Anthropic
1. Go to https://console.anthropic.com
2. Sign up for beta access
3. Copy API key from settings
4. Cost: ~$0.008-0.024 per 1K tokens (balanced)

#### LangSmith
1. Go to https://smith.langchain.com
2. Sign up with GitHub
3. Create new project: "IT-Service-WebDev"
4. Copy API key from settings
5. Free tier available

---

## 🆘 Troubleshooting

### Common Issues

#### ❌ "Port 8000 already in use"
```bash
# Find and kill process using port 8000
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Or use different port
python -m uvicorn app:app --port 8001
```

#### ❌ "No API key configured"
```bash
# Verify .env file exists and has API key
cat .env | grep OPENROUTER_API_KEY

# If missing, add it
echo "OPENROUTER_API_KEY=your_key_here" >> .env
```

#### ❌ "No HTML in preview"
1. Check browser console (F12) for errors
2. Check server logs for API errors
3. Verify all dependencies installed: `pip install -r requirements.txt`
4. Try simpler prompt: "Create a hello world website"

#### ❌ "Workflow takes too long"
- Normal: 30-60 seconds for complete workflow
- LangSmith tracing adds ~5-10 seconds
- First generation slower due to LLM initialization
- Subsequent generations are faster

#### ❌ "High costs"
- Use OpenRouter (10x cheaper than OpenAI)
- Reduce retry attempts in QA testing
- Use shorter prompts
- Monitor LangSmith dashboard for inefficiencies

### Debug Mode

```bash
# Run with full debug output
PYTHONUNBUFFERED=1 python -m uvicorn app:app --reload --log-level debug

# Check health endpoint
curl http://localhost:8000/api/health

# View server logs
tail -f /tmp/server.log
```

---

## 🎓 Advanced Usage

### Multi-turn Conversation

Instead of one detailed prompt, have a conversation:

```
User: "Create a portfolio website"
AI: ✅ Modern portfolio landing page created

User: "Add a blog section"
AI: ✅ Added blog section with recent posts

User: "Change colors to blue theme"
AI: ✅ Updated color scheme to blue

User: "Download it"
[Gets polished website.html]
```

### Improvement Requests

Supported improvement keywords:
- "improve" → Routes to design team
- "change" → Routes to design team  
- "add" → Routes to developer
- "remove" → Routes to developer
- "fix" → Routes to QA tester

### Monitoring with LangSmith

1. Set `LANGSMITH_API_KEY` in .env
2. Run server: `python -m uvicorn app:app --reload`
3. Make a request in UI
4. Visit: https://smith.langchain.com/projects/IT-Service-WebDev
5. View complete trace tree showing:
   - Which agent ran
   - Input/output for each agent
   - Token usage and costs
   - Execution times
   - Any errors

### Custom LLM Model

Modify `service_company_workflow.py`:

```python
# Use specific model
LLM = ChatOpenAI(
    model="gpt-4-turbo",           # Change here
    api_key=os.getenv("OPENAI_API_KEY")
)
```

### Enabling RAG with Qdrant

1. Start Qdrant: `docker run -d -p 6333:6333 qdrant/qdrant`
2. Set environment variables:
   ```bash
   QDRANT_URL=http://localhost:6333
   QDRANT_API_KEY=your_key
   ```
3. System will use vector search for design system lookup

---

## 📊 Performance Metrics

### Typical Execution Times

| Step | Time | Agent |
|------|------|-------|
| Requirements | 5-10s | Account Manager |
| Design | 10-15s | UX/UI Designer |
| Style System | 5-8s | Design Team |
| Code Gen | 15-20s | Web Developer |
| QA Test | 5-10s | QA Tester |
| Delivery | 2-3s | Project Manager |
| **TOTAL** | **40-60s** | All agents |

### Cost Breakdown (per request)

| Provider | Cost | Quality |
|----------|------|---------|
| OpenRouter | $0.01-0.05 | Good |
| OpenAI | $0.15-0.30 | Excellent |
| Anthropic | $0.05-0.15 | Good |

LangSmith shows exact costs for each run.

---

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest test_app.py -v

# Specific test
pytest test_app.py::TestSessionManagement -v

# With coverage
pytest test_app.py --cov=app

# End-to-end test
python test_system.py
```

### Example Test

```python
def test_chat_message():
    """Test sending a chat message"""
    client = TestClient(app)
    
    # Create session
    response = client.post("/api/session/create")
    session_id = response.json()["session_id"]
    
    # Send message
    response = client.post(
        "/api/chat/message",
        json={
            "session_id": session_id,
            "message": "Create a hello world website"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "html_content" in data.get("state", {})
```

---

## 📚 Additional Documentation

- **LANGGRAPH_README.md** - Detailed LangGraph workflow documentation
- **QUICK_REFERENCE.txt** - Quick command reference

---

## 🤝 Contributing

To contribute improvements:

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes
4. Run tests: `pytest test_app.py -v`
5. Commit: `git commit -am "Add my feature"`
6. Push: `git push origin feature/my-feature`
7. Create Pull Request

---

## 📄 License

MIT License - Free for personal and commercial use

---

## 🎯 Roadmap

### Planned Features
- [ ] Database persistence (PostgreSQL)
- [ ] User accounts and authentication
- [ ] Team collaboration features
- [ ] Advanced RAG with Qdrant
- [ ] Custom model fine-tuning
- [ ] Mobile app (React Native)
- [ ] Webhook integrations
- [ ] Template library
- [ ] A/B testing framework
- [ ] Analytics dashboard

---

## 📞 Support

### Resources
- 📖 Full LangGraph docs: https://langchain-ai.github.io/langgraph/
- 📖 LangSmith docs: https://docs.smith.langchain.com/
- 📖 LangChain docs: https://python.langchain.com/docs/
- 🎓 OpenRouter API: https://openrouter.ai/docs

### Getting Help
1. Check troubleshooting section above
2. Review test files for usage examples
3. Check server logs: `tail -f /tmp/server.log`
4. Open browser console (F12) for frontend errors
5. Check LangSmith dashboard for workflow issues

---

**Built with ❤️ using LangChain, LangGraph, and FastAPI**

Last Updated: November 5, 2024
Version: 2.0 (Service Company Edition)
