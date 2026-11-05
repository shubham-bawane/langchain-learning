# UI Visual Guide & Screenshot Reference

## Full UI Layout

```
╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║  🖥️  HTML Generation AI System                                    ● Ready    ║
║                                                                                ║
╠═══════════════════════════════════════════╦═════════════════════════════════════╣
║                                           ║                                     ║
║          CHAT INTERFACE (35%)             ║    LIVE PREVIEW (65%)              ║
║          Left Side                        ║    Right Side                       ║
║                                           ║                                     ║
║  ┌──────────────────────────────────┐   ║  ┌───────────────────────────────┐  ║
║  │ Conversation Thread              │   ║  │ [↗ Open] [⬇ Download] [🔄]   │  ║
║  │                                  │   ║  ├───────────────────────────────┤  ║
║  │ 🤖 Bot: Hi! What website would   │   ║  │                               │  ║
║  │ you like to create?              │   ║  │  ╔─────────────────────────┐ │  ║
║  │                                  │   ║  │  │  Your Portfolio Website │ │  ║
║  │ 👤 You: A portfolio for a        │   ║  │  │                         │ │  ║
║  │ developer                         │   ║  │  │  Hi, I'm John Doe       │ │  ║
║  │                                  │   ║  │  │  Full Stack Developer   │ │  ║
║  │ 🤖 Bot: Great! What's your       │   ║  │  │  ▰▰▰▰▰ (5 yrs exp)     │ │  ║
║  │ color preference?                │   ║  │  │                         │ │  ║
║  │                                  │   ║  │  │  📧 Contact Me          │ │  ║
║  │ ✓ Requirements Clarified         │   ║  │  │  🔗 View Projects       │ │  ║
║  │ ✓ UX Blueprint Created           │   ║  │  │                         │ │  ║
║  │ ✓ Design System Defined          │   ║  │  │ [Visit Portfolio] [Git] │ │  ║
║  │ ✓ HTML Generated                 │   ║  │  │ [LinkedIn] [Twitter]    │ │  ║
║  │ → Validating...                  │   ║  │  └─────────────────────────┘ │  ║
║  │                                  │   ║  │                               │  ║
║  │ ⚠ Validation Issue Found:        │   ║  │ (Responsive, Tailwind CSS)   │  ║
║  │ • Missing viewport meta tag      │   ║  │                               │  ║
║  │ • Retry 1/3                      │   ║  └───────────────────────────────┘  ║
║  │                                  │   ║  📦 Framework: Tailwind CSS          ║
║  ├──────────────────────────────────┤   ║  ✓ Status: Valid (100%)              ║
║  │ Your prompt:                     │   ║  📄 Size: 8.5 KB                     ║
║  │ [_____________________][💬][🗑️]  │   ║                                     ║
║  │ Shift+Enter for new line         │   ║                                     ║
║  └──────────────────────────────────┘   ║                                     ║
║                                           ║                                     ║
╚═══════════════════════════════════════════╩═════════════════════════════════════╝

⌨️  Keyboard Controls:
   Enter → Send message
   Shift+Enter → New line
   Ctrl+L → Focus input
```

## Component Breakdown

### 1. Header Bar
```
┌─────────────────────────────────────────────────┐
│ 💻 HTML Generation AI System      ● Ready      │
├─────────────────────────────────────────────────┤
│ • Logo with icon (left)                         │
│ • Status indicator (animated pulse - green)     │
│ • Status text (Ready/Processing/Complete)       │
└─────────────────────────────────────────────────┘
```

### 2. Chat Panel (Left)
```
┌───────────────────────────────────────┐
│ Chat History (scrollable)             │
├───────────────────────────────────────┤
│                                       │
│  🤖  [Bot Message]                    │
│  └─ "Hi! What website..."             │
│     [12:34 PM]                        │
│                                       │
│                    👤 [Your Message]  │
│                    └─ "A portfolio"   │
│                       [12:35 PM]      │
│                                       │
│  🤖  [Bot Message]                    │
│  └─ "Great! Colors?"                  │
│     [12:35 PM]                        │
│                                       │
├───────────────────────────────────────┤
│ Progress: ✓ ✓ ✓ → ○ ○                │
│          R  U  D  H  V                │
│ (Requirements, UX, Design,            │
│  HTML, Validation)                    │
├───────────────────────────────────────┤
│ Errors: ⚠ Missing meta tags           │
│         Retry 1/3                     │
├───────────────────────────────────────┤
│ Input: [_________] [📤] [🗑️]         │
│        Message    Send Clear          │
│ "Shift+Enter for new line"            │
└───────────────────────────────────────┘
```

### 3. Preview Panel (Right)
```
┌─────────────────────────────────────────┐
│ [↗ Open in Tab] [⬇ Download] [🔄] 🔄   │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐  │
│  │  Website Preview (Live HTML)    │  │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │  │
│  │                                 │  │
│  │  ╭─────────────────────────╮    │  │
│  │  │ Your Portfolio          │    │  │
│  │  │                         │    │  │
│  │  │ Hi, I'm Jane Doe        │    │  │
│  │  │ Product Designer        │    │  │
│  │  │                         │    │  │
│  │  │ [My Work] [Contact]     │    │  │
│  │  ╰─────────────────────────╯    │  │
│  │                                 │  │
│  │  Featured Projects              │  │
│  │  ├─ Project 1                   │  │
│  │  ├─ Project 2                   │  │
│  │  └─ Project 3                   │  │
│  │                                 │  │
│  └─────────────────────────────────┘  │
│                                         │
│ 📦 Tailwind CSS | ✓ Valid | 8.5 KB     │
└─────────────────────────────────────────┘
```

## User Interactions

### Flow 1: Initial Load
```
Browser opens http://localhost:5000
         ↓
Load index.html (7.7 KB)
         ↓
Load CSS (10.1 KB) - Dark theme renders
         ↓
Load JavaScript (11.7 KB) - ChatApp initializes
         ↓
POST /api/session/create
         ↓
Receive session_id (UUID)
         ↓
Display: "👋 Hi! What website would you like to create?"
         ↓
Ready for user input ✓
```

### Flow 2: Generate Website
```
User types: "A blog about AI"
         ↓
Press Enter
         ↓
Message appears in left panel (styled as user-message)
Show loading spinner
         ↓
POST /api/chat/message {session_id, message}
         ↓
Backend: run_html_generation_workflow()
Execute 6 agents (20-60 seconds)
         ↓
Receive: {response, state}
         ↓
Update progress indicators: ✓ ✓ ✓ ✓ →
         ↓
Bot message appears in chat
         ↓
Preview iframe populated with HTML
         ↓
Right side shows live website
         ↓
Control buttons enabled: [↗] [⬇]
         ↓
User can download or open in tab
```

### Flow 3: Refine Design
```
Looking at preview, user thinks: "Too dark"
         ↓
Types in chat: "Make the background lighter"
         ↓
Press Enter
         ↓
(Repeats generation with additional context)
         ↓
Preview updates with new design
         ↓
User satisfied? Download! [⬇]
```

## Responsive Breakpoints

### Desktop (1024px+) - Default
```
┌─────────┬──────────────────────┐
│         │                      │
│ 35%     │      65%             │
│ Chat    │      Preview         │
│         │                      │
│         │                      │
└─────────┴──────────────────────┘
```

### Tablet (768px - 1023px)
```
┌──────────────────────────────┐
│                              │
│  40% Chat                    │
│                              │
├──────────────────────────────┤
│                              │
│  60% Preview                 │
│                              │
└──────────────────────────────┘
```

### Mobile (<768px)
```
┌──────────────────────┐
│                      │
│  Chat Interface      │
│  (Full Width)        │
│                      │
├──────────────────────┤
│                      │
│  Preview             │
│  (Full Width)        │
│  (Scrollable)        │
│                      │
└──────────────────────┘
```

### Small Mobile (<480px)
```
┌──────────────┐
│ 🖥️ AI Gen    │ (Header only logo)
├──────────────┤
│ Chat         │ (Full screen, stacked)
├──────────────┤
│ Preview      │ (Full screen, stacked)
│ [↗] [⬇] [🔄]│ (Icons only, no labels)
└──────────────┘
```

## Color Scheme

### Dark Theme (Active)
```
Background:    #020617 (Very dark blue)
Surface:       #1e293b (Dark blue-gray)
Primary:       #0ea5e9 (Sky blue - accent)
Secondary:     #06b6d4 (Cyan - hover)
Success:       #10b981 (Green - checkmarks)
Warning:       #f59e0b (Amber - retry)
Error:         #ef4444 (Red - issues)
Text:          #f1f5f9 (Light text)
Text Secondary: #cbd5e1 (Dimmed text)
Border:        #475569 (Subtle border)
```

### Theme Customization Example
Change to light theme by modifying `static/style.css`:
```css
:root {
    --primary-color: #2563eb;      /* Blue */
    --bg-dark: #ffffff;            /* White */
    --bg-surface: #f8fafc;         /* Light gray */
    --text-primary: #1e293b;       /* Dark text */
    /* ... etc */
}
```

## Progress Indicator States

### Step Not Started
```
○ Requirements
```

### Step In Progress
```
→ UX Design
```

### Step Complete
```
✓ Design System
```

### All Complete
```
✓ ✓ ✓ ✓ ✓
R U D H V
```

## Message Styling

### Bot Message
```
┌────────────────────────────────┐
│ 🤖 Message content             │
│ Left-aligned (gray background) │
│ [12:34 PM]                     │
└────────────────────────────────┘
```

### User Message
```
                 ┌────────────────────────────┐
                 │ Your message content       │
                 │ Right-aligned (blue bg)    │
                 │ [12:35 PM]                 │
                 └────────────────────────────┘
```

## Control Buttons

### States

#### Enabled (After HTML Generated)
```
[↗ Open in New Tab] [⬇ Download] [🔄 Refresh]
 (Blue hover)       (Blue hover)  (Always on)
```

#### Disabled (Before HTML Generated)
```
[↗ Open in New Tab] [⬇ Download] [🔄 Refresh]
 (Grayed out)       (Grayed out)  (Enabled)
```

## Loading State

```
┌─────────────────────────────────┐
│                                 │
│          ⟳⟳⟳⟳                  │
│   Generating your website...    │
│                                 │
│      Please wait (10-60s)        │
│                                 │
└─────────────────────────────────┘
(Overlay with semi-transparent background)
```

## Error Display

```
┌─────────────────────────────────┐
│ ⚠ Issues Found                  │
├─────────────────────────────────┤
│ ⚠ Missing viewport meta tag     │
│ ⚠ CDN link not found            │
│ ⚠ No DOCTYPE declaration        │
│                                 │
│ Retry 1/3 - Agent is fixing...  │
└─────────────────────────────────┘
```

## Animation Effects

### Message Slide-In
```
Frame 1:  (invisible, 10px below)
Frame 2:  (opacity 0.5, sliding up)
Frame 3:  ✓ (fully visible, at rest)
Duration: 300ms
Easing:   ease
```

### Pulse Animation (Status Indicator)
```
Frame 1:  ● (opacity 1.0 - solid green)
Frame 2:  ● (opacity 0.5 - fading)
Frame 3:  ● (opacity 1.0 - solid again)
Duration: 2000ms (repeating)
```

### Button Hover
```
At rest:     [↗ Open in Tab] (normal)
On hover:    [↗ Open in Tab] (blue bg, +2px up)
On click:    [↗ Open in Tab] (reset position)
On disabled: [↗ Open in Tab] (grayed, no hover)
```

## Accessibility Features

✓ **ARIA Labels**: Buttons have descriptive titles
✓ **Keyboard Navigation**: Tab through elements
✓ **Semantic HTML**: Proper heading hierarchy
✓ **Color Contrast**: WCAG AA compliant
✓ **Focus Indicators**: Visible on interactive elements
✓ **Screen Reader Support**: Semantic structure
✓ **High DPI Support**: CSS scaling handles retina displays

## Print Stylesheet

Users can print the generated website by:
1. Click [↗ Open in Tab]
2. Press Ctrl+P
3. Save as PDF or print

The UI itself is not print-optimized (intentional), but generated websites print correctly.

---

**Total Design Token Count**: ~20 colors, 5 typography sizes, 8 spacing scales
**CSS Bytes**: 10.1 KB (minified: ~7 KB)
**Animation Count**: 3 (slide-in, pulse, hover)
**Responsive Breakpoints**: 4 major points
