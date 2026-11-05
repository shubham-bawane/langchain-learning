# UI Quick Start Guide

## 30-Second Setup

### 1. Install UI Dependencies
```bash
pip install flask flask-cors
```

### 2. Run the Server
```bash
python ui.py
```

### 3. Open in Browser
Visit: `http://localhost:5000`

That's it! 🎉

---

## How It Works

### Left Side - Chat
- Type your website description (e.g., "Create a portfolio for a developer")
- Press Enter to send
- AI asks clarifying questions
- Watch progress update in real-time

### Right Side - Preview
- Automatically displays generated website
- **Open in Tab** - View full screen in new tab
- **Download** - Save as HTML file to your computer
- **Refresh** - Reload preview

### Progress Indicators
Watch these stages complete:
1. ✓ Requirements Clarified
2. ✓ UX Design Blueprint
3. ✓ Design System Defined
4. ✓ HTML Code Generated
5. ✓ Validation Complete

---

## Example Workflow

```
You:  "Create a professional landing page for a SaaS startup"
↓
Bot:  "Great! What's the company name and main product?"
↓
You:  "CloudSync - A file synchronization tool"
↓
Bot:  "Perfect! Generating your website...
       [✓ Requirements Clarified]
       [✓ UX Blueprint Created]
       [→ Generating HTML...]"
↓
(Right panel shows live preview)
↓
Bot:  "✓ Website generated successfully!
       📦 Framework: Tailwind CSS"
↓
You: Click [↗ Open in Tab] or [⬇ Download]
```

---

## File Structure

```
/workspaces/langchain-learning/
├── ui.py                          # Flask backend
├── templates/
│   └── index.html                # Main UI HTML
├── static/
│   ├── app.js                    # Frontend logic
│   └── style.css                 # Styling
└── UI_GUIDE.md                   # Full documentation
```

---

## Common Tasks

### Change Framework (Tailwind → Bootstrap)
Edit the chat to mention your preference:
- "Use Bootstrap instead of Tailwind"
- "Generate with Bootstrap 5"

### Open Preview in Full Window
- Click [↗ Open in Tab] button
- Or right-click in preview and "Open Frame in New Tab"

### Download Generated Website
- Click [⬇ Download] button
- HTML file saves to Downloads folder
- Open in any browser

### Clear Chat and Start Over
- Click [🗑️ Trash] button
- Confirms before clearing
- Creates new session

### View Multiple Versions
- Open multiple browser tabs
- Each tab has independent session
- Compare different designs side-by-side

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Send message |
| Shift+Enter | New line in message |
| Ctrl+L | Focus message input |

---

## Features at a Glance

| Feature | Location | Usage |
|---------|----------|-------|
| Chat | Left side | Type prompts |
| Preview | Right side | See live website |
| Progress | Left side below chat | Track generation |
| Controls | Above preview | Open/Download |
| Info | Below preview | Framework & size |
| Errors | Left side | Validation issues |

---

## Tips & Tricks

✅ **Be Descriptive**
- "Portfolio site with blue theme" works better than "website"
- Include specific colors, layouts, content types

✅ **Ask Follow-ups**
- "Can you make it darker?"
- "Add more white space"
- "Use a different color scheme"

✅ **Leverage Auto-Correction**
- System automatically retries up to 3 times if errors found
- You'll see "Retry 1/3" in status
- Let it complete before asking for changes

✅ **Explore Variations**
- Open multiple tabs to compare different prompts
- Same session = continuous iteration
- New tab = fresh start

✅ **Performance**
- Modern browsers render HTML instantly
- Chrome/Firefox/Safari recommended
- Mobile browsers supported

---

## Troubleshooting

**Q: "Cannot connect to API"**
A: Make sure `python ui.py` is running and port 5000 is open

**Q: "Preview not showing"**
A: Wait for HTML to generate (watch progress), then click Refresh

**Q: "Download not working"**
A: Try a different browser or check download settings

**Q: "Response very slow"**
A: Check API key configuration in `.env` file

---

## Customization

### Change Colors
Edit `static/style.css`:
```css
--primary-color: #0ea5e9;    /* Blue → your color */
--bg-dark: #0f172a;          /* Dark → your shade */
```

### Change Panel Width
Edit `static/style.css`:
```css
.left-panel {
    flex: 0 0 35%;  /* 35% width → change to 40%, 45%, etc */
}
```

### Modify Preview Size
Edit `templates/index.html`:
```html
<!-- Adjust iframe height or container size -->
```

---

## Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 ui:app
```

### Using Docker
```bash
# Build image
docker build -t website-generator .

# Run container
docker run -p 5000:5000 website-generator
```

### Using Heroku
```bash
# Deploy
git push heroku main
```

---

## Under the Hood

The UI connects to your existing HTML generation system:

1. **Frontend** (app.js) sends chat message to Flask API
2. **Backend** (ui.py) creates/updates session state
3. **Agent System** (html_generation_agent.py) processes the request
4. **Response** flows back through API
5. **Preview** updates automatically
6. **Download** saves the HTML file

All 6 agents (Manager, UI/UX, Designer, Code Gen, Validator, Writer) run server-side while you watch progress.

---

## Next Steps

1. ✅ Run `python ui.py`
2. ✅ Open browser to `http://localhost:5000`
3. ✅ Type your first website description
4. ✅ Watch it generate in real-time
5. ✅ Download your website!

---

Need more help? See `UI_GUIDE.md` for full documentation.
