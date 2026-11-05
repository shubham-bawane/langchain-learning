"""
FastAPI Backend for HTML Generation System
Provides REST API endpoints for the chat interface and HTML generation
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from io import BytesIO
import asyncio
import logging

from website_studio_workflow import start_studio, resume_studio, LANGSMITH_ENABLED

# Setup logging to capture agent output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Data Models
# ============================================================================

class MessageRequest(BaseModel):
    """Request model for sending chat messages"""
    session_id: str
    message: str


class MessageResponse(BaseModel):
    """Response model for chat messages"""
    success: bool
    response: str
    state: Optional[Dict]
    error: Optional[str] = None


class SessionResponse(BaseModel):
    """Response model for session creation"""
    session_id: str


class PreviewResponse(BaseModel):
    """Response model for HTML preview"""
    html_content: str


class DownloadResponse(BaseModel):
    """Response model for download"""
    content: str
    filename: str


class ClarificationRequest(BaseModel):
    """Request model for answering clarification questions"""
    session_id: str
    answers: List[str]  # Answers to each question in order


# ============================================================================
# Global State
# ============================================================================

# Store active sessions with progress tracking
sessions: Dict[str, Dict] = {}
progress_updates: Dict[str, List[str]] = {}  # Track progress messages per session


# ============================================================================
# Lifecycle Events
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle"""
    print("🚀 FastAPI server starting...")
    yield
    print("🛑 FastAPI server shutting down...")


# ============================================================================
# FastAPI App Setup
# ============================================================================

app = FastAPI(
    title="HTML Generation API",
    description="Multi-agent AI system for generating HTML websites",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================================
# Helper Functions
# ============================================================================

def generate_bot_response(state: Dict) -> str:
    """Generate bot response from a website-studio result"""
    if state.get("needs_clarification"):
        questions = "\n\n".join(f"❓ {i + 1}. {q}" for i, q in enumerate(state.get("questions", [])))
        return (
            "🤔 Before I design this, a few quick questions:\n\n"
            f"{questions}\n\n"
            "Reply with numbered answers (e.g. \"1. ...  2. ...\"), or say \"you decide\" and I'll make the calls."
        )

    if state.get("final_html"):
        sections = len(state.get("completed_sections", []))
        if state.get("validation_errors"):
            return (
                f"⚠️ Website generated ({sections} sections) but QA still reports issues: "
                + "; ".join(state["validation_errors"])
            )
        assumptions = (state.get("app_blueprint") or {}).get("assumptions") or []
        note = "\n\nAssumptions I made:\n" + "\n".join(f"• {a}" for a in assumptions) if assumptions else ""
        return f"✅ Interactive website generated ({sections} sections, QA passed). Preview is ready.{note}"

    return "📝 Analyzing requirements..."


def get_progress_status(state: Dict) -> Dict[str, bool]:
    """Get progress status from a website-studio result"""
    if state is None:
        state = {}
    return {
        "requirements": bool(state.get("is_clarified")),
        "ux_design": bool(state.get("section_specs")),
        "aesthetics": bool(state.get("design_system")),
        "html_generation": bool(state.get("final_html")),
        "validation": bool(state.get("final_html")) and not state.get("validation_errors"),
    }


def current_step(state: Dict) -> str:
    if state.get("needs_clarification"):
        return "awaiting_clarification"
    if state.get("final_html"):
        return "delivered" if not state.get("validation_errors") else "qa_issues"
    return "development"


def finish_run(session: Dict, session_id: str, result: Dict) -> MessageResponse:
    """Record a workflow result (finished or paused for questions) and build the API response."""
    session["state"] = result
    session["_awaiting_clarification"] = bool(result.get("needs_clarification"))
    if result.get("final_html"):
        session["html_content"] = result["final_html"]

    bot_response = generate_bot_response(result)
    state_payload = {
        "progress": get_progress_status(result),
        "html_content": result.get("final_html", ""),
        "validation_errors": result.get("validation_errors", []),
        "retry_count": result.get("retry_count", 0),
        "current_step": current_step(result),
        "needs_clarification": bool(result.get("needs_clarification")),
        "questions": result.get("questions", []),
        "count": len(result.get("questions", [])),
    }
    session["messages"].append({
        "role": "assistant",
        "content": bot_response,
        "timestamp": datetime.now().isoformat(),
        "state": state_payload,
    })
    progress_updates[session_id].append(
        "💬 Waiting for your answers..." if result.get("needs_clarification") else "✅ Generation complete!"
    )
    return MessageResponse(success=True, response=bot_response, state=state_payload)


# ============================================================================
# API Routes
# ============================================================================

@app.get("/")
async def serve_ui():
    """Serve the main UI"""
    from fastapi.responses import FileResponse
    return FileResponse("templates/index_modern.html")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "sessions_active": len(sessions),
        "langsmith_tracing": LANGSMITH_ENABLED,
        "langsmith_project": os.getenv("LANGSMITH_PROJECT") if LANGSMITH_ENABLED else None,
    }


@app.post("/api/session/create", response_model=SessionResponse)
async def create_session():
    """Create a new chat session"""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "id": session_id,
        "created_at": datetime.now().isoformat(),
        "messages": [],
        "state": None,
        "html_content": None,
        "is_processing": False,
    }
    progress_updates[session_id] = []
    print(f"✓ Session created: {session_id}")
    return SessionResponse(session_id=session_id)


@app.get("/api/session/{session_id}/progress")
async def get_progress(session_id: str):
    """Get progress updates for current generation"""
    if session_id not in sessions:
        raise HTTPException(status_code=400, detail="Invalid session")
    
    session = sessions[session_id]
    updates = progress_updates.get(session_id, [])
    
    return {
        "session_id": session_id,
        "is_processing": session.get("is_processing", False),
        "updates": updates,
        "current_step": updates[-1] if updates else "Waiting...",
    }


@app.post("/api/chat/message", response_model=MessageResponse)
async def send_message(request: MessageRequest):
    """Send a chat message and get agent response"""
    session_id = request.session_id
    user_message = request.message
    
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=400, detail="Invalid session")
    
    if not user_message:
        raise HTTPException(status_code=400, detail="Message required")
    
    session = sessions[session_id]
    
    # Mark as processing
    session["is_processing"] = True
    progress_updates[session_id] = ["🚀 Starting generation..."]
    
    # Add user message to history
    session["messages"].append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat()
    })
    
    # Follow-ups that ask for changes revise the existing site; anything else is a new brief
    is_revision = bool(session.get("html_content")) and any(
        word in user_message.lower() for word in ["improve", "change", "update", "modify", "add", "remove", "fix"]
    )

    def on_progress(message: str) -> None:
        progress_updates[session_id].append(message)

    # The workflow is synchronous and slow; run it in a worker thread so the server
    # keeps answering /progress polls and other sessions.
    try:
        if session.get("_awaiting_clarification"):
            # This message is the client's reply to the clarifying questions
            result = await asyncio.to_thread(
                resume_studio, session["thread_id"], user_message, on_progress, session_id
            )
        else:
            if is_revision:
                prompt = (
                    f"{session['brief']}\n\nRevision request from the client "
                    f"(keep the same concept, apply this change): {user_message}"
                )
            else:
                session["brief"] = prompt = user_message
            session["thread_id"] = f"{session_id}-{uuid.uuid4().hex[:8]}"
            result = await asyncio.to_thread(
                start_studio, prompt, None, session["thread_id"], not is_revision, on_progress, session_id
            )

        print(f"✓ Message processed for session {session_id}")
        return finish_run(session, session_id, result)

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error processing message: {error_msg}")
        session["_awaiting_clarification"] = False
        progress_updates[session_id].append(f"❌ Error: {error_msg}")
        session["messages"].append({
            "role": "assistant",
            "content": f"Error: {error_msg}",
            "timestamp": datetime.now().isoformat(),
        })
        return MessageResponse(
            success=False,
            response=f"An error occurred: {error_msg}",
            state=None,
            error=error_msg,
        )
    finally:
        # Mark processing complete
        session["is_processing"] = False


@app.get("/api/preview/html")
async def get_preview(session_id: str):
    """Get the current HTML content for preview"""
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=400, detail="Invalid session")
    
    session = sessions[session_id]
    html_content = session.get("html_content", "") or ""
    
    return {"html_content": html_content}


@app.post("/api/download/html")
async def download_html(session_id: str):
    """Download the generated HTML file"""
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=400, detail="Invalid session")
    
    session = sessions[session_id]
    html_content = session.get("html_content", "")
    
    if not html_content:
        raise HTTPException(status_code=400, detail="No HTML generated yet")
    
    # Create file in memory
    filename = f"website_{session_id[:8]}.html"
    
    print(f"✓ Download initiated for session {session_id}")
    
    return {
        "success": True,
        "content": html_content,
        "filename": filename,
    }


@app.get("/api/session/{session_id}/messages")
async def get_messages(session_id: str):
    """Get all messages for a session"""
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=400, detail="Invalid session")
    
    session = sessions[session_id]
    return {
        "success": True,
        "messages": session.get("messages", []),
        "count": len(session.get("messages", [])),
    }


@app.get("/api/session/{session_id}/state")
async def get_session_state(session_id: str):
    """Get current state for a session"""
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=400, detail="Invalid session")
    
    session = sessions[session_id]
    state = session.get("state", {})
    
    return {
        "success": True,
        "state": state,
        "progress": get_progress_status(state),
    }


@app.post("/api/chat/clarify")
async def submit_clarification(request: ClarificationRequest):
    """Submit answers to clarification questions and resume workflow"""
    session_id = request.session_id
    answers = request.answers
    
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=400, detail="Invalid session")
    
    session = sessions[session_id]
    if not session.get("_awaiting_clarification"):
        raise HTTPException(status_code=400, detail="No clarification pending")

    questions = (session.get("state") or {}).get("questions", [])
    if len(answers) != len(questions):
        raise HTTPException(status_code=400, detail="Number of answers must match number of questions")

    session["is_processing"] = True
    progress_updates[session_id] = ["🚀 Resuming generation with your answers..."]

    def on_progress(message: str) -> None:
        progress_updates[session_id].append(message)

    try:
        result = await asyncio.to_thread(resume_studio, session["thread_id"], answers, on_progress, session_id)
        print(f"✓ Clarification processed for session {session_id}")
        return finish_run(session, session_id, result)

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error processing clarification: {error_msg}")
        session["_awaiting_clarification"] = False
        progress_updates[session_id].append(f"❌ Error: {error_msg}")
        return MessageResponse(
            success=False,
            response=f"Error processing clarification: {error_msg}",
            state=None,
            error=error_msg,
        )
    finally:
        session["is_processing"] = False


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
    )
