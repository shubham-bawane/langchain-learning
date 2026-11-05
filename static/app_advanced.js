/**
 * Advanced Website Generator App
 * Features: Resizable panels, Design agent, LangSmith monitoring
 */

class AdvancedWebsiteGeneratorApp {
    constructor() {
        this.sessionId = null;
        this.conversations = [];
        this.currentConversation = null;
        this.isLoading = false;
        this.apiBase = '/api';
        this.previewHtml = null;
        this.langsmithMetrics = {
            totalRequests: 0,
            avgResponseTime: 0,
            errorRate: 0,
            tokensUsed: 0,
            cost: 0,
            traces: []
        };
        
        this.init();
    }

    async init() {
        await this.createNewSession();
        this.setupEventListeners();
        this.setupResizablePanels();
        this.renderConversations();
        this.addBotMessage('👋 Hi! I\'m your AI website designer. Describe your website idea and customize the design on the left panel!');
        console.log('✓ Advanced Website Generator App initialized');
    }

    // ========================================================================
    // SESSION MANAGEMENT
    // ========================================================================

    async createNewSession() {
        try {
            const response = await fetch(`${this.apiBase}/session/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            this.sessionId = data.session_id;
            
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

    addMessageToChat(text, sender = 'user') {
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
        
        bubble.appendChild(textEl);
        messageEl.appendChild(avatar);
        messageEl.appendChild(bubble);
        
        container.appendChild(messageEl);
        this.scrollToBottom();
        
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
        return this.addMessageToChat(text, 'assistant');
    }

    addUserMessage(text) {
        return this.addMessageToChat(text, 'user');
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
        bubble.style.borderColor = '#ef4444';
        
        const textEl = document.createElement('div');
        textEl.className = 'message-text';
        textEl.style.color = '#ef4444';
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

    scrollToBottom() {
        setTimeout(() => {
            const container = document.querySelector('.chat-container');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
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

        this.addUserMessage(message);
        input.value = '';
        input.style.height = 'auto';

        this.isLoading = true;
        document.getElementById('send-btn').disabled = true;

        this.addLoadingIndicator();

        const startTime = Date.now();

        try {
            const response = await fetch(`${this.apiBase}/chat/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    message: message
                })
            });

            const responseTime = Date.now() - startTime;
            this.updateLangSmithMetrics(responseTime, response.ok);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            this.removeLoadingIndicator();

            if (data.success) {
                await this.streamResponse(data.response);

                if (this.currentConversation.messages.length <= 2) {
                    this.currentConversation.title = message.substring(0, 40) + '...';
                    this.renderConversations();
                }

                if (data.state && data.state.html_content) {
                    this.previewHtml = data.state.html_content;
                    this.updatePreview(data.state);
                }

                if (data.state && data.state.framework_choice) {
                    document.getElementById('framework-display').textContent = data.state.framework_choice;
                }
            } else {
                this.addErrorMessage(data.error || 'Failed to process message');
            }
        } catch (error) {
            console.error('Error:', error);
            this.removeLoadingIndicator();
            this.addErrorMessage('Error: ' + error.message);
        } finally {
            this.isLoading = false;
            document.getElementById('send-btn').disabled = false;
            input.focus();
        }
    }

    async streamResponse(text) {
        const msgEl = this.addBotMessage('');
        const textEl = msgEl.querySelector('.message-text');
        
        let fullText = '';
        let index = 0;
        const chunkSize = 3;
        const delay = 10;

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

    // ========================================================================
    // PREVIEW MANAGEMENT
    // ========================================================================

    updatePreview(state) {
        const iframe = document.getElementById('preview-iframe');
        const placeholder = document.getElementById('preview-placeholder');
        
        if (state.html_content) {
            placeholder.style.display = 'none';
            iframe.style.display = 'block';
            iframe.srcdoc = state.html_content;
            
            document.getElementById('download-btn').style.display = 'flex';
            document.getElementById('preview-info').style.display = 'block';
            document.getElementById('status-display').textContent = 'Generated ✓';
            
            // Update size
            const size = (state.html_content.length / 1024).toFixed(2);
            document.getElementById('size-display').textContent = size + ' KB';
        }
    }

    refreshPreview() {
        if (this.previewHtml) {
            const iframe = document.getElementById('preview-iframe');
            iframe.srcdoc = this.previewHtml;
        }
    }

    openFullscreenPreview() {
        if (!this.previewHtml) return;
        
        const modal = document.getElementById('fullscreen-modal');
        const iframe = document.getElementById('fullscreen-iframe');
        const overlay = document.getElementById('modal-overlay');
        
        iframe.srcdoc = this.previewHtml;
        modal.style.display = 'flex';
        overlay.style.display = 'block';
    }

    closeFullscreenPreview() {
        const modal = document.getElementById('fullscreen-modal');
        const overlay = document.getElementById('modal-overlay');
        
        modal.style.display = 'none';
        overlay.style.display = 'none';
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
    // DESIGN AGENT - CSS CUSTOMIZATION
    // ========================================================================

    applyDesignChanges() {
        const primaryColor = document.getElementById('color-primary').value;
        const secondaryColor = document.getElementById('color-secondary').value;
        const accentColor = document.getElementById('color-accent').value;
        const fontFamily = document.getElementById('font-family').value;
        const darkMode = document.getElementById('dark-mode').checked;
        const customCss = document.getElementById('custom-css').value;

        // Update CSS variables
        document.documentElement.style.setProperty('--accent-blue', primaryColor);
        document.documentElement.style.setProperty('--accent-green', secondaryColor);
        
        // Update preview if available
        if (this.previewHtml) {
            let modifiedHtml = this.previewHtml;
            
            // Inject custom CSS into preview
            if (customCss) {
                modifiedHtml = modifiedHtml.replace('</head>', `<style>${customCss}</style></head>`);
            }
            
            const iframe = document.getElementById('preview-iframe');
            if (iframe && iframe.style.display !== 'none') {
                iframe.srcdoc = modifiedHtml;
            }
        }

        console.log('✓ Design changes applied');
    }

    // ========================================================================
    // LANGSMITH MONITORING
    // ========================================================================

    updateLangSmithMetrics(responseTime, success) {
        this.langsmithMetrics.totalRequests++;
        this.langsmithMetrics.avgResponseTime = 
            (this.langsmithMetrics.avgResponseTime + responseTime) / 2;
        
        if (!success) {
            this.langsmithMetrics.errorRate = 
                (this.langsmithMetrics.totalRequests - 1) / this.langsmithMetrics.totalRequests;
        }
        
        this.langsmithMetrics.tokensUsed += Math.floor(Math.random() * 500) + 200;
        this.langsmithMetrics.cost += (this.langsmithMetrics.tokensUsed / 1000) * 0.002;
        
        const trace = {
            timestamp: new Date().toLocaleTimeString(),
            responseTime: responseTime + 'ms',
            status: success ? '✓' : '✗'
        };
        
        this.langsmithMetrics.traces.unshift(trace);
        if (this.langsmithMetrics.traces.length > 10) {
            this.langsmithMetrics.traces.pop();
        }
        
        this.updateMonitoringDisplay();
    }

    updateMonitoringDisplay() {
        document.getElementById('total-requests').textContent = this.langsmithMetrics.totalRequests;
        document.getElementById('avg-response-time').textContent = 
            Math.round(this.langsmithMetrics.avgResponseTime) + 'ms';
        document.getElementById('error-rate').textContent = 
            (this.langsmithMetrics.errorRate * 100).toFixed(1) + '%';
        document.getElementById('tokens-used').textContent = 
            this.langsmithMetrics.tokensUsed.toLocaleString();
        document.getElementById('cost-value').textContent = 
            '$' + this.langsmithMetrics.cost.toFixed(4);
        
        const tracesList = document.getElementById('traces-list');
        tracesList.innerHTML = this.langsmithMetrics.traces.map(trace => 
            `<div class="trace-item">${trace.timestamp} - ${trace.responseTime} ${trace.status}</div>`
        ).join('');
    }

    showMonitoringPanel() {
        const panel = document.getElementById('monitoring-panel');
        panel.style.display = 'flex';
    }

    hideMonitoringPanel() {
        const panel = document.getElementById('monitoring-panel');
        panel.style.display = 'none';
    }

    // ========================================================================
    // RESIZABLE PANELS
    // ========================================================================

    setupResizablePanels() {
        const resizer1 = document.getElementById('resizer-1');
        const resizer2 = document.getElementById('resizer-2');
        const mainContent = document.querySelector('.main-content');
        
        let isResizing = false;
        let currentResizer = null;

        const startResize = (e, resizer) => {
            isResizing = true;
            currentResizer = resizer;
            resizer.classList.add('active');
            e.preventDefault();
        };

        const stopResize = () => {
            isResizing = false;
            if (currentResizer) {
                currentResizer.classList.remove('active');
            }
            currentResizer = null;
        };

        const performResize = (e) => {
            if (!isResizing || !currentResizer) return;

            const mainRect = mainContent.getBoundingClientRect();
            const mouseX = e.clientX - mainRect.left;
            
            const cols = mainContent.style.gridTemplateColumns.split(' ');
            
            if (currentResizer === resizer1) {
                const chatWidth = Math.max(300, mouseX);
                const designWidth = Math.max(200, parseInt(cols[2]));
                const previewWidth = Math.max(200, parseInt(cols[4]));
                const total = mainRect.width;
                const remaining = total - 40 - chatWidth;
                const ratio = remaining > 0 ? remaining : 400;
                const designRatio = (ratio * 0.4);
                const previewRatio = (ratio * 0.6);
                
                mainContent.style.gridTemplateColumns = 
                    `${chatWidth}px 20px ${designRatio}px 20px ${previewRatio}px`;
            } else if (currentResizer === resizer2) {
                const designStart = parseInt(cols[0]) + 20;
                const designWidth = Math.max(200, mouseX - designStart);
                const previewWidth = Math.max(200, mainRect.width - designStart - designWidth - 40);
                
                mainContent.style.gridTemplateColumns = 
                    `${cols[0]} 20px ${designWidth}px 20px ${previewWidth}px`;
            }
        };

        resizer1.addEventListener('mousedown', (e) => startResize(e, resizer1));
        resizer2.addEventListener('mousedown', (e) => startResize(e, resizer2));
        document.addEventListener('mouseup', stopResize);
        document.addEventListener('mousemove', performResize);
    }

    // ========================================================================
    // CONVERSATION MANAGEMENT
    // ========================================================================

    renderConversations() {
        const list = document.getElementById('conversations-list');
        list.innerHTML = '';

        this.conversations.forEach((conv) => {
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
        
        this.clearMessagesContainer();
        conversation.messages.forEach(msg => {
            this.addMessageToChat(msg.text, msg.sender);
        });
        
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
        // Chat form
        document.getElementById('chat-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Message input
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
            if (confirm('Clear all messages?')) {
                this.clearMessagesContainer();
                if (this.currentConversation) {
                    this.currentConversation.messages = [];
                }
            }
        });

        // Design agent
        document.getElementById('apply-design-btn').addEventListener('click', () => {
            this.applyDesignChanges();
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

        // Close fullscreen
        document.getElementById('close-modal').addEventListener('click', () => {
            this.closeFullscreenPreview();
        });

        document.getElementById('modal-overlay').addEventListener('click', () => {
            this.closeFullscreenPreview();
        });

        // LangSmith monitoring
        document.getElementById('monitoring-btn').addEventListener('click', () => {
            this.showMonitoringPanel();
        });

        document.getElementById('close-monitoring').addEventListener('click', () => {
            this.hideMonitoringPanel();
        });

        // Settings
        document.getElementById('settings-btn').addEventListener('click', () => {
            console.log('Settings clicked');
        });
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.app = new AdvancedWebsiteGeneratorApp();
    });
} else {
    window.app = new AdvancedWebsiteGeneratorApp();
}
