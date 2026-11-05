# FastAPI HTML Generation System - Setup & Testing

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key in .env
OPENROUTER_API_KEY=your_key_here

# 3. Start server
uvicorn app:app --host 0.0.0.0 --port 5000 --reload

# 4. Open browser
http://localhost:5000
```

## Testing

```bash
# Run comprehensive test
python test_system.py

# Run unit tests  
pytest test_app.py -v

# Expected: ✅ All tests pass
```

## What It Does

1. **Chat Interface** - Describe your website idea
2. **AI Generates** - Multi-agent workflow creates HTML
3. **Live Preview** - See results in real-time
4. **Download** - Save as `.html` file

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | FastAPI backend (7 endpoints) |
| `html_generation_agent.py` | Multi-agent workflow |
| `test_system.py` | End-to-end system test |
| `test_app.py` | 34 unit tests |
| `templates/index.html` | Web UI |
| `static/app.js` | Frontend logic |
| `static/style.css` | Styling |

## API Endpoints

- `GET /api/health` - Server status
- `POST /api/session/create` - New session
- `POST /api/chat/message` - Send message
- `GET /api/preview/html` - Get preview
- `POST /api/download/html` - Download file
- `GET /api/session/{id}/messages` - Chat history
- `GET /api/session/{id}/state` - Current state

## Status

✅ **System is fully functional**

- Backend: FastAPI with async support
- Frontend: Clean split-screen UI
- Tests: 34 passing unit tests + end-to-end test
- Performance: ~40 seconds for website generation

## Next Steps

1. Add your API key to `.env`
2. Run `test_system.py` to verify
3. Open UI in browser
4. Generate websites!

## Support

- Server logs show real-time progress
- `test_system.py` validates each step
- `pytest test_app.py -v` for detailed tests
