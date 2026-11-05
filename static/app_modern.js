/**
 * Website Generator AI - Modern UI
 * Handles chat, API communication, and preview updates
 */

class WebsiteGenerator {
    constructor() {
        this.sessionId = null;
        this.isLoading = false;
        this.apiBase = '/api';
        this.init();
    }

    async init() {
        try {
            await this.createSession();
            this.setupEventListeners();
            console.log('✅ Website Generator initialized');
        } catch (error) {
            console.error('❌ Initialization error:', error);
            this.showError('Failed to initialize app');
        }
    }

    async createSession() {
        try {
            const response = await fetch(`${this.apiBase}/session/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (!response.ok) throw new Error('Failed to create session');
            
            const data = await response.json();
            this.sessionId = data.session_id;
            console.log('✅ Session created:', this.sessionId);
        } catch (error) {
            console.error('❌ Session creation error:', error);
            throw error;
        }
    }

    setupEventListeners() {
        const form = document.getElementById('chat-form');
        const input = document.getElementById('message-input');
        const clearBtn = document.getElementById('clear-btn');
        const refreshBtn = document.getElementById('refresh-btn');
        const downloadBtn = document.getElementById('download-btn');
        const openTabBtn = document.getElementById('open-tab-btn');

        // Form submission
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendMessage();
            });
        }

        // Clear chat button
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                if (confirm('Clear all messages?')) {
                    document.getElementById('chat-history').innerHTML = '';
                    this.sessionId = null;
                    this.createSession();
                }
            });
        }

        // Refresh preview button
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshPreview();
            });
        }

        // Download button
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                this.downloadHTML();
            });
        }

        // Open in tab button
        if (openTabBtn) {
            openTabBtn.addEventListener('click', () => {
                this.openInNewTab();
            });
        }

        // Enter to send, Shift+Enter for new line
        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        console.log('✅ Event listeners attached');
    }

    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();

        if (!message || this.isLoading || !this.sessionId) {
            if (!this.sessionId) {
                this.showError('Creating session... please wait');
            }
            return;
        }

        this.isLoading = true;
        console.log('📤 Sending message:', message);

        try {
            // Add user message to chat
            this.addMessage(message, 'user');
            input.value = '';
            input.style.height = 'auto';

            // Show loading indicator
            this.showLoading('Generating your website...');

            // Send message to API
            const response = await fetch(`${this.apiBase}/chat/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: this.sessionId, message })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `API error: ${response.status}`);
            }

            const data = await response.json();
            console.log('📥 Received response:', {
                success: data.success,
                response: data.response?.substring(0, 50),
                stateKeys: Object.keys(data.state || {}),
                htmlLength: data.state?.html_content?.length
            });

            // Hide loading
            this.hideLoading();

            // Add bot response
            if (data.response) {
                this.addMessage(data.response, 'bot');
            }

            // Update preview if HTML is available in state
            if (data.state && data.state.html_content) {
                console.log('🖼️ Found HTML in state, updating preview...');
                this.updatePreview(data.state.html_content);
            } else {
                console.warn('⚠️ No HTML content in response state');
            }

            // Update progress if available
            if (data.state && data.state.current_step) {
                this.updateProgress(data.state.current_step);
            }

            // Show download/open buttons if HTML exists
            if (data.state && data.state.html_content) {
                document.getElementById('download-btn').style.display = 'flex';
                document.getElementById('open-tab-btn').style.display = 'flex';
            }

            // Scroll to bottom
            this.scrollToBottom();
        } catch (error) {
            this.hideLoading();
            console.error('❌ Error sending message:', error);
            this.addMessage(`❌ Error: ${error.message}`, 'bot');
        } finally {
            this.isLoading = false;
        }
    }

    addMessage(text, sender) {
        const chatHistory = document.getElementById('chat-history');
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}-message`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = sender === 'user' ? 
            '<i class="fas fa-user"></i>' : 
            '<i class="fas fa-robot"></i>';

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        bubbleDiv.innerHTML = `
            <p>${this.escapeHtml(text)}</p>
            <span class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        `;

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(bubbleDiv);
        chatHistory.appendChild(messageDiv);

        this.scrollToBottom();
    }

    updatePreview(html) {
        const iframe = document.getElementById('preview-iframe');
        const placeholder = document.getElementById('preview-placeholder');

        console.log('🎯 Updating preview with HTML length:', html ? html.length : 0);

        if (!html) {
            console.warn('⚠️ No HTML content to preview');
            return;
        }

        if (placeholder) {
            placeholder.style.display = 'none';
        }

        if (iframe) {
            iframe.style.display = 'block';
            try {
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                doc.open();
                doc.write(html);
                doc.close();

                console.log('✅ Preview updated successfully');

                // Update size info
                const size = (new Blob([html]).size / 1024).toFixed(2);
                const sizeDisplay = document.getElementById('size-display');
                if (sizeDisplay) {
                    sizeDisplay.textContent = `${size} KB`;
                }

                // Show info stats
                const infoStats = document.getElementById('info-stats');
                if (infoStats) {
                    infoStats.style.display = 'flex';
                }
            } catch (error) {
                console.error('❌ Error updating preview:', error);
                this.showError('Failed to display preview');
            }
        } else {
            console.error('❌ Preview iframe not found');
        }
    }

    updateProgress(step) {
        const steps = ['requirements', 'ux', 'design', 'html', 'validate'];
        
        steps.forEach((stepName, index) => {
            const stepEl = document.getElementById(`step-${stepName}`);
            if (stepEl) {
                const stepIndex = steps.indexOf(step);
                if (index <= stepIndex) {
                    stepEl.classList.add('active');
                    if (index < stepIndex) {
                        stepEl.classList.add('completed');
                    }
                } else {
                    stepEl.classList.remove('active', 'completed');
                }
            }
        });

        // Show progress container
        const progressContainer = document.getElementById('progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }
    }

    scrollToBottom() {
        const chatHistory = document.getElementById('chat-history');
        if (chatHistory) {
            setTimeout(() => {
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }, 100);
        }
    }

    showLoading(text = 'Generating your website...') {
        const modal = document.getElementById('loading-modal');
        const loadingText = document.getElementById('loading-text');
        
        if (modal) {
            modal.style.display = 'flex';
        }
        if (loadingText) {
            loadingText.textContent = text;
        }

        this.updateStatusIndicator('generating', 'Generating website...');
    }

    hideLoading() {
        const modal = document.getElementById('loading-modal');
        if (modal) {
            modal.style.display = 'none';
        }
        this.updateStatusIndicator('ready', 'Ready to generate');
    }

    updateStatusIndicator(status, text) {
        const statusText = document.getElementById('status-text');
        const statusDot = document.querySelector('.status-dot');

        if (statusText) {
            statusText.textContent = text;
        }
        if (statusDot) {
            statusDot.style.background = status === 'ready' ? '#10b981' : '#f59e0b';
        }
    }

    refreshPreview() {
        // Refresh the iframe
        const iframe = document.getElementById('preview-iframe');
        if (iframe && iframe.style.display !== 'none') {
            iframe.contentDocument?.location.reload();
        }
    }

    async downloadHTML() {
        try {
            const response = await fetch(`${this.apiBase}/preview/html?session_id=${this.sessionId}`);
            if (!response.ok) throw new Error('Failed to download HTML');

            const data = await response.json();
            const html = data.html_content;

            if (!html) {
                this.showError('No HTML generated yet');
                return;
            }

            // Create blob and download
            const blob = new Blob([html], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `website-${Date.now()}.html`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            console.log('✅ HTML downloaded');
        } catch (error) {
            console.error('❌ Download error:', error);
            this.showError('Failed to download HTML');
        }
    }

    openInNewTab() {
        const iframe = document.getElementById('preview-iframe');
        if (iframe && iframe.style.display !== 'none') {
            const doc = iframe.contentDocument || iframe.contentWindow.document;
            const html = doc.documentElement.outerHTML;
            const blob = new Blob([html], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            window.open(url, '_blank');
        }
    }

    showError(message) {
        this.addMessage(`❌ ${message}`, 'bot');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new WebsiteGenerator();
});
