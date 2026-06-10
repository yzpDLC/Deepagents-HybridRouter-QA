// ========================================
// 企业内部知识库问答系统 — 前端逻辑
// ========================================

let isLoading = false;
let currentStreamingMessage = null;
let streamingContent = '';
let abortController = null;
/** 会话标识，同一对话窗口共用同一个值，新对话时重新生成 */
let currentSessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);

const textarea = document.getElementById('message-input');
const conversation = document.getElementById('conversation');
const sendBtn = document.getElementById('btn-send');
const stopBtn = document.getElementById('btn-stop');
const generateVideoBtn = document.getElementById('btn-generate-video');
const sidebar = document.getElementById('sidebar');
const agentDot = document.querySelector('#status-agent .status-dot');
const modelDot = document.querySelector('#status-model .status-dot');
const agentBadge = document.querySelector('#status-agent .status-badge');
const modelBadge = document.querySelector('#status-model .status-badge');

// ========================================
// Init
// ========================================

function init() {
    if (typeof marked !== 'undefined') {
        marked.setOptions({ breaks: true, gfm: true });
    }
    if (textarea) {
        textarea.addEventListener('input', autoResize);
        textarea.addEventListener('keydown', handleKeyPress);
        textarea.focus();
    }
    checkHealth();
    // 每30秒检查一次健康状态
    setInterval(checkHealth, 30000);
}

function autoResize() {
    this.style.height = 'auto';
    this.style.height = Math.min(120, this.scrollHeight) + 'px';
}

// ========================================
// Health Check
// ========================================

async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();

        if (agentDot) {
            agentDot.classList.toggle('online', data.agent_loaded);
            agentDot.classList.toggle('offline', !data.agent_loaded);
        }
        if (agentBadge) {
            agentBadge.textContent = data.agent_loaded ? '在线' : '离线';
            agentBadge.classList.toggle('online', data.agent_loaded);
            agentBadge.classList.toggle('offline', !data.agent_loaded);
        }
        if (modelDot) {
            modelDot.classList.toggle('online', data.model_loaded);
            modelDot.classList.toggle('offline', !data.model_loaded);
        }
        if (modelBadge) {
            modelBadge.textContent = data.model_loaded ? '在线' : '离线';
            modelBadge.classList.toggle('online', data.model_loaded);
            modelBadge.classList.toggle('offline', !data.model_loaded);
        }
    } catch {
        if (agentDot) {
            agentDot.classList.remove('online');
            agentDot.classList.add('offline');
        }
        if (agentBadge) {
            agentBadge.textContent = '离线';
            agentBadge.classList.remove('online');
            agentBadge.classList.add('offline');
        }
        if (modelDot) {
            modelDot.classList.remove('online');
            modelDot.classList.add('offline');
        }
        if (modelBadge) {
            modelBadge.textContent = '离线';
            modelBadge.classList.remove('online');
            modelBadge.classList.add('offline');
        }
    }
}

// ========================================
// Sidebar
// ========================================

function toggleSidebar() {
    if (sidebar) sidebar.classList.toggle('collapsed');
}

// ========================================
// Send Message
// ========================================

async function sendMessage() {
    const message = textarea.value.trim();
    if (!message || isLoading) return;

    hideWelcome();
    addMessage('user', message);
    resetInput();
    setLoading(true);

    abortController = new AbortController();
    streamingContent = '';
    currentStreamingMessage = createStreamingMessage();

    try {
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, session_id: currentSessionId }),
            signal: abortController.signal,
        });

        if (!response.ok) {
            throw new Error(`请求失败 (${response.status})`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        let streamDone = false;
        while (!streamDone) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || trimmed.startsWith(':')) continue;

                if (trimmed.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(trimmed.slice(6));

                        if (data.error) throw new Error(data.error);
                        if (data.done) { streamDone = true; break; }

                        if (data.content) {
                            streamingContent += data.content;
                            updateStreamingMessage(currentStreamingMessage, streamingContent);
                        }
                    } catch (e) {
                        if (e instanceof SyntaxError) continue;
                        throw e;
                    }
                }
            }
        }

        setLoading(false);

        const finalizedMsg = currentStreamingMessage;
        const finalizedContent = streamingContent;

        if (!finalizedContent) {
            updateStreamingMessage(finalizedMsg, '收到空响应，请稍后重试');
        }
        requestAnimationFrame(() => {
            finalizeMessage(finalizedMsg, finalizedContent);
        });

    } catch (error) {
        setLoading(false);

        const finalizedMsg = currentStreamingMessage;
        const finalizedContent = streamingContent;

        if (error.name === 'AbortError') {
            updateStreamingMessage(finalizedMsg, finalizedContent || '已停止生成');
        } else {
            console.error('Stream error:', error);
            updateStreamingMessage(finalizedMsg, error.message || '连接失败，请检查服务是否启动');
        }
        requestAnimationFrame(() => {
            finalizeMessage(finalizedMsg, finalizedContent);
        });
    } finally {
        currentStreamingMessage = null;
        abortController = null;
    }
}

function resetInput() {
    textarea.value = '';
    textarea.style.height = 'auto';
    textarea.focus();
}

function sendHint(text) {
    if (isLoading) return;
    textarea.value = text;
    sendMessage();
}

async function generateVideo() {
    if (isLoading) return;

    const messages = collectChatHistory();
    if (messages.length === 0) {
        showToast('对话历史为空，无法生成视频');
        return;
    }

    hideWelcome();
    setLoading(true);

    abortController = new AbortController();
    streamingContent = '';
    currentStreamingMessage = createStreamingMessage();

    try {
        const response = await fetch('/api/chat/generate-video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages, session_id: currentSessionId }),
            signal: abortController.signal,
        });

        if (!response.ok) {
            throw new Error(`请求失败 (${response.status})`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        let streamDone = false;
        while (!streamDone) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || trimmed.startsWith(':')) continue;

                if (trimmed.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(trimmed.slice(6));

                        if (data.error) throw new Error(data.error);
                        if (data.done) { streamDone = true; break; }

                        if (data.content) {
                            streamingContent += data.content;
                            updateStreamingMessage(currentStreamingMessage, streamingContent);
                        }
                    } catch (e) {
                        if (e instanceof SyntaxError) continue;
                        throw e;
                    }
                }
            }
        }

        setLoading(false);

        const finalizedMsg = currentStreamingMessage;
        const finalizedContent = streamingContent;

        if (!finalizedContent) {
            updateStreamingMessage(finalizedMsg, '收到空响应，请稍后重试');
        }
        requestAnimationFrame(() => {
            finalizeMessage(finalizedMsg, finalizedContent);
        });

    } catch (error) {
        setLoading(false);

        const finalizedMsg = currentStreamingMessage;
        const finalizedContent = streamingContent;

        if (error.name === 'AbortError') {
            updateStreamingMessage(finalizedMsg, finalizedContent || '已停止生成');
        } else {
            console.error('Video generation error:', error);
            updateStreamingMessage(finalizedMsg, error.message || '生成视频失败，请检查服务是否启动');
        }
        requestAnimationFrame(() => {
            finalizeMessage(finalizedMsg, finalizedContent);
        });
    } finally {
        currentStreamingMessage = null;
        abortController = null;
    }
}

function collectChatHistory() {
    const blocks = conversation.querySelectorAll('.message-block');
    const messages = [];
    blocks.forEach(block => {
        const isUser = block.classList.contains('user');
        const bubble = block.querySelector('.bubble');
        if (!bubble) return;
        const content = bubble._rawText || bubble.textContent || '';
        if (!content.trim()) return;
        messages.push({
            role: isUser ? 'user' : 'assistant',
            content: content,
        });
    });
    return messages;
}

function stopGeneration() {
    if (!abortController || !isLoading) return;
    fetch('/api/chat/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: currentSessionId }),
    }).catch(() => {});
    abortController.abort();
}

// ========================================
// Loading State
// ========================================

function setLoading(loading) {
    isLoading = loading;
    if (sendBtn) sendBtn.disabled = loading;
    if (stopBtn) stopBtn.style.display = loading ? 'flex' : 'none';
    if (generateVideoBtn) generateVideoBtn.disabled = loading;
}

// ========================================
// Welcome Screen
// ========================================

function hideWelcome() {
    const el = document.getElementById('welcome-screen');
    if (el) el.classList.add('hidden');
}

// ========================================
// Markdown (简化版)
// ========================================

function renderMarkdown(text) {
    if (!text) return '';

    if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
        try {
            return marked.parse(text);
        } catch (e) {
            console.error('marked parse error:', e);
        }
    }

    // 降级方案：简单的 HTML 转义和换行
    return escapeHtml(text).replace(/\n/g, '<br>');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========================================
// Messages
// ========================================

function createMessageBlock(role, content, isStreaming = false) {
    const block = document.createElement('div');
    block.className = `message-block ${role}`;

    const avatar = document.createElement('div');
    avatar.className = `avatar ${role}`;
    avatar.textContent = role === 'user' ? '我' : 'AI';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    if (isStreaming) {
        bubble.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
    } else if (role === 'assistant') {
        bubble.innerHTML = renderMarkdown(content);
        bubble._rawText = content;
    } else {
        bubble.textContent = content;
    }

    block.appendChild(avatar);
    block.appendChild(bubble);

    return block;
}

function addMessage(role, content) {
    const block = createMessageBlock(role, content, false);
    conversation.appendChild(block);

    if (role === 'assistant' && content) {
        addCopyButton(block.querySelector('.bubble'), content);
    }

    addTimestamp(block);
    if (generateVideoBtn) generateVideoBtn.style.display = 'flex';
    scrollToBottom();
}

function createStreamingMessage() {
    const block = createMessageBlock('assistant', '', true);
    conversation.appendChild(block);
    scrollToBottom();
    return block;
}

function updateStreamingMessage(block, content) {
    if (!block) return;
    const bubble = block.querySelector('.bubble');
    if (bubble) {
        bubble.innerHTML = renderMarkdown(content || ' ');
        bubble._rawText = content;
        scrollToBottom();
    }
}

function finalizeMessage(block, content) {
    if (!block) return;
    const bubble = block.querySelector('.bubble');
    if (bubble && content) {
        bubble.innerHTML = renderMarkdown(content);
        addCopyButton(bubble, content);
    }
    addTimestamp(block);
}

function addTimestamp(block) {
    if (block.querySelector('.message-time')) return;
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    block.appendChild(time);
}

// ========================================
// Copy Button
// ========================================

function addCopyButton(bubble, content) {
    if (bubble.querySelector('.btn-copy')) return;

    const btn = document.createElement('button');
    btn.className = 'btn-copy';
    btn.title = '复制';
    btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="4" y="4" width="8" height="8" rx="1" stroke="currentColor" stroke-width="1.2"/><path d="M2 10V3a1 1 0 011-1h7" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>';

    btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        try {
            await navigator.clipboard.writeText(content);
            btn.classList.add('copied');
            showToast('已复制到剪贴板');
            setTimeout(() => btn.classList.remove('copied'), 1500);
        } catch {
            showToast('复制失败');
        }
    });

    bubble.appendChild(btn);
}

// ========================================
// Clear Chat
// ========================================

function clearChat() {
    conversation.replaceChildren();

    const welcome = createWelcomeScreen();
    conversation.appendChild(welcome);

    // 重置状态
    if (abortController) {
        abortController.abort();
    }
    isLoading = false;
    streamingContent = '';
    currentStreamingMessage = null;
    abortController = null;
    // 新对话，重新生成 session_id
    currentSessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);

    if (sendBtn) sendBtn.disabled = false;
    if (stopBtn) stopBtn.style.display = 'none';
    if (generateVideoBtn) generateVideoBtn.style.display = 'none';

    if (textarea) textarea.focus();
}

function createWelcomeScreen() {
    const welcome = document.createElement('div');
    welcome.className = 'welcome-screen';
    welcome.id = 'welcome-screen';
    welcome.innerHTML = `
        <div class="welcome-brand">
            <div class="welcome-brand-ring">
                <svg width="36" height="36" viewBox="0 0 48 48" fill="none" stroke="#3b82f6" stroke-width="2">
                    <circle cx="24" cy="24" r="19"/>
                    <path d="M24 11v14l8 4" stroke-linecap="round"/>
                    <circle cx="24" cy="24" r="3" fill="#3b82f6"/>
                </svg>
            </div>
        </div>
        <h2>企业内部知识库问答系统</h2>
        <p>基于知识图谱与网络实时搜索，为您提供专业的企业知识解答</p>
        <div class="welcome-hints">
            <button class="hint-chip" onclick="sendHint('公司的请假流程是什么')">公司的请假流程是什么</button>
            <button class="hint-chip" onclick="sendHint('网络安全制度有哪些要求')">网络安全制度有哪些要求</button>
            <button class="hint-chip" onclick="sendHint('项目管理规范包含哪些内容')">项目管理规范包含哪些内容</button>
            <button class="hint-chip" onclick="sendHint('公司的保密制度是什么')">公司的保密制度是什么</button>
        </div>
    `;
    return welcome;
}

// ========================================
// Toast
// ========================================

function showToast(message) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 2000);
}

// ========================================
// Keyboard
// ========================================

function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        if (!isLoading) sendMessage();
    }
}

// ========================================
// Scroll
// ========================================

function scrollToBottom() {
    if (conversation) {
        conversation.scrollTop = conversation.scrollHeight;
    }
}

// ========================================
// Exports
// ========================================

window.sendMessage = sendMessage;
window.sendHint = sendHint;
window.clearChat = clearChat;
window.stopGeneration = stopGeneration;
window.generateVideo = generateVideo;
window.toggleSidebar = toggleSidebar;

// 启动应用
document.addEventListener('DOMContentLoaded', init);