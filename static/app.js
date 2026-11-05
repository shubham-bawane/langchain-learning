/**
 * Frontend Application for HTML Generation AI System
 * Handles chat interaction, preview updates, and file operations
 */

class ChatApp {
    constructor() {
        this.sessionId = null;
        this.state = null;
        this.isLoading = false;
        this.apiBase = '/api';
        
        this.init();
    }

    async init() {
        // Create a new session
        const response = await fetch(`${this.apiBase}/session/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        this.sessionId = data.session_id;
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Log ready state
        console.log(`✓ Session created: ${this.sessionId}`);
    }

    setupEventListeners() {
        // Chat form submission
        document.getElementById('chat-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Message input - handle Shift+Enter for new line
        const input = document.getElementById('message-input');
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Clear chat button
        document.getElementById('clear-btn').addEventListener('click', () => {
            this.clearChat();
        });

        // Preview controls
        document.getElementById('open-tab-btn').addEventListener('click', () => {
            this.openInNewTab();
        });

        document.getElementById('download-btn').addEventListener('click', () => {
            this.downloadHTML();
        });

        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.refreshPreview();
        });
    }

    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();

        if (!message) {
            return;
        }

        // Disable input while sending
        input.disabled = true;
        document.getElementById('send-btn').disabled = true;

        // Add user message to chat
        this.addMessageToChat(message, 'user');
        input.value = '';

        // Show loading state
        this.showLoading('Processing your request...');

        try {
            // Send message to backend
            const response = await fetch(`${this.apiBase}/chat/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    message: message
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to send message');
            }

            // Add bot response to chat
            this.addMessageToChat(data.response, 'bot');

            // Update state and progress
            if (data.state) {
                this.state = data.state;
                this.updateProgress(data.state.progress);
                
                // Update preview if HTML is available
                if (data.state.html_content) {
                    this.updatePreview(data.state.html_content, data.state.progress?.framework);
                    this.showPreviewControls();
                }

                // Show validation errors if any
                if (data.state.validation_errors && data.state.validation_errors.length > 0) {
                    this.showValidationErrors(data.state.validation_errors);
                }
            }

        } catch (error) {
            console.error('Error:', error);
            this.addMessageToChat(`⚠ Error: ${error.message}`, 'bot');
        } finally {
            // Re-enable input
            input.disabled = false;
            document.getElementById('send-btn').disabled = false;
            this.hideLoading();
            input.focus();
        }
    }

    addMessageToChat(content, role) {
        const chatHistory = document.getElementById('chat-history');
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}-message`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Handle multiline content
        const lines = content.split('\n');
        lines.forEach((line, index) => {
            const p = document.createElement('p');
            p.textContent = line;
            if (index === lines.length - 1) {
                p.style.marginBottom = '0.5rem';
            }
            contentDiv.appendChild(p);
        });

        const timeDiv = document.createElement('small');
        timeDiv.className = 'message-time';
        timeDiv.textContent = this.getCurrentTime();
        contentDiv.appendChild(timeDiv);

        messageDiv.appendChild(contentDiv);
        chatHistory.appendChild(messageDiv);

        // Scroll to bottom
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    updateProgress(progress) {
        if (!progress) return;

        const progressSection = document.getElementById('progress-section');
        progressSection.style.display = 'block';

        const steps = [
            { id: 'step-requirements', completed: progress.requirements_clarified },
            { id: 'step-ux', completed: progress.ux_designed },
            { id: 'step-design', completed: progress.design_complete },
            { id: 'step-html', completed: progress.html_generated },
            { id: 'step-validate', completed: progress.validated }
        ];

        steps.forEach(step => {
            const element = document.getElementById(step.id);
            if (step.completed) {
                element.classList.add('completed');
                element.querySelector('.step-icon').textContent = '✓';
            }
        });

        // Update status text
        const statusText = document.getElementById('status-text');
        if (progress.validated) {
            statusText.textContent = 'Complete';
            statusText.style.color = 'var(--success-color)';
        } else if (progress.html_generated) {
            statusText.textContent = 'Validating';
            statusText.style.color = 'var(--warning-color)';
        } else if (progress.design_complete) {
            statusText.textContent = 'Generating';
            statusText.style.color = 'var(--primary-color)';
        }

        // Update info panel
        this.updateInfoPanel(progress);
    }

    updateInfoPanel(progress) {
        const infoPanel = document.getElementById('info-panel');
        infoPanel.style.display = 'flex';

        document.getElementById('framework-display').textContent = progress.framework || 'Tailwind CSS';
        
        const statusElement = document.getElementById('validation-status');
        if (progress.validated) {
            statusElement.textContent = '✓ Valid';
            statusElement.style.color = 'var(--success-color)';
        } else if (progress.html_generated) {
            statusElement.textContent = `⚠ Retry ${progress.retry_count}/3`;
            statusElement.style.color = 'var(--warning-color)';
        } else {
            statusElement.textContent = 'Pending';
            statusElement.style.color = 'var(--text-secondary)';
        }
    }

    async updatePreview(htmlContent, framework) {
        const iframe = document.getElementById('preview-iframe');
        const placeholder = document.getElementById('preview-placeholder');

        try {
            // Write HTML to iframe
            iframe.style.display = 'block';
            placeholder.style.display = 'none';
            
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
            iframeDoc.open();
            iframeDoc.write(htmlContent);
            iframeDoc.close();

            // Update framework display
            if (framework) {
                document.getElementById('framework-display').textContent = framework;
            }

            // Update size display
            const sizeKB = (htmlContent.length / 1024).toFixed(2);
            document.getElementById('size-display').textContent = `${sizeKB} KB`;

        } catch (error) {
            console.error('Error updating preview:', error);
            placeholder.style.display = 'flex';
            iframe.style.display = 'none';
        }
    }

    showValidationErrors(errors) {
        const errorSection = document.getElementById('error-section');
        const errorList = document.getElementById('error-list');
        
        errorList.innerHTML = '';
        errors.forEach(error => {
            const li = document.createElement('li');
            li.textContent = error;
            errorList.appendChild(li);
        });

        errorSection.style.display = 'block';
    }

    showPreviewControls() {
        document.getElementById('open-tab-btn').style.display = 'flex';
        document.getElementById('download-btn').style.display = 'flex';
    }

    openInNewTab() {
        if (!this.state || !this.state.html_content) {
            alert('No HTML generated yet');
            return;
        }

        const blob = new Blob([this.state.html_content], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
    }

    downloadHTML() {
        if (!this.state || !this.state.html_content) {
            alert('No HTML generated yet');
            return;
        }

        const blob = new Blob([this.state.html_content], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `website_${this.sessionId.substring(0, 8)}.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    async refreshPreview() {
        try {
            const response = await fetch(
                `${this.apiBase}/preview/html?session_id=${this.sessionId}`
            );

            if (!response.ok) {
                throw new Error('No preview available');
            }

            const data = await response.json();
            this.updatePreview(data.html, data.framework);

        } catch (error) {
            console.error('Error refreshing preview:', error);
            alert('Could not refresh preview');
        }
    }

    clearChat() {
        if (confirm('Clear all messages? You can start a new chat session.')) {
            // Reset to new session
            window.location.reload();
        }
    }

    showLoading(text) {
        const modal = document.getElementById('loading-modal');
        document.getElementById('loading-text').textContent = text;
        modal.style.display = 'flex';
        this.isLoading = true;
    }

    hideLoading() {
        const modal = document.getElementById('loading-modal');
        modal.style.display = 'none';
        this.isLoading = false;
    }

    getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit',
            hour12: true 
        });
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
    console.log('✓ Chat application initialized');
});
