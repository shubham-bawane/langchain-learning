# FastAPI Quick Start Guide

## 30-Second Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your API key to .env
# Edit .env and add: OPENROUTER_API_KEY=your_key_here

# 3. Start server
uvicorn app:app --host 0.0.0.0 --port 5000 --reload

# 4. Open browser
# Navigate to http://localhost:5000
```

## Testing (10 Seconds)

```bash
# Run all 34 tests
pytest test_app.py -v

# Expected: 34 passed ✅
```

## Using the API

### 1. Create a Session
```bash
curl -X POST http://localhost:5000/api/session/create
# Returns: {"session_id": "abc123..."}
```

### 2. Send a Message
```bash
curl -X POST http://localhost:5000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc123...",
    "message": "Create a flower shop website"
  }'
```

### 3. Get Preview
```bash
curl http://localhost:5000/api/preview/html?session_id=abc123...
```

### 4. Download HTML
```bash
curl -X POST http://localhost:5000/api/download/html?session_id=abc123...
```

## Using the UI

1. Open `http://localhost:5000`
2. Type your website idea (e.g., "flower shop")
3. Watch the AI generate HTML in real-time
4. Preview on the right side
5. Download the final file

## Common Commands

### Server Control
```bash
# Start with auto-reload
uvicorn app:app --reload

# Start on custom port
uvicorn app:app --port 8000

# Start with workers (production)
uvicorn app:app --workers 4
```

### Testing
```bash
# Run tests
pytest test_app.py

# Verbose output
pytest test_app.py -v

# Specific test
pytest test_app.py::TestSessionManagement -v

# With coverage
pytest test_app.py --cov=app
```

### Debugging
```bash
# Run with debug output
PYTHONUNBUFFERED=1 uvicorn app:app --reload

# Check server health
curl http://localhost:5000/api/health
```

## API Documentation

**Swagger UI**: http://localhost:5000/docs
**ReDoc**: http://localhost:5000/redoc

Browse interactive API documentation automatically generated from FastAPI.

## Endpoints Summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | / | Serve UI |
| GET | /api/health | Health check |
| POST | /api/session/create | Create session |
| POST | /api/chat/message | Send message |
| GET | /api/preview/html | Get preview |
| POST | /api/download/html | Download HTML |
| GET | /api/session/{id}/messages | Get messages |
| GET | /api/session/{id}/state | Get state |

## Environment Variables

```bash
# Required
OPENROUTER_API_KEY=sk_...

# Optional
LANGSMITH_API_KEY=ls_...
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...
```

## Troubleshooting

**"Port 5000 already in use"**
```bash
# Kill existing process
lsof -i :5000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

**"Module not found"**
```bash
# Install all dependencies
pip install -r requirements.txt
```

**"API key not set"**
```bash
# Edit .env and add your key
OPENROUTER_API_KEY=your_actual_key
```

## What's Happening

When you send a prompt:

1. **Manager Agent** - Clarifies requirements if vague
2. **UI/UX Agent** - Designs page layout
3. **Designer Agent** - Creates design system
4. **Code Generator** - Writes HTML + CSS
5. **Validator** - Checks for errors
6. **File Writer** - Saves output

All in 30-60 seconds! ⚡

## Next Steps

- [ ] Generate your first website
- [ ] Try different prompts
- [ ] Download and open in browser
- [ ] Customize the frontend UI
- [ ] Deploy to production
- [ ] Add database persistence

## Support

- Check `FASTAPI_README.md` for full documentation
- Review `test_app.py` for usage examples
- Check server logs for errors

---

**Let's build websites with AI!** 🚀
