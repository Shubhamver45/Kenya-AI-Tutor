/**
 * Kenya AI Tutor — Professional Client Controller
 * ChatGPT & Claude-style interaction, streaming-feel dynamic responses
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatMessages = document.getElementById("chat-messages");
  const chatScrollArea = document.getElementById("chat-scroll-area");
  const btnSubmit = document.getElementById("btn-submit");
  const btnNewChat = document.getElementById("btn-new-chat");
  const btnClearChat = document.getElementById("btn-clear-chat");
  const historyList = document.getElementById("history-list");
  const gradeSelect = document.getElementById("grade-select");
  const langEnBtn = document.getElementById("lang-en");
  const langSwBtn = document.getElementById("lang-sw");
  const starterCards = document.querySelectorAll(".starter-card");
  const btnToggleSidebar = document.getElementById("btn-toggle-sidebar");
  const sidebar = document.getElementById("sidebar");

  // State
  let activeGrade = gradeSelect ? (parseInt(gradeSelect.value) || 6) : 6;
  let activeLanguage = "en";
  let conversationHistory = [];
  let sessions = [];
  let currentSessionTitle = "";

  // ──────────────────────────────────────────────────────────────────────────
  // 1. Input Box Auto-Resize & Keyboard Handling
  // ──────────────────────────────────────────────────────────────────────────

  function autoResizeTextarea() {
    if (!chatInput) return;
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + "px";
  }

  if (chatInput) {
    chatInput.addEventListener("input", () => {
      autoResizeTextarea();
      if (btnSubmit) {
        if (chatInput.value.trim().length > 0) {
          btnSubmit.classList.add("active");
        } else {
          btnSubmit.classList.remove("active");
        }
      }
    });

    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (chatInput.value.trim()) {
          chatForm.dispatchEvent(new Event("submit"));
        }
      }
    });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 2. Controls & Preferences (Grade & Language)
  // ──────────────────────────────────────────────────────────────────────────

  if (gradeSelect) {
    gradeSelect.addEventListener("change", (e) => {
      activeGrade = parseInt(e.target.value);
    });
  }

  if (langEnBtn) {
    langEnBtn.addEventListener("click", () => {
      activeLanguage = "en";
      langEnBtn.classList.add("active");
      if (langSwBtn) langSwBtn.classList.remove("active");
      if (chatInput) chatInput.placeholder = "Message Kenya AI Tutor...";
    });
  }

  if (langSwBtn) {
    langSwBtn.addEventListener("click", () => {
      activeLanguage = "sw";
      langSwBtn.classList.add("active");
      if (langEnBtn) langEnBtn.classList.remove("active");
      if (chatInput) chatInput.placeholder = "Tuma ujumbe kwa Kenya AI Tutor...";
    });
  }

  if (btnToggleSidebar && sidebar) {
    btnToggleSidebar.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }

  // Starter Prompts Click
  starterCards.forEach(card => {
    card.addEventListener("click", () => {
      const prompt = card.dataset.prompt;
      if (prompt && chatInput) {
        chatInput.value = prompt;
        autoResizeTextarea();
        chatForm.dispatchEvent(new Event("submit"));
      }
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 3. New Chat & Clear Chat Handlers
  // ──────────────────────────────────────────────────────────────────────────

  function startNewChat() {
    conversationHistory = [];
    currentSessionTitle = "";
    chatMessages.innerHTML = `
      <div class="chat-welcome-state" id="chat-welcome-state">
        <div class="welcome-icon">
          <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="48" height="48" rx="14" fill="#2563EB"/>
            <path d="M14 16C14 14.8954 14.8954 14 16 14H21.5C23.433 14 25 15.567 25 17.5V31C25 29.6193 23.8807 28.5 22.5 28.5H16C14.8954 28.5 14 27.6046 14 26.5V16Z" fill="white"/>
            <path d="M34 16C34 14.8954 33.1046 14 32 14H26.5C24.567 14 23 15.567 23 17.5V31C23 29.6193 24.1193 28.5 25.5 28.5H32C33.1046 28.5 34 27.6046 34 26.5V16Z" fill="#93C5FD"/>
          </svg>
        </div>
        <h1 class="welcome-title">How can I help you learn today?</h1>
        <p class="welcome-subtitle">Ask any question across Mathematics, Science & Technology, English, Kiswahili, or Social Studies.</p>

        <div class="starter-prompts-grid">
          <button type="button" class="starter-card" data-prompt="What is a fraction and how do numerators and denominators work?">
            <span class="starter-card-title">What is a fraction?</span>
            <span class="starter-card-desc">Explain numerators and denominators with everyday examples</span>
          </button>
          <button type="button" class="starter-card" data-prompt="Explain the main human internal organs and their functions in Science">
            <span class="starter-card-title">Human Internal Organs</span>
            <span class="starter-card-desc">Learn how the heart, brain, lungs, and stomach work together</span>
          </button>
          <button type="button" class="starter-card" data-prompt="What is the difference between proper nouns, common nouns, and collective nouns in English?">
            <span class="starter-card-title">Proper vs Common Nouns</span>
            <span class="starter-card-desc">Grammar rules and sentence examples for English class</span>
          </button>
          <button type="button" class="starter-card" data-prompt="Eleza muundo wa sentensi na kazi za viungo vya mwili katika Kiswahili">
            <span class="starter-card-title">Mifumo ya Mwili (Kiswahili)</span>
            <span class="starter-card-desc">Maelezo wazi ya viungo vya ndani kwa lugha ya Kiswahili</span>
          </button>
        </div>
      </div>
    `;

    // Re-attach starter listeners
    document.querySelectorAll(".starter-card").forEach(c => {
      c.addEventListener("click", () => {
        const prompt = c.dataset.prompt;
        if (prompt && chatInput) {
          chatInput.value = prompt;
          autoResizeTextarea();
          chatForm.dispatchEvent(new Event("submit"));
        }
      });
    });

    if (chatInput) {
      chatInput.value = "";
      autoResizeTextarea();
      chatInput.focus();
    }
  }

  if (btnNewChat) btnNewChat.addEventListener("click", startNewChat);
  if (btnClearChat) btnClearChat.addEventListener("click", startNewChat);

  // ──────────────────────────────────────────────────────────────────────────
  // 4. Chat Submission Pipeline
  // ──────────────────────────────────────────────────────────────────────────

  if (chatForm) {
    chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const question = chatInput.value.trim();
      if (!question) return;

      // Clean welcome state if present
      const welcome = document.getElementById("chat-welcome-state");
      if (welcome) welcome.remove();

      chatInput.value = "";
      autoResizeTextarea();
      if (btnSubmit) btnSubmit.classList.remove("active");

      // Record session in sidebar history if new
      if (!currentSessionTitle) {
        currentSessionTitle = question.length > 28 ? question.substring(0, 28) + "..." : question;
        addToHistory(currentSessionTitle);
      }

      await executePipeline(question);
    });
  }

  async function executePipeline(question) {
    appendUserMessage(question);

    if (btnSubmit) btnSubmit.disabled = true;
    if (chatInput) chatInput.disabled = true;

    const typingId = appendTypingIndicator();
    scrollToBottom();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question,
          history: conversationHistory,
          grade: activeGrade,
          subject: "General",
        }),
      });

      const data = await res.json();
      removeTypingIndicator(typingId);

      if (!res.ok) {
        throw new Error(data.error || "Execution failed");
      }

      const answer = data.answer;

      conversationHistory.push({ role: "user", content: question });
      conversationHistory.push({ role: "assistant", content: answer });

      appendAssistantMessage(answer);
      scrollToBottom();

    } catch (err) {
      removeTypingIndicator(typingId);
      appendErrorMessage(err.message);
      scrollToBottom();
    } finally {
      if (btnSubmit) btnSubmit.disabled = false;
      if (chatInput) {
        chatInput.disabled = false;
        chatInput.focus();
      }
    }
  }

  function appendUserMessage(text) {
    const turn = document.createElement("div");
    turn.className = "chat-turn student-turn";
    turn.innerHTML = `
      <div class="student-bubble">
        ${escapeHtml(text)}
      </div>
    `;
    chatMessages.appendChild(turn);
  }

  function appendAssistantMessage(answerText) {
    const turn = document.createElement("div");
    turn.className = "chat-turn tutor-turn";
    const msgId = "msg-" + Date.now();

    turn.innerHTML = `
      <div class="tutor-avatar-box">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
      </div>
      <div class="tutor-body-wrap">
        <div class="tutor-text" id="${msgId}">
          ${formatAnswerMarkdown(answerText)}
        </div>
        <div class="tutor-action-row">
          <button type="button" class="btn-copy" onclick="copyResponse('${msgId}', this)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span>Copy</span>
          </button>
        </div>
      </div>
    `;

    chatMessages.appendChild(turn);
  }

  function appendTypingIndicator() {
    const id = "typing-" + Date.now();
    const turn = document.createElement("div");
    turn.className = "chat-turn tutor-turn";
    turn.id = id;
    turn.innerHTML = `
      <div class="tutor-avatar-box">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
      </div>
      <div class="tutor-body-wrap">
        <div style="display: flex; gap: 6px; align-items: center; padding: 0.5rem 0;">
          <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#10B981; animation: pulse 1s infinite;"></span>
          <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#10B981; animation: pulse 1s infinite 0.2s;"></span>
          <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#10B981; animation: pulse 1s infinite 0.4s;"></span>
        </div>
      </div>
    `;
    chatMessages.appendChild(turn);
    return id;
  }

  function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function appendErrorMessage(msg) {
    const turn = document.createElement("div");
    turn.className = "chat-turn tutor-turn";
    turn.innerHTML = `
      <div class="tutor-avatar-box" style="background:#ef4444;">
        <span style="color:white; font-size:14px;">⚠️</span>
      </div>
      <div class="tutor-body-wrap">
        <div class="tutor-text" style="color: #b91c1c;">
          ${escapeHtml(msg)}
        </div>
      </div>
    `;
    chatMessages.appendChild(turn);
  }

  function scrollToBottom() {
    if (chatScrollArea) {
      chatScrollArea.scrollTop = chatScrollArea.scrollHeight;
    }
  }

  function addToHistory(title) {
    if (!historyList) return;
    const item = document.createElement("div");
    item.className = "history-item active";
    item.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
      <span>${escapeHtml(title)}</span>
    `;
    historyList.prepend(item);
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 5. Markdown Parsing
  // ──────────────────────────────────────────────────────────────────────────

  function formatAnswerMarkdown(text) {
    if (!text) return "";

    let formatted = text
      .replace(/\\frac\{(\d+)\}\{(\d+)\}/g, '<span class="fraction-inline"><span class="num">$1</span><span class="den">$2</span></span>')
      .replace(/\b(\d+)\/(\d+)\b/g, '<span class="fraction-inline"><span class="num">$1</span><span class="den">$2</span></span>')
      .replace(/^###\s+(.*)$/gm, '<h4>$1</h4>')
      .replace(/^##\s+(.*)$/gm, '<h3>$1</h3>')
      .replace(/^---\s*$/gm, '<hr />')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/^[*-]\s+(.*)$/gm, '<li>$1</li>');

    formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    const paras = formatted.split(/\n\n+/);
    return paras.map(p => {
      p = p.trim();
      if (!p) return "";
      if (p.startsWith("<ul") || p.startsWith("<div") || p.startsWith("<h") || p.startsWith("<hr")) return p;
      return `<p>${p}</p>`;
    }).join("");
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Global copy response function
  window.copyResponse = function(elId, btn) {
    const el = document.getElementById(elId);
    if (!el) return;
    const text = el.innerText;
    navigator.clipboard.writeText(text).then(() => {
      const originalText = btn.innerHTML;
      btn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <span style="color:#10b981;">Copied!</span>
      `;
      setTimeout(() => {
        btn.innerHTML = originalText;
      }, 1800);
    });
  };
});
