"""
Web UI Backend for HTML Generation System
Provides REST API endpoints for the chat interface and HTML generation
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from io import BytesIO

from html_generation_agent import run_html_generation_workflow, AgentState

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Store active sessions
sessions = {}


@app.route('/')
def index():
    """Serve the main UI"""
    return render_template('index.html')


@app.route('/api/session/create', methods=['POST'])
def create_session():
    """Create a new chat session"""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        'id': session_id,
        'created_at': datetime.now().isoformat(),
        'messages': [],
        'state': None,
        'html_content': None,
    }
    return jsonify({'session_id': session_id})


@app.route('/api/chat/message', methods=['POST'])
def send_message():
    """Send a chat message and get agent response"""
    try:
        data = request.json
        session_id = data.get('session_id')
        user_message = data.get('message')
        
        if not session_id or session_id not in sessions:
            return jsonify({'error': 'Invalid session'}), 400
        
        if not user_message:
            return jsonify({'error': 'Message required'}), 400
        
        session = sessions[session_id]
        
        # Add user message to history
        session['messages'].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Initialize or get state
        if session['state'] is None:
            session['state'] = AgentState(
                user_prompt=user_message,
                manager_clarifications=[],
                final_specifications='',
                ux_blueprint='',
                design_system='',
                framework_choice='Tailwind',
                html_content='',
                validation_errors=[],
                retry_count=0,
                session_id=session_id,
                llm_provider='',
            )
        else:
            # Update with new message
            session['state']['user_prompt'] = user_message
        
        # Run the workflow (this will be async in real implementation)
        try:
            state = run_html_generation_workflow(session['state'])
            session['state'] = state
            
            # Extract bot response
            bot_response = generate_bot_response(state)
            
            # Add bot message to history
            session['messages'].append({
                'role': 'assistant',
                'content': bot_response,
                'timestamp': datetime.now().isoformat(),
                'state': {
                    'progress': get_progress_status(state),
                    'html_content': state.get('html_content', ''),
                    'validation_errors': state.get('validation_errors', []),
                }
            })
            
            # Store HTML content if generated
            if state.get('html_content'):
                session['html_content'] = state['html_content']
            
            return jsonify({
                'success': True,
                'response': bot_response,
                'state': {
                    'progress': get_progress_status(state),
                    'html_content': state.get('html_content', ''),
                    'validation_errors': state.get('validation_errors', []),
                    'retry_count': state.get('retry_count', 0),
                }
            })
        
        except Exception as e:
            error_msg = str(e)
            session['messages'].append({
                'role': 'assistant',
                'content': f'Error: {error_msg}',
                'timestamp': datetime.now().isoformat(),
            })
            return jsonify({
                'success': False,
                'error': error_msg,
                'response': f'An error occurred: {error_msg}'
            }), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/preview/html', methods=['GET'])
def get_preview():
    """Get the current HTML content for preview"""
    try:
        session_id = request.args.get('session_id')
        
        if not session_id or session_id not in sessions:
            return jsonify({'error': 'Invalid session'}), 400
        
        session = sessions[session_id]
        html_content = session.get('html_content', '')
        
        if not html_content:
            return jsonify({'error': 'No HTML generated yet'}), 404
        
        return jsonify({
            'html': html_content,
            'framework': session['state'].get('framework_choice', 'Tailwind') if session['state'] else 'Tailwind'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/html', methods=['GET'])
def download_html():
    """Download the generated HTML file"""
    try:
        session_id = request.args.get('session_id')
        
        if not session_id or session_id not in sessions:
            return jsonify({'error': 'Invalid session'}), 400
        
        session = sessions[session_id]
        html_content = session.get('html_content', '')
        
        if not html_content:
            return jsonify({'error': 'No HTML generated yet'}), 404
        
        # Create a BytesIO object
        file_data = BytesIO(html_content.encode('utf-8'))
        
        return send_file(
            file_data,
            mimetype='text/html',
            as_attachment=True,
            download_name=f'website_{session_id[:8]}.html'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>/messages', methods=['GET'])
def get_messages(session_id):
    """Get all messages in a session"""
    try:
        if session_id not in sessions:
            return jsonify({'error': 'Invalid session'}), 400
        
        session = sessions[session_id]
        return jsonify({'messages': session['messages']})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def generate_bot_response(state: dict) -> str:
    """Generate a bot response based on current state"""
    messages = []
    
    if state.get('final_specifications'):
        messages.append("✓ Requirements clarified and finalized")
    
    if state.get('ux_blueprint'):
        messages.append("✓ UX blueprint created")
    
    if state.get('design_system'):
        messages.append("✓ Design system defined")
    
    if state.get('html_content'):
        if state.get('validation_errors'):
            messages.append(f"⚠ HTML generated but has {len(state['validation_errors'])} validation errors")
        else:
            messages.append("✓ Website generated successfully!")
            messages.append(f"📦 Framework: {state.get('framework_choice', 'Tailwind')}")
    
    if state.get('validation_errors'):
        messages.append(f"⚠ Validation errors:\n" + "\n".join(f"  • {e}" for e in state['validation_errors'][:3]))
    
    if not messages:
        messages.append("Processing your request...")
    
    return "\n".join(messages)


def get_progress_status(state: dict) -> dict:
    """Get progress status for UI"""
    return {
        'requirements_clarified': bool(state.get('final_specifications')),
        'ux_designed': bool(state.get('ux_blueprint')),
        'design_complete': bool(state.get('design_system')),
        'html_generated': bool(state.get('html_content')),
        'validated': len(state.get('validation_errors', [])) == 0,
        'retry_count': state.get('retry_count', 0),
        'framework': state.get('framework_choice', 'Tailwind'),
    }


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'active_sessions': len(sessions),
        'timestamp': datetime.now().isoformat()
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Run the development server
    app.run(debug=True, host='0.0.0.0', port=5000)
