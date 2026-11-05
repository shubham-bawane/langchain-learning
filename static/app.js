/**
 * Website Generator AI - ChatGPT/Claude-like UI
 * Features:
 * - Chat-based conversation flow
 * - Streaming responses
 * - Message history
 * - Live preview with progress tracking
 * - Multi-turn conversation memory
 */

class WebsiteGeneratorApp {
    constructor() {
        this.sessionId = null;
        this.conversations = [];
        this.currentConversation = null;
        this.isLoading = false;
        this.apiBase = '/api';
        this.previewHtml = null;
        
        this.init();
    }

    async init() {
        await this.createNewSession();
        this.setupEventListeners();
        this.renderConversations();
        this.addBotMessage('👋 Hi! I\'m your AI website designer. Tell me what website you\'d like to create! You can describe it step by step, and I\'ll iterate with you.');
        console.log('✓ Website Generator App initialized');
    }

    // ========================================================================
    // SESSION & CONVERSATION MANAGEMENT
    // ========================================================================

    async createNewSession() {
        try {
            const response = await fetch(`${this.apiBase}/session/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (!response.ok) throw new Error('Failed to create session');
            
            const data = await response.json();
            this.sessionId = data.session_id;
            
            // Create new conversation
            this.currentConversation = {
                id: this.sessionId,
                title: 'New Website',
                messages: [],
                createdAt: new Date(),
                framework: null,
                status: 'ready'
            };
            
            this.conversations.unshift(this.currentConversation);
            this.renderConversations();
            this.clearMessagesContainer();
            
            console.log(`✓ Session created: ${this.sessionId}`);
        } catch (error) {
            console.error('Error creating session:', error);
            this.addErrorMessage('Failed to create new session');
        }
    }

    // ========================================================================
    // MESSAGE HANDLING
    // ========================================================================

    addMessageToChat(text, sender = 'user', streaming = false) {
        const container = document.getElementById('messages-container');
        const messageEl = document.createElement('div');
        messageEl.className = `message ${sender}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = sender === 'user' ? '👤' : '🤖';
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        const textEl = document.createElement('div');
        textEl.className = 'message-text';
        textEl.textContent = text;
        
        const timeEl = document.createElement('div');
        timeEl.className = 'message-time';
        timeEl.textContent = this.formatTime(new Date());
        
        bubble.appendChild(textEl);
        bubble.appendChild(timeEl);
        messageEl.appendChild(avatar);
        messageEl.appendChild(bubble);
        
        // Store reference for streaming updates
        if (streaming) {
            messageEl.id = `message-${Date.now()}`;
            messageEl.dataset.streaming = 'true';
        }
        
        container.appendChild(messageEl);
        this.scrollToBottom();
        
        // Store in conversation
        if (this.currentConversation) {
            this.currentConversation.messages.push({
                sender,
                text,
                timestamp: new Date()
            });
        }
        
        return messageEl;
    }

    addBotMessage(text) {
        return this.addMessageToChat(text, 'assistant', false);
    }

    addUserMessage(text) {
        return this.addMessageToChat(text, 'user', false);
    }

    addErrorMessage(text) {
        const container = document.getElementById('messages-container');
        const messageEl = document.createElement('div');
        messageEl.className = 'message assistant';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = '⚠️';
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.style.borderColor = 'var(--accent-red)';
        
        const textEl = document.createElement('div');
        textEl.className = 'message-text';
        textEl.style.color = 'var(--accent-red)';
        textEl.textContent = text;
        
        bubble.appendChild(textEl);
        messageEl.appendChild(avatar);
        messageEl.appendChild(bubble);
        
        container.appendChild(messageEl);
        this.scrollToBottom();
    }

    addLoadingIndicator() {
        const container = document.getElementById('messages-container');
        const msgEl = document.createElement('div');
        msgEl.className = 'message assistant';
        msgEl.id = 'loading-indicator';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = '🤖';
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        const dotsEl = document.createElement('div');
        dotsEl.className = 'loading-dots';
        dotsEl.innerHTML = '<span class="loading-dot"></span><span class="loading-dot"></span><span class="loading-dot"></span>';
        
        bubble.appendChild(dotsEl);
        msgEl.appendChild(avatar);
        msgEl.appendChild(bubble);
        
        container.appendChild(msgEl);
        this.scrollToBottom();
    }

    removeLoadingIndicator() {
        const loadingEl = document.getElementById('loading-indicator');
        if (loadingEl) loadingEl.remove();
    }

    updateLastMessage(text, append = false) {
        const container = document.getElementById('messages-container');
        const messages = container.querySelectorAll('.message.assistant');
        if (messages.length === 0) return;
        
        const lastMsg = messages[messages.length - 1];
        const textEl = lastMsg.querySelector('.message-text');
        
        if (append) {
            textEl.textContent += text;
        } else {
            textEl.textContent = text;
        }
        
        this.scrollToBottom();
    }

    scrollToBottom() {
        const container = document.getElementById('chat-container');
        if (!container) return;
        
        setTimeout(() => {
            const messages = document.getElementById('messages-container');
            messages.parentElement.scrollTop = messages.parentElement.scrollHeight;
        }, 0);
    }

    clearMessagesContainer() {
        const container = document.getElementById('messages-container');
        container.innerHTML = '';
    }

    // ========================================================================
    // CHAT INTERACTION
    // ========================================================================

    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();

        if (!message || this.isLoading) return;

        // Add user message
        this.addUserMessage(message);
        input.value = '';
        input.style.height = 'auto';

        this.isLoading = true;
        document.getElementById('send-btn').disabled = true;

        // Show loading indicator
        this.addLoadingIndicator();

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

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Remove loading indicator
            this.removeLoadingIndicator();

            if (data.success) {
                // Add bot response with streaming effect
                await this.streamResponse(data.response);

                // Update conversation title if first message
                if (this.currentConversation.messages.length <= 2) {
                    this.currentConversation.title = message.substring(0, 40) + '...';
                    this.renderConversations();
                }

                // Update preview if HTML is available
                if (data.state && data.state.html_content) {
                    this.previewHtml = data.state.html_content;
                    this.updatePreview(data.state);
                    this.showProgressSteps(data.state);
                }

                // Update framework display
                if (data.state && data.state.framework_choice) {
                    document.getElementById('framework-display').textContent = data.state.framework_choice;
                }
            } else {
                this.addErrorMessage(data.error || 'Failed to process message');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.removeLoadingIndicator();
            this.addErrorMessage('Error communicating with server: ' + error.message);
        } finally {
            this.isLoading = false;
            document.getElementById('send-btn').disabled = false;
            input.focus();
        }
    }

    async streamResponse(text) {
        // Create message for streaming
        const msgEl = this.addBotMessage('');
        const textEl = msgEl.querySelector('.message-text');
        
        let fullText = '';
        let index = 0;
        const chunkSize = 3;
        const delay = 10;

        // Simulate streaming by revealing text gradually
        return new Promise(resolve => {
            const typeInterval = setInterval(() => {
                if (index < text.length) {
                    const chunk = text.substring(index, index + chunkSize);
                    fullText += chunk;
                    textEl.textContent = fullText;
                    index += chunkSize;
                    this.scrollToBottom();
                } else {
                    clearInterval(typeInterval);
                    resolve();
                }
            }, delay);
        });
    }

    showProgressSteps(state) {
        // Show progress indicator based on state
        const progressSection = document.querySelector('.progress-section');
        if (!progressSection) {
            const container = document.getElementById('messages-container');
            const progressEl = document.createElement('div');
            progressEl.className = 'progress-section';
            progressEl.innerHTML = `
                <div class="progress-title">Generation Progress</div>
                <div class="progress-steps">
                    <div class="progress-step completed" id="step-requirements">
                        <span class="step-icon">✓</span>
                        <span class="step-label">Requirements</span>
                    </div>
                    <div class="progress-step ${state.ux_blueprint ? 'completed' : 'active'}" id="step-ux">
                        <span class="step-icon">${state.ux_blueprint ? '✓' : '●'}</span>
                        <span class="step-label">UX Design</span>
                    </div>
                    <div class="progress-step ${state.design_system ? 'completed' : 'active'}" id="step-design">
                        <span class="step-icon">${state.design_system ? '✓' : '●'}</span>
                        <span class="step-label">Aesthetics</span>
                    </div>
                    <div class="progress-step ${state.html_content ? 'completed' : 'active'}" id="step-html">
                        <span class="step-icon">${state.html_content ? '✓' : '●'}</span>
                        <span class="step-label">HTML Code</span>
                    </div>
                    <div class="progress-step ${state.validation_errors?.length === 0 ? 'completed' : 'active'}" id="step-validate">
                        <span class="step-icon">${state.validation_errors?.length === 0 ? '✓' : '●'}</span>
                        <span class="step-label">Validation</span>
                    </div>
                </div>
            `;
            container.appendChild(progressEl);
        }
    }

    // ========================================================================
    // PREVIEW MANAGEMENT
    // ========================================================================

    updatePreview(state) {
        const iframe = document.getElementById('preview-iframe');
        const placeholder = document.getElementById('preview-placeholder');
        
        if (state.html_content) {
            // Show iframe and hide placeholder
            placeholder.style.display = 'none';
            iframe.style.display = 'block';
            
            // Set iframe content
            iframe.srcdoc = state.html_content;
            
            // Show download button
            document.getElementById('download-btn').style.display = 'flex';
            
            // Show preview info
            document.getElementById('preview-info').style.display = 'block';
            document.getElementById('status-display').textContent = 'Generated ✓';
        }
    }

    refreshPreview() {
        if (this.previewHtml) {
            const iframe = document.getElementById('preview-iframe');
            iframe.srcdoc = this.previewHtml;
        }
    }

    openFullscreenPreview() {
        const modal = document.getElementById('fullscreen-modal');
        const iframe = document.getElementById('fullscreen-iframe');
        
        if (this.previewHtml) {
            iframe.srcdoc = this.previewHtml;
            modal.style.display = 'flex';
        }
    }

    closeFullscreenPreview() {
        const modal = document.getElementById('fullscreen-modal');
        modal.style.display = 'none';
    }

    downloadHTML() {
        if (!this.previewHtml) {
            alert('No HTML to download yet');
            return;
        }

        const element = document.createElement('a');
        element.setAttribute('href', 'data:text/html;charset=utf-8,' + encodeURIComponent(this.previewHtml));
        element.setAttribute('download', `website-${Date.now()}.html`);
        element.style.display = 'none';
        
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    }

    // ========================================================================
    // CONVERSATION MANAGEMENT
    // ========================================================================

    renderConversations() {
        const list = document.getElementById('conversations-list');
        list.innerHTML = '';

        if (this.conversations.length === 0) {
            list.innerHTML = '<div style="color: var(--text-tertiary); font-size: 0.85rem; padding: var(--spacing-md);">No conversations yet</div>';
            return;
        }

        this.conversations.forEach((conv, index) => {
            const item = document.createElement('div');
            item.className = 'conversation-item';
            if (conv.id === this.currentConversation?.id) {
                item.classList.add('active');
            }
            
            item.textContent = conv.title || 'New Website';
            item.addEventListener('click', () => this.loadConversation(conv));
            list.appendChild(item);
        });
    }

    loadConversation(conversation) {
        this.currentConversation = conversation;
        this.sessionId = conversation.id;
        
        // Clear and reload messages
        this.clearMessagesContainer();
        conversation.messages.forEach(msg => {
            this.addMessageToChat(msg.text, msg.sender);
        });
        
        // Update preview if available
        if (conversation.htmlContent) {
            this.previewHtml = conversation.htmlContent;
            this.updatePreview({ html_content: conversation.htmlContent });
        }
        
        this.renderConversations();
    }

    // ========================================================================
    // EVENT SETUP
    // ========================================================================

    setupEventListeners() {
        // Send message
        document.getElementById('chat-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Message input - auto-resize and handle Enter
        const textarea = document.getElementById('message-input');
        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
        });

        textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // New chat
        document.getElementById('new-chat-btn').addEventListener('click', () => {
            this.createNewSession();
        });

        // Clear history
        document.getElementById('clear-history-btn').addEventListener('click', () => {
            if (confirm('Clear all messages in this chat?')) {
                this.clearMessagesContainer();
                if (this.currentConversation) {
                    this.currentConversation.messages = [];
                }
            }
        });

        // Preview controls
        document.getElementById('refresh-preview-btn').addEventListener('click', () => {
            this.refreshPreview();
        });

        document.getElementById('fullscreen-btn').addEventListener('click', () => {
            this.openFullscreenPreview();
        });

        document.getElementById('download-btn').addEventListener('click', () => {
            this.downloadHTML();
        });

        // Close fullscreen modal
        document.getElementById('close-modal').addEventListener('click', () => {
            this.closeFullscreenPreview();
        });

        // Close modal on background click
        document.getElementById('fullscreen-modal').addEventListener('click', (e) => {
            if (e.target.id === 'fullscreen-modal') {
                this.closeFullscreenPreview();
            }
        });

        // Theme toggle (placeholder)
        document.getElementById('theme-toggle').addEventListener('click', () => {
            console.log('Theme toggle clicked');
            // TODO: Implement theme toggle
        });

        // Settings (placeholder)
        document.getElementById('settings-btn').addEventListener('click', () => {
            console.log('Settings clicked');
            // TODO: Implement settings
        });
    }

    // ========================================================================
    // UTILITIES
    // ========================================================================

    formatTime(date) {
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true 
        });
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Wait for DOM to be ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.app = new WebsiteGeneratorApp();
    });
} else {
    window.app = new WebsiteGeneratorApp();
}
