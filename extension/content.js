(function () {
  "use strict";

  const BACKEND    = "http://127.0.0.1:8000";
  const STATES     = ["sleep", "observe", "wave", "happy"];
  const ASSET_PATH = chrome.runtime.getURL("assets/");

  const SVG_FILES = {
    sleep:   "kiro-sleep.svg",
    observe: "kiro-observe.svg",
    wave:    "kiro-wave.svg",
    happy:   "kiro-happy.svg",
  };

  const svgCache = {};

  const SITE_SELECTORS = [
    { name: "chatgpt", composer: '[data-composer-surface="true"]' },
    { name: "claude",  composer: 'div[contenteditable="true"]' },
    { name: "gemini",  composer: "rich-textarea" },
    { name: "generic", composer: 'textarea[placeholder*="message" i]' },
  ];

  function findComposer() {
    for (const s of SITE_SELECTORS) {
      const el = document.querySelector(s.composer);
      if (el) return el;
    }
    return null;
  }

  function ensureAnchor(composerEl) {
    if (!composerEl) return null;
    if (getComputedStyle(composerEl).position === "static") {
      composerEl.classList.add("kiro-anchor-injected");
    }
    composerEl.style.overflow = "visible";
    composerEl.classList.add("kiro-anchor");
    return composerEl;
  }

  async function getSvgMarkup(state) {
    if (svgCache[state]) return svgCache[state];
    const res  = await fetch(ASSET_PATH + SVG_FILES[state]);
    const text = await res.text();
    svgCache[state] = text;
    return text;
  }

  async function classifyPrompt(prompt) {
    const res = await fetch(`${BACKEND}/classify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    return res.json();
  }

  async function fetchQuestions(prompt) {
    const res = await fetch(`${BACKEND}/questioner`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    return res.json();
  }

  async function streamRewrite(prompt, answers, onChunk, onDone, onError) {
    const res = await fetch(`${BACKEND}/rewriter`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, answers }),
    });

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        try {
          const payload = JSON.parse(line.slice(5).trim());
          if (payload.error) { onError(payload.error); return; }
          if (payload.done)  { onDone(); return; }
          if (payload.chunk) onChunk(payload.chunk);
        } catch (_) {}
      }
    }
  }

  // ── Robot controller ──────────────────────────────────────────────────────
  class kiroRobot {
    constructor(anchorEl) {
      this.anchorEl      = anchorEl;
      this.container     = document.createElement("div");
      this.container.className = "kiro-robot";
      this.bubble        = null;
      this.card          = null;
      this.currentState  = null;
      this.currentPrompt = "";
      this._blockNextClassify = false;

      anchorEl.appendChild(this.container);

      // ── Reposition triggers ────────────────────────────────────────────
      // Composer height changes (multi-line prompt growing/shrinking)
      const composer = findComposer();
      if (composer) {
        const resizeObserver = new ResizeObserver(() => this.positionCard());
        resizeObserver.observe(composer);
        this._resizeObserver = resizeObserver;
      }

      // Window resize / zoom changes
      window.addEventListener("resize", () => this.positionCard());

      this.setState("sleep");
    }

    async setState(state, force = false) {
      if (!STATES.includes(state)) return;
      if (state === this.currentState && !force) return;
      this.currentState = state;

      const markup = await getSvgMarkup(state);
      this.container.innerHTML = markup;
      this.container.className = `kiro-robot kiro-robot--${state}`;
      this._renderBubble(state);
    }

    _renderBubble(state) {
      if (this.bubble) { this.bubble.remove(); this.bubble = null; }
      if (state !== "wave") return;

      this.bubble = document.createElement("div");
      this.bubble.className = "kiro-bubble";
      this.bubble.textContent = "Improve this prompt?";
      this.bubble.addEventListener("click", (e) => {
        e.stopPropagation();
        this.bubble.remove();
        this.bubble = null;
        this._openQuestionCard();
      });
      this.container.appendChild(this.bubble);
    }

    // ── Card shell (cross button lives outside innerHTML-managed area) ─────
    _buildCardShell() {
      this._removeCard();

      const card = document.createElement("div");
      card.className = "kiro-card";

      const closeBtn = document.createElement("button");
      closeBtn.type      = "button";
      closeBtn.className = "kiro-card-close";
      closeBtn.textContent = "✕";
      closeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        this._removeCard();
        this.setState("sleep");
      });
      card.appendChild(closeBtn);

      const content = document.createElement("div");
      content.id = "kiro-content";
      card.appendChild(content);

      document.body.appendChild(card);
      this.card = card;
      this.positionCard();
      return content;
    }

    _getContent() {
      return this.card ? this.card.querySelector("#kiro-content") : null;
    }

    // ── Question card ───────────────────────────────────────────────────────
    async _openQuestionCard() {
      const content = this._buildCardShell();
      content.innerHTML = `
        <div class="kiro-card-header">Loading questions...</div>
        <div class="kiro-loading-dots">
          <span></span><span></span><span></span>
        </div>`;
      
      requestAnimationFrame(() => this.positionCard());

      let data;
      try {
        data = await fetchQuestions(this.currentPrompt);
      } catch (err) {
        console.error("[kiro] questioner error:", err);
        this._removeCard();
        return;
      }

      const questions = data.questions || [];
      if (!questions.length) { this._removeCard(); return; }

      this._renderQuestionCard(questions);
    }

    _renderQuestionCard(questions) {
      let currentIndex = 0;
      const collected  = [];

      const renderQuestion = (idx) => {
        const content = this._getContent();
        if (!content) return;

        const q      = questions[idx];
        const total  = questions.length;
        const isLast = idx === total - 1;

        content.innerHTML = `
          <div class="kiro-card-header">Question ${idx + 1} of ${total}</div>
          <div class="kiro-question">${q.text}</div>
          <div class="kiro-options">
            ${q.options.map(opt => `
              <button
                type="button"
                data-letter="${opt.letter}"
                data-text="${opt.text.replace(/"/g, "&quot;")}"
              >
                <span class="kiro-opt-letter">${opt.letter}</span>
                <span class="kiro-opt-text">${opt.text}</span>
              </button>
            `).join("")}
          </div>
          <button type="button" class="kiro-next" disabled>
            ${isLast ? "Submit" : "Next →"}
          </button>`;

        // Reposition — question text length varies, card height changes
        requestAnimationFrame(() => this.positionCard());

        let selectedLetter = null;
        let selectedText   = null;

        content.querySelectorAll(".kiro-options button").forEach(btn => {
          btn.addEventListener("click", () => {
            content.querySelectorAll(".kiro-options button")
                   .forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
            selectedLetter = btn.dataset.letter;
            selectedText   = btn.dataset.text;
            content.querySelector(".kiro-next").disabled = false;
          });
        });

        content.querySelector(".kiro-next").addEventListener("click", () => {
          if (!selectedLetter) return;
          collected.push({
            id:            q.id,
            text:          q.text,
            chosen_letter: selectedLetter,
            chosen_text:   selectedText,
          });

          if (!isLast) {
            currentIndex++;
            renderQuestion(currentIndex);
          } else {
            this._startStreaming(collected);
          }
        });
      };

      renderQuestion(0);
    }

    // ── Streaming rewrite ───────────────────────────────────────────────────
    _startStreaming(answers) {
      const content = this._getContent();
      if (!content) return;

      content.innerHTML = `
        <div class="kiro-stream-header">✦ Improving your prompt</div>
        <div class="kiro-stream-text"></div>`;

      this.card.classList.add("kiro-card--streaming");
      requestAnimationFrame(() => this.positionCard());

      const textEl   = content.querySelector(".kiro-stream-text");
      let   fullText = "";

      streamRewrite(
        this.currentPrompt,
        answers,
        (chunk) => {
          fullText += chunk;
          textEl.textContent = fullText;
          textEl.scrollTop   = textEl.scrollHeight;

          this.positionCard();
        },
        () => {
          const useBtn = document.createElement("button");
          useBtn.type      = "button";
          useBtn.className = "kiro-use-btn";
          useBtn.textContent = "Use this prompt ↗";
          useBtn.addEventListener("click", () => {
            this._blockNextClassify = true;
            this._pasteIntoInput(fullText);
            this._removeCard();
            this.setState("happy");
            setTimeout(() => this.setState("sleep"), 2000);
          });
          content.appendChild(useBtn);
          requestAnimationFrame(() => this.positionCard());
        },
        (err) => {
          console.error("[kiro] rewriter error:", err);
          textEl.textContent = "Something went wrong. Please try again.";
          requestAnimationFrame(() => this.positionCard());
        }
      );
    }

    _pasteIntoInput(text) {
      const composerEl = findComposer();
      if (!composerEl) return;

      const editableEl =
        composerEl.querySelector('[contenteditable="true"]') ||
        composerEl.querySelector("textarea") ||
        composerEl;

      editableEl.focus();

      if (editableEl.isContentEditable) {
        editableEl.innerText = "";
        document.execCommand("insertText", false, text);
      } else {
        const setter = Object.getOwnPropertyDescriptor(
          window.HTMLTextAreaElement.prototype, "value"
        ).set;
        setter.call(editableEl, text);
        editableEl.dispatchEvent(new Event("input", { bubbles: true }));
      }
    }

    // ── Core positioning logic ──────────────────────────────────────────────
    // Places the card directly above the robot, clamped to stay fully
    // within the viewport both horizontally and vertically. Recalculated
    // on every meaningful content/size change (see call sites above).
    positionCard() {
      if (!this.card) return;

      const robotRect    = this.container.getBoundingClientRect();
      const composer      = findComposer();
      const composerRect  = composer ? composer.getBoundingClientRect() : null;

      const edge = 16;  // min distance from any viewport edge
      const gap  = 12;  // gap between card and robot/composer

      // Reset to natural size first so offsetWidth/offsetHeight below
      // reflect the CURRENT content, not a stale cached size.
      this.card.style.position  = "fixed";
      this.card.style.left      = "0px";
      this.card.style.top       = "0px";
      this.card.style.right     = "auto";
      this.card.style.bottom    = "auto";
      this.card.style.maxHeight = `${window.innerHeight - edge * 2}px`;
      this.card.style.overflowY = "auto";

      const cardWidth  = this.card.offsetWidth  || 300;
      const cardHeight = this.card.offsetHeight || 200;

      // Horizontal: center under robot, clamp to viewport
      let left = robotRect.left + robotRect.width / 2 - cardWidth / 2;
      left = Math.max(edge, Math.min(left, window.innerWidth - cardWidth - edge));

      // Vertical: prefer directly above the robot
      let top = robotRect.top - cardHeight - gap;

      // If card would go above the viewport top, clamp it down
      top = Math.max(edge, top);

      // If composer is tall (long prompt) and card would overlap it,
      // push card up just above the composer instead
      if (composerRect && top + cardHeight > composerRect.top - gap) {
        top = Math.max(edge, composerRect.top - cardHeight - gap);
      }

      // Final safety: if card is still taller than available space
      // (composer took up most of the screen), cap its height so the
      // Submit/Use button never gets clipped off-screen
      const availableHeight = window.innerHeight - edge * 2;
      if (cardHeight > availableHeight) {
        this.card.style.maxHeight = `${availableHeight}px`;
        top = edge;
      }

      this.card.style.left   = `${left}px`;
      this.card.style.top    = `${top}px`;
      this.card.style.zIndex = "999999";
    }

    _removeCard() {
      if (this.card) {
        this.card.remove();
        this.card = null;
      }
    }
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  function init() {
    const composerEl = findComposer();
    if (!composerEl) { setTimeout(init, 800); return; }

    const anchor = ensureAnchor(composerEl);
    if (!anchor || anchor.querySelector(".kiro-robot")) return;

    const robot = new kiroRobot(anchor);
    window.kiroRobot = robot;

    const editableEl =
      composerEl.querySelector('[contenteditable="true"]') ||
      composerEl.querySelector("textarea") ||
      composerEl;

    let typingTimer       = null;
    let classifierRunning = false;

    editableEl.addEventListener("input", () => {
      if (robot._blockNextClassify) {
        robot._blockNextClassify = false;
        return;
      }

      if (robot.card) return;

      robot.setState("observe");
      clearTimeout(typingTimer);

      typingTimer = setTimeout(async () => {
        const prompt = (editableEl.innerText || editableEl.value || "").trim();

        if (prompt.length < 5) {
          robot.setState("sleep");
          return;
        }

        if (classifierRunning) return;
        classifierRunning = true;

        try {
          const result = await classifyPrompt(prompt);
          classifierRunning = false;
          console.log("[kiro] classify:", result);

          if (result.is_complex) {
            robot.currentPrompt = prompt;
            robot.setState("wave");
          } else {
            robot.setState("sleep");
          }
        } catch (err) {
          console.error("[kiro] classify error:", err);
          classifierRunning = false;
          robot.setState("sleep");
        }
      }, 3000);
    });

    editableEl.addEventListener("blur", () => {
      if (robot.currentState === "observe") robot.setState("sleep");
    });
  }

  window.kiroDebug = () => {
    const el = findComposer();
    if (!el) { console.log("[kiro] No composer found."); return; }
    el.style.outline = "3px solid red";
    console.log("[kiro] Composer:", el);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  setInterval(() => {
    if (!document.querySelector(".kiro-robot") && findComposer()) init();
  }, 2000);

})();