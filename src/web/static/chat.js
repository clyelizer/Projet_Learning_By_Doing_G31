/**
 * Chat Bubble — Assistant Agricole IA
 * Icône 💬 en bas à droite → fenêtre de chat 380×500px
 * Modèle : Groq Llama 3.1 8B
 */
(function () {
    'use strict';

    const toggleBtn = document.getElementById('chat-toggle');
    const windowEl = document.getElementById('chat-window');
    const closeBtn = document.getElementById('chat-close');
    const messagesEl = document.getElementById('chat-messages');
    const inputEl = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send');

    let isOpen = false;
    let isLoading = false;
    let unread = 0;

    // ── Toggle ──────────────────────────────────────────────────
    function open() {
        isOpen = true;
        windowEl.classList.remove('hidden');
        toggleBtn.textContent = '✕';
        unread = 0;
        updateBadge();
        inputEl.focus();
    }

    function close() {
        isOpen = false;
        windowEl.classList.add('hidden');
        toggleBtn.textContent = '💬';
    }

    toggleBtn.addEventListener('click', () => isOpen ? close() : open());
    closeBtn.addEventListener('click', close);

    // ── Badge notification ──────────────────────────────────────
    function updateBadge() {
        const existing = toggleBtn.querySelector('.chat-badge');
        if (existing) existing.remove();
        if (unread > 0 && !isOpen) {
            const badge = document.createElement('span');
            badge.className = 'chat-badge';
            badge.textContent = unread > 9 ? '9+' : unread;
            toggleBtn.appendChild(badge);
        }
    }

    // ── Messages ────────────────────────────────────────────────
    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `chat-msg chat-msg-${sender}`;
        div.innerHTML = `<div class="chat-msg-content">${escapeHTML(text)}</div>`;
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function addTyping() {
        const div = document.createElement('div');
        div.className = 'chat-msg chat-msg-bot';
        div.id = 'typing-indicator';
        div.innerHTML = '<div class="chat-msg-content"><span class="dot">●</span><span class="dot">●</span><span class="dot">●</span></div>';
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function removeTyping() {
        const el = document.getElementById('typing-indicator');
        if (el) el.remove();
    }

    function escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ── Send ────────────────────────────────────────────────────
    async function sendMessage() {
        const text = inputEl.value.trim();
        if (!text || isLoading) return;

        inputEl.value = '';
        addMessage(text, 'user');
        addTyping();
        isLoading = true;

        try {
            const resp = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, language: 'fr' }),
            });
            const data = await resp.json();
            removeTyping();

            if (data.error) {
                addMessage('❌ ' + data.error, 'bot');
            } else {
                addMessage(data.reply, 'bot');
            }
        } catch (e) {
            removeTyping();
            addMessage('❌ Erreur de connexion.', 'bot');
        }

        isLoading = false;

        if (!isOpen) {
            unread++;
            updateBadge();
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keydown', e => {
        if (e.key === 'Enter') sendMessage();
    });

    // ── Message d'accueil ───────────────────────────────────────
    addMessage(
        'Bonjour ! Je suis votre assistant agricole. Posez-moi vos questions sur les résultats d\'analyse du sol, les cultures recommandées ou les pratiques agricoles adaptées à votre terrain.',
        'bot'
    );
})();

// ── Global: replay TTS ───────────────────────────────────────────
function replayTTS(text, lang) {
    fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language: lang || 'fr', engine: 'auto' }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) console.error('TTS:', data.error);
    })
    .catch(e => console.error('TTS fetch failed:', e));
}
