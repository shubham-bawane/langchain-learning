# HTML Generation System - Web UI Guide

## Overview

The Web UI provides an intuitive split-screen interface for generating HTML websites through natural language conversation. The system combines a modern chat interface with a live preview sandbox in a responsive design.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         ui.py (Flask Backend)                   │
│  - REST API endpoints for chat, preview, download              │
│  - Session management                                           │
│  - Integration with html_generation_agent.py                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      templates/index.html                        │
│  - Main HTML structure with split-screen layout                │
│  - Dynamic containers for chat and preview                     │
│  - Control buttons and progress indicators                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    static/app.js (Frontend Logic)               │
│  - Chat interaction handling                                    │
│  - API communication                                            │
│  - Preview updates and control                                 │
│  - File operations (download, open in tab)                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   static/style.css (Styling)                    │
│  - Dark theme with accent colors                               │
│  - Responsive design (desktop to mobile)                       │
│  - Smooth animations and transitions                           │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### 1. **Chat Interface (Left Panel - 35% width)**
- Real-time conversation with AI agent
- Message history with timestamps
- User and bot message differentiation
- Smooth message animations
- Auto-scroll to latest message
- Multi-line input support (Shift+Enter for newline, Enter to send)

### 2. **Live Preview (Right Panel - 65% width)**
- Real-time HTML rendering in iframe sandbox
- Responsive preview scaling
- Safe HTML execution environment
- Framework-specific CDN detection

### 3. **Progress Tracking**
- Visual progress indicators for 5 stages:
  1. Requirements Clarified
  2. UX Design Blueprint
  3. Design System Defined
  4. HTML Code Generated
  5. Validation Complete
- Status color changes (pending → in-progress → complete)
- Step completion checkmarks

### 4. **Preview Controls**
- **Open in New Tab**: Launch preview in full browser window
- **Download**: Save generated HTML file to computer
- **Refresh**: Reload preview without regeneration
- Dynamic button visibility (shown only after HTML generation)

### 5. **Error Display**
- Validation errors displayed in chat flow
- Detailed error breakdown
- Retry information
- Solutions suggested by agent

### 6. **Info Panel**
- Framework used (Tailwind CSS or Bootstrap)
- Validation status
- File size in KB

## Setup and Installation

### Prerequisites
- Python 3.8+
- Flask and dependencies (see ui_requirements.txt)
- Existing html_generation_agent.py system

### Step 1: Install UI Dependencies
```bash
pip install -r ui_requirements.txt
```

### Step 2: Run the Development Server
```bash
python ui.py
```

The server will start at `http://localhost:5000`

### Step 3: Access the UI
Open your browser and navigate to:
```
http://localhost:5000
```

## API Endpoints

### Session Management

#### `POST /api/session/create`
Create a new chat session.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### Chat Operations

#### `POST /api/chat/message`
Send a message and get agent response.

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Create a portfolio website"
}
```

**Response:**
```json
{
  "success": true,
  "response": "✓ Requirements clarified...",
  "state": {
    "progress": {
      "requirements_clarified": true,
      "ux_designed": false,
      "design_complete": false,
      "html_generated": false,
      "validated": false,
      "retry_count": 0,
      "framework": "Tailwind"
    },
    "html_content": "<html>...</html>",
    "validation_errors": []
  }
}
```

#### `GET /api/session/<session_id>/messages`
Retrieve all messages in a session.

**Response:**
```json
{
  "messages": [
    {
      "role": "bot",
      "content": "Hi! What website would you like to create?",
      "timestamp": "2024-11-05T10:30:00"
    },
    {
      "role": "user",
      "content": "A portfolio for a developer",
      "timestamp": "2024-11-05T10:30:15"
    }
  ]
}
```

---

### Preview and Download

#### `GET /api/preview/html?session_id=<session_id>`
Get current HTML content for preview.

**Response:**
```json
{
  "html": "<html>...</html>",
  "framework": "Tailwind"
}
```

#### `GET /api/download/html?session_id=<session_id>`
Download HTML file directly.

**Response:** Binary HTML file with filename `website_<session_id>.html`

---

### Health Check

#### `GET /api/health`
Check server status.

**Response:**
```json
{
  "status": "healthy",
  "active_sessions": 5,
  "timestamp": "2024-11-05T10:30:00"
}
```

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari 12+, Chrome Android)

## Customization

### Change Theme Colors
Edit `static/style.css` and modify the CSS variables in `:root`:

```css
:root {
    --primary-color: #0ea5e9;      /* Primary accent */
    --secondary-color: #06b6d4;    /* Secondary accent */
    --success-color: #10b981;      /* Success indicator */
    --error-color: #ef4444;        /* Error indicator */
    --bg-dark: #0f172a;           /* Main background */
    --text-primary: #f1f5f9;       /* Primary text */
}
```

### Adjust Panel Width
Edit the left panel flex basis in `static/style.css`:

```css
.left-panel {
    flex: 0 0 35%;  /* Change 35% to desired width */
}
```

### Modify API Base URL
Edit `static/app.js` and change the `apiBase` property:

```javascript
this.apiBase = 'http://localhost:5000/api';  // Your API URL
```

## Deployment

### Production Deployment with Gunicorn

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 ui:app
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ui_requirements.txt ./
RUN pip install -r requirements.txt -r ui_requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "ui:app"]
```

### Environment Variables

```bash
# Flask configuration
FLASK_ENV=production
FLASK_APP=ui.py

# Allowed Origins (update CORS_ALLOW_ORIGINS if needed)
CORS_ALLOW_ORIGINS=https://yourdomain.com
```

## Troubleshooting

### Issue: "Cannot connect to API"
- Ensure `ui.py` is running: `python ui.py`
- Check if port 5000 is in use: `lsof -i :5000`
- Verify firewall settings allow local connections

### Issue: Preview not updating
- Click the "Refresh" button in preview controls
- Check browser console (F12) for JavaScript errors
- Verify iframe sandbox permissions in Flask security settings

### Issue: Download not working
- Check browser download settings
- Ensure sufficient disk space
- Try a different browser

### Issue: Chat messages not sending
- Check network tab (F12 → Network)
- Verify session ID is valid
- Check Flask server logs for errors

### Issue: Slow response times
- Check LLM provider rate limits
- Monitor Python process CPU/memory
- Consider implementing queue system for multiple sessions

## Performance Optimization

### Frontend Optimization
- Messages are virtualized (only visible messages rendered)
- CSS animations use GPU acceleration
- JavaScript bundled and minified in production

### Backend Optimization
- Session data stored in memory (use Redis for scaling)
- Async processing for long-running workflows (implement later)
- Connection pooling for database operations

### Recommended Production Setup
```
nginx (reverse proxy)
    ↓
gunicorn (4-8 workers)
    ↓
ui.py + html_generation_agent.py
    ↓
Redis (session cache)
    ↓
Optional: Qdrant (vector DB)
```

## Future Enhancements

- [ ] Real-time streaming responses with Server-Sent Events (SSE)
- [ ] WebSocket support for bidirectional communication
- [ ] Session persistence (database storage)
- [ ] User authentication and accounts
- [ ] Website template gallery
- [ ] Bulk generation API
- [ ] Webhooks for external integrations
- [ ] Advanced analytics dashboard
- [ ] Team collaboration features
- [ ] A/B testing variants
- [ ] Mobile app (React Native)
- [ ] Export to Figma/Adobe XD

## Security Considerations

### Current Protections
- ✓ CORS enabled with Flask-CORS
- ✓ Iframe sandbox prevents script access
- ✓ Input validation on backend
- ✓ Safe HTML rendering (no eval/exec)

### Recommended for Production
- [ ] Add CSRF protection (Flask-WTF)
- [ ] Implement rate limiting
- [ ] Add authentication (JWT or OAuth)
- [ ] Use HTTPS/TLS in production
- [ ] Sanitize user input with DOMPurify
- [ ] Content Security Policy (CSP) headers
- [ ] SQL injection prevention (if DB added)
- [ ] Regular security audits

## Support

For issues, feature requests, or questions:
1. Check this documentation
2. Review example usage in `examples.py`
3. Check browser console for errors (F12)
4. Review Flask server logs
5. See main project documentation in `START_HERE.md`
