"""
API Bridge - Connects FastAPI to the IT Service Company Workflow

Adapts between:
- REST API calls from the web UI
- Internal service company workflow
- LangSmith monitoring
"""

from typing import Optional, Dict, Any
from datetime import datetime
from service_company_workflow import (
    run_service_company_workflow,
    ServiceCompanyState,
    ClientRequest,
    LLMConfig
)
from langgraph.types import Interrupt


class ServiceCompanyAPIBridge:
    """Bridge between REST API and service company workflow."""
    
    @staticmethod
    def convert_chat_to_client_request(session_id: str, user_message: str) -> ServiceCompanyState:
        """Convert REST API chat message to service company workflow state."""
        
        # Parse user message to extract project details
        # This would be improved with better parsing/extraction
        
        request_state = ServiceCompanyState(
            client_id=session_id,
            client_request={
                "client_name": "Web Client",
                "project_description": user_message,
                "budget_tier": "standard",
                "timeline": "7"
            },
            account_manager_notes="",
            ux_designer_blueprint="",
            design_system={},
            creative_direction={},
            developer_code="",
            qa_test_report="",
            project_status="inquiry",
            project_timeline={},
            estimated_cost=0.0,
            assigned_team={},
            validation_errors=[],
            warnings=[],
            retry_count=0,
            html_content="",
            design_assets={},
            documentation="",
            framework_choice="Tailwind",
            tech_stack=["HTML5", "CSS3", "JavaScript"],
            llm_provider=LLMConfig.get_default_provider(),
            session_id=session_id
        )
        
        return request_state
    
    @staticmethod
    async def process_client_request(user_message: str, session_id: str) -> Dict[str, Any]:
        """Process a client request through the service company workflow."""
        
        # Convert to internal state
        initial_state = ServiceCompanyAPIBridge.convert_chat_to_client_request(
            session_id, 
            user_message
        )
        
        try:
            # Run workflow
            result_state = run_service_company_workflow(initial_state)
            
            # Extract stakeholder responses
            responses = {
                "account_manager": result_state.get("account_manager_notes", ""),
                "ux_designer": result_state.get("ux_designer_blueprint", ""),
                "design_team": result_state.get("design_system", {}),
                "developer": result_state.get("developer_code", ""),
                "qa_tester": result_state.get("qa_test_report", ""),
                "project_manager": result_state.get("documentation", "")
            }
            
            # Create human-readable summary
            summary = f"""
🏢 **IT Service Company Project Update**

**Project Status:** {result_state.get('project_status', 'unknown').upper()}

**Account Manager Notes:**
{result_state.get('account_manager_notes', 'Gathering requirements...')}

**Design System Created:**
Framework: {result_state.get('framework_choice', 'Tailwind')}

**Quality Assurance Report:**
{result_state.get('qa_test_report', 'Testing in progress...')}

**Errors:** {len(result_state.get('validation_errors', []))}
**Warnings:** {len(result_state.get('warnings', []))}
            """
            
            return {
                "success": True,
                "response": summary,
                "state": {
                    "html_content": result_state.get("html_content", ""),
                    "validation_errors": result_state.get("validation_errors", []),
                    "warnings": result_state.get("warnings", []),
                    "project_status": result_state.get("project_status", "unknown"),
                    "stakeholder_responses": responses,
                    "design_system": result_state.get("design_system", {}),
                    "current_step": result_state.get("project_status", "inquiry")
                }
            }
        
        except Interrupt as e:
            # Clarification needed
            return {
                "success": True,
                "response": f"🤔 {str(e)}",
                "state": {
                    "needs_clarification": True,
                    "message": str(e),
                    "project_status": "awaiting_clarification"
                }
            }
        
        except Exception as e:
            return {
                "success": False,
                "response": f"❌ Error processing request: {str(e)}",
                "error": str(e),
                "state": {
                    "project_status": "error"
                }
            }


# Example usage in FastAPI
if __name__ == "__main__":
    import asyncio
    
    async def test():
        result = await ServiceCompanyAPIBridge.process_client_request(
            user_message="Create a beautiful landing page for a tech startup with a dark theme",
            session_id="TEST_SESSION_001"
        )
        
        print("Result:", result)
    
    asyncio.run(test())
