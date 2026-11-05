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
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from io import BytesIO

from html_generation_agent import run_html_generation_workflow, AgentState

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


# ============================================================================
# Global State
# ============================================================================

sessions: Dict[str, Dict] = {}


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
    """Generate bot response from state"""
    if state.get("validation_errors"):
        return f"⚠️ Validation errors found: {', '.join(state['validation_errors'])}"
    
    if state.get("html_content"):
        return "✅ HTML generated successfully! Preview is ready."
    
    if state.get("design_system"):
        return "🎨 Design system created. Generating HTML..."
    
    if state.get("ux_blueprint"):
        return "📐 UI/UX blueprint created. Designing aesthetics..."
    
    if state.get("final_specifications"):
        return "📋 Requirements clarified. Creating UI/UX blueprint..."
    
    return "📝 Analyzing requirements..."


def get_progress_status(state: Dict) -> Dict[str, bool]:
    """Get progress status from state"""
    if state is None:
        state = {}
    return {
        "requirements": bool(state.get("final_specifications")),
        "ux_design": bool(state.get("ux_blueprint")),
        "aesthetics": bool(state.get("design_system")),
        "html_generation": bool(state.get("html_content")),
        "validation": not bool(state.get("validation_errors")),
    }


# ============================================================================
# API Routes
# ============================================================================

@app.get("/")
async def serve_ui():
    """Serve the main UI"""
    from fastapi.responses import FileResponse
    return FileResponse("templates/index.html")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "sessions_active": len(sessions),
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
    }
    print(f"✓ Session created: {session_id}")
    return SessionResponse(session_id=session_id)


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
    
    # Add user message to history
    session["messages"].append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat()
    })
    
    # Initialize or get state
    if session["state"] is None:
        session["state"] = {
            "user_prompt": user_message,
            "manager_clarifications": [],
            "final_specifications": "",
            "ux_blueprint": "",
            "design_system": "",
            "framework_choice": "Tailwind",
            "html_content": "",
            "validation_errors": [],
            "retry_count": 0,
            "session_id": session_id,
            "llm_provider": "",
        }
    else:
        # Update with new message
        session["state"]["user_prompt"] = user_message
    
    # Run the workflow
    try:
        state = run_html_generation_workflow(session["state"])
        session["state"] = state
        
        # Extract bot response
        bot_response = generate_bot_response(state)
        
        # Add bot message to history
        session["messages"].append({
            "role": "assistant",
            "content": bot_response,
            "timestamp": datetime.now().isoformat(),
            "state": {
                "progress": get_progress_status(state),
                "html_content": state.get("html_content", ""),
                "validation_errors": state.get("validation_errors", []),
            }
        })
        
        # Store HTML content if generated
        if state.get("html_content"):
            session["html_content"] = state["html_content"]
        
        print(f"✓ Message processed for session {session_id}")
        
        return MessageResponse(
            success=True,
            response=bot_response,
            state={
                "progress": get_progress_status(state),
                "html_content": state.get("html_content", ""),
                "validation_errors": state.get("validation_errors", []),
                "retry_count": state.get("retry_count", 0),
            }
        )
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error processing message: {error_msg}")
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


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        reload=True,
    )
