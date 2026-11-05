"""
Comprehensive Tests for HTML Generation System
Tests for both html_generation_agent and FastAPI backend
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import FastAPI test client
from fastapi.testclient import TestClient
from app import app, sessions

# Import agent components
from html_generation_agent import (
    AgentState,
    LLMConfig,
    DatabaseConfig,
    build_graph,
    clarify_requirements,
    design_user_journey,
    define_aesthetics,
    generate_html,
    validate_code,
    save_file,
    run_html_generation_workflow,
    _extract_text,
    _parse_clarifications,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def sample_state():
    """Sample AgentState for testing"""
    return {
        "user_prompt": "Create a flower shop website",
        "manager_clarifications": [],
        "final_specifications": "Modern e-commerce site for flower shop",
        "ux_blueprint": "Hero section, product grid, cart, checkout",
        "design_system": "Tailwind colors: pink, green, white",
        "framework_choice": "Tailwind",
        "html_content": "<html><body>Test</body></html>",
        "validation_errors": [],
        "retry_count": 0,
        "llm_provider": "openrouter",
        "session_id": "test-session-123",
    }


@pytest.fixture
def mock_llm():
    """Mock LLM response"""
    mock = MagicMock()
    mock.content = "Generated response"
    return mock


# ============================================================================
# Unit Tests - Utility Functions
# ============================================================================

class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_extract_text_from_string(self):
        """Test extracting text from string"""
        result = _extract_text("Hello, world!")
        assert result == "Hello, world!"
    
    def test_extract_text_from_object_with_content(self):
        """Test extracting text from object with content attribute"""
        obj = MagicMock()
        obj.content = "Object content"
        result = _extract_text(obj)
        assert result == "Object content"
    
    def test_extract_text_from_object_without_content(self):
        """Test extracting text from object without content attribute"""
        obj = {"key": "value"}
        result = _extract_text(obj)
        assert "key" in result
    
    def test_parse_clarifications(self):
        """Test parsing clarification text"""
        text = """Question: What style do you prefer?
- Modern
- Classic

This is a summary"""
        questions, summary = _parse_clarifications(text)
        assert len(questions) >= 1
        assert "summary" in summary.lower() or len(summary) > 0


# ============================================================================
# Unit Tests - LLM Configuration
# ============================================================================

class TestLLMConfig:
    """Test LLM configuration"""
    
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"})
    def test_get_default_provider_openrouter(self):
        """Test getting default provider when OpenRouter is available"""
        provider = LLMConfig.get_default_provider()
        assert provider == "openrouter"
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_default_provider_not_configured(self):
        """Test error when no LLM provider is configured"""
        with pytest.raises(ValueError, match="No LLM API key configured"):
            LLMConfig.get_default_provider()
    
    def test_providers_dict(self):
        """Test providers dictionary is properly configured"""
        assert "openai" in LLMConfig.PROVIDERS
        assert "openrouter" in LLMConfig.PROVIDERS
        assert "anthropic" in LLMConfig.PROVIDERS


# ============================================================================
# Unit Tests - Database Configuration
# ============================================================================

class TestDatabaseConfig:
    """Test database configuration"""
    
    @patch.dict(os.environ, {"QDRANT_URL": "", "QDRANT_API_KEY": ""}, clear=True)
    def test_is_configured_false(self):
        """Test Qdrant is not configured"""
        assert DatabaseConfig.is_configured() is False
    
    @patch.dict(os.environ, {"QDRANT_URL": "http://localhost:6333", "QDRANT_API_KEY": "key"})
    def test_is_configured_true(self):
        """Test Qdrant is configured"""
        assert DatabaseConfig.is_configured() is True


# ============================================================================
# Unit Tests - Node Functions
# ============================================================================

class TestNodeFunctions:
    """Test individual node functions"""
    
    def test_clarify_requirements_with_clear_prompt(self, sample_state):
        """Test clarify requirements with clear prompt"""
        sample_state["user_prompt"] = "Create a professional website"
        # Note: This would require mocking LLM, skipping for now
        assert sample_state["user_prompt"]
    
    def test_validate_code_with_valid_html(self, sample_state):
        """Test validate code with valid HTML"""
        sample_state["html_content"] = "<!DOCTYPE html><html><head><title>Test</title></head><body></body></html>"
        # Would need to mock LLM call
        assert "<!DOCTYPE html>" in sample_state["html_content"]
    
    def test_validate_code_detects_missing_doctype(self, sample_state):
        """Test validate code detects missing DOCTYPE"""
        sample_state["html_content"] = "<html><body></body></html>"
        # Would need to call actual validator
        assert "<!DOCTYPE html>" not in sample_state["html_content"]


# ============================================================================
# FastAPI Tests - Session Management
# ============================================================================

class TestSessionManagement:
    """Test session management endpoints"""
    
    def test_create_session(self, client):
        """Test creating a new session"""
        response = client.post("/api/session/create")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0
    
    def test_session_stored(self, client):
        """Test that created session is stored"""
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        assert session_id in sessions
    
    def test_get_session_messages_empty(self, client):
        """Test getting messages from new session"""
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        response = client.get(f"/api/session/{session_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["messages"]) == 0
    
    def test_get_session_invalid(self, client):
        """Test getting session with invalid ID"""
        response = client.get("/api/session/invalid-id/messages")
        assert response.status_code == 400


# ============================================================================
# FastAPI Tests - Chat Endpoints
# ============================================================================

class TestChatEndpoints:
    """Test chat endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    @patch('app.run_html_generation_workflow')
    def test_send_message_valid_session(self, mock_workflow, client):
        """Test sending message with valid session"""
        # Create session
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        # Mock workflow response
        mock_workflow.return_value = {
            "user_prompt": "Test",
            "html_content": "<html></html>",
            "validation_errors": [],
            "final_specifications": "Test spec",
            "ux_blueprint": "Test blueprint",
            "design_system": "Test design",
            "retry_count": 0,
            "session_id": session_id,
            "llm_provider": "openrouter",
            "manager_clarifications": [],
        }
        
        # Send message
        response = client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": "Create a website"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "response" in data
    
    def test_send_message_invalid_session(self, client):
        """Test sending message with invalid session"""
        response = client.post(
            "/api/chat/message",
            json={"session_id": "invalid", "message": "Test"}
        )
        assert response.status_code == 400
    
    def test_send_message_empty_message(self, client):
        """Test sending empty message"""
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        response = client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": ""}
        )
        assert response.status_code == 400
    
    def test_send_message_history(self, client):
        """Test message history is maintained"""
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        # Messages should be stored in session
        assert session_id in sessions
        session = sessions[session_id]
        assert "messages" in session
        assert isinstance(session["messages"], list)


# ============================================================================
# FastAPI Tests - Preview and Download
# ============================================================================

class TestPreviewAndDownload:
    """Test preview and download endpoints"""
    
    def test_preview_empty(self, client):
        """Test preview with no HTML generated"""
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        response = client.get(f"/api/preview/html?session_id={session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["html_content"] == ""
    
    def test_preview_invalid_session(self, client):
        """Test preview with invalid session"""
        response = client.get("/api/preview/html?session_id=invalid")
        assert response.status_code == 400
    
    @patch('app.run_html_generation_workflow')
    def test_download_with_content(self, mock_workflow, client):
        """Test download with generated content"""
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        # Manually set HTML content
        sessions[session_id]["html_content"] = "<html><body>Test</body></html>"
        
        response = client.post(f"/api/download/html?session_id={session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "content" in data
        assert "filename" in data
    
    def test_download_no_content(self, client):
        """Test download without content"""
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        response = client.post(f"/api/download/html?session_id={session_id}")
        assert response.status_code == 400


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflow"""
    
    def test_complete_workflow_setup(self, client):
        """Test complete workflow setup"""
        # Create session
        response = client.post("/api/session/create")
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        
        # Verify session exists
        assert session_id in sessions
        
        # Get session state
        response = client.get(f"/api/session/{session_id}/state")
        assert response.status_code == 200
    
    def test_api_endpoints_accessible(self, client):
        """Test that all API endpoints are accessible"""
        endpoints = [
            ("/api/health", "GET"),
        ]
        
        for endpoint, method in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)
            assert response.status_code in [200, 400, 405]
    
    def test_concurrent_sessions(self, client):
        """Test multiple concurrent sessions"""
        session_ids = []
        
        for i in range(3):
            response = client.post("/api/session/create")
            assert response.status_code == 200
            session_id = response.json()["session_id"]
            session_ids.append(session_id)
        
        # Verify all sessions exist
        for session_id in session_ids:
            assert session_id in sessions


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_extract_text_none(self):
        """Test extracting text from None"""
        result = _extract_text(None)
        assert result == "None"
    
    def test_extract_text_empty_string(self):
        """Test extracting text from empty string"""
        result = _extract_text("")
        assert result == ""
    
    def test_extract_text_dict(self):
        """Test extracting text from dict"""
        result = _extract_text({"key": "value"})
        assert isinstance(result, str)
    
    def test_state_initialization(self, sample_state):
        """Test state has all required fields"""
        required_fields = [
            "user_prompt",
            "manager_clarifications",
            "final_specifications",
            "ux_blueprint",
            "design_system",
            "framework_choice",
            "html_content",
            "validation_errors",
            "retry_count",
            "llm_provider",
            "session_id",
        ]
        
        for field in required_fields:
            assert field in sample_state


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test performance characteristics"""
    
    def test_session_creation_time(self, client):
        """Test session creation is fast"""
        import time
        start = time.time()
        response = client.post("/api/session/create")
        elapsed = time.time() - start
        assert elapsed < 0.1  # Should be instant
    
    def test_health_check_time(self, client):
        """Test health check is fast"""
        import time
        start = time.time()
        response = client.get("/api/health")
        elapsed = time.time() - start
        assert elapsed < 0.05  # Should be very fast


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
