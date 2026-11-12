/*
 * "Ask AI" widget for ucp.dev. Dependency-free. Talks to the Worker in ask/
 * over Server-Sent Events and renders a constrained subset of Markdown.
 *
 * Config comes from <script id="ask-ai-config"> rendered by overrides/main.html.
 */
(() => {
  

  const configEl = document.getElementById("ask-ai-config");
  if (!configEl) return;
  let config;
  try {
    config = JSON.parse(configEl.textContent);
  } catch (_e) {
    return;
  }
  if (!config?.endpoint) return;

  const STORAGE_KEY = "ucp-ask-ai-thread";
  const OPEN_KEY = "ucp-ask-ai-open";
  const MAX_STORED_MESSAGES = 12;
  const SUGGESTIONS = [
    "What is UCP and who is it for?",
    "How does a checkout session work end to end?",
    "What is the difference between REST and MCP transports?",
    "How do payment handlers work?",
    "How do I get started implementing UCP?",
  ];
  const SPARK =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l1.8 5.6L19.5 9.5l-5.7 1.9L12 17l-1.8-5.6L4.5 9.5l5.7-1.9L12 2zm7 11l.9 2.6 2.6.9-2.6.9L19 20l-.9-2.6-2.6-.9 2.6-.9L19 13zM5 14l.7 2 2 .7-2 .7L5 19.5l-.7-2.1-2-.7 2-.7L5 14z"/></svg>';

  /* ------------------------------------------------------------------ state */
  let thread = loadThread(); // [{role, content, sources?}]
  let controller = null;

  function loadThread() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (_e) {
      return [];
    }
  }
  function saveThread() {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(thread.slice(-MAX_STORED_MESSAGES)));
    } catch (_e) {
      /* storage unavailable: conversation simply does not persist */
    }
  }

  /* --------------------------------------------------------------- markup */
  const SEND =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12l1.4 1.4L11 7.8V20h2V7.8l5.6 5.6L20 12l-8-8-8 8z"/></svg>';

  // Header entry point, placed next to search like other developer docs sites.
  const fab = el("button", {
    class: "ask-ai-header-btn",
    type: "button",
    "aria-label": "Ask AI about the UCP documentation",
    "aria-expanded": "false",
    title: "Ask AI (press . to open)",
  });
  fab.innerHTML = `${SPARK}<span>Ask AI</span><kbd>.</kbd>`;
  const headerInner = document.querySelector(".md-header__inner");
  const search = headerInner ? headerInner.querySelector(".md-search") : null;
  if (headerInner) headerInner.insertBefore(fab, search ? search.nextSibling : null);
  else document.body.appendChild(fab);

  const panel = el("section", { class: "ask-ai-panel", role: "dialog", "aria-label": "Ask AI", hidden: "" });
  const header = el("div", { class: "ask-ai-header" });
  header.innerHTML = SPARK;
  const title = el("strong");
  title.textContent = "Ask AI";
  const clearBtn = el("button", { type: "button", title: "Start a new conversation" });
  clearBtn.textContent = "New chat";
  const closeBtn = el("button", { type: "button", class: "ask-ai-close", "aria-label": "Close" });
  closeBtn.textContent = "\u2715";
  header.appendChild(title);
  header.appendChild(clearBtn);
  header.appendChild(closeBtn);

  const messages = el("div", { class: "ask-ai-messages", "aria-live": "polite" });
  const form = el("form", { class: "ask-ai-form" });
  const input = el("textarea", {
    rows: "1",
    placeholder: "Ask about UCP\u2026",
    maxlength: "600",
    "aria-label": "Your question",
  });
  const sendBtn = el("button", { type: "submit", "aria-label": "Send" });
  sendBtn.innerHTML = SEND;
  form.appendChild(input);
  form.appendChild(sendBtn);
  const footer = el("div", { class: "ask-ai-footer" });
  footer.textContent = `Answers are generated from the ${config.version || "current"} documentation and can be wrong. Check the linked sections.`;

  panel.appendChild(header);
  panel.appendChild(messages);
  panel.appendChild(form);
  panel.appendChild(footer);
  document.body.appendChild(panel);

  /* -------------------------------------------------------------- behavior */
  fab.addEventListener("click", () => { setOpen(true); input.focus(); });
  closeBtn.addEventListener("click", () => { setOpen(false); });
  clearBtn.addEventListener("click", () => {
    if (controller) controller.abort();
    thread = [];
    saveThread();
    renderThread();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !panel.hidden) {
      setOpen(false);
      return;
    }
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target?.tagName) || "") || (e.target?.isContentEditable);
    if (e.key === "." && !typing && !e.metaKey && !e.ctrlKey && !e.altKey && panel.hidden) {
      e.preventDefault();
      setOpen(true);
      input.focus();
    }
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event("submit", { cancelable: true }));
    }
  });
  input.addEventListener("input", autosize);
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q || controller) return;
    input.value = "";
    autosize();
    ask(q);
  });

  function setOpen(open) {
    panel.hidden = !open;
    fab.setAttribute("aria-expanded", open ? "true" : "false");
    try { sessionStorage.setItem(OPEN_KEY, open ? "1" : "0"); } catch (_e) { /* ignore */ }
    if (open) { renderThread(); scrollToEnd(); }
  }
  function autosize() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 96)}px`;
  }

  function renderThread() {
    messages.innerHTML = "";
    if (!thread.length) {
      const intro = el("div", { class: "ask-ai-intro" });
      intro.innerHTML =
        "<h3>How can I help?</h3><p>Ask anything about the Universal Commerce Protocol. Answers cite the documentation sections they come from.</p>";
      messages.appendChild(intro);
      const sug = el("div", { class: "ask-ai-suggestions" });
      SUGGESTIONS.forEach((s) => {
        const b = el("button", { type: "button" });
        b.textContent = s;
        b.addEventListener("click", () => { ask(s); });
        sug.appendChild(b);
      });
      messages.appendChild(sug);
      return;
    }
    thread.forEach((m) => { messages.appendChild(renderMessage(m)); });
  }

  function renderMessage(m) {
    const node = el("div", { class: `ask-ai-msg ask-ai-msg--${m.role}` });
    if (m.role === "user") {
      node.textContent = m.content;
    } else {
      node.innerHTML = renderMarkdown(m.content, m.sources || []);
      if (m.sources?.length) node.appendChild(renderSources(m.sources));
    }
    return node;
  }

  function renderSources(sources) {
    const wrap = el("div", { class: "ask-ai-sources" });
    const label = el("span");
    label.textContent = "Sources";
    wrap.appendChild(label);
    const ol = el("ol");
    for (const s of sources) {
      const li = el("li");
      const a = el("a", { href: s.url, target: "_blank", rel: "noopener" });
      const n = el("b");
      n.textContent = String(s.n);
      const t = document.createTextNode(s.title);
      a.appendChild(n);
      a.appendChild(t);
      if (s.heading && s.heading !== s.title) {
        const h = el("small");
        h.textContent = `\u203a ${s.heading}`;
        a.appendChild(h);
      }
      li.appendChild(a);
      ol.appendChild(li);
    }
    wrap.appendChild(ol);
    return wrap;
  }

  function scrollToEnd() { messages.scrollTop = messages.scrollHeight; }

  /* ------------------------------------------------------------------ ask */
  function ask(question) {
    setOpen(true);
    const history = thread
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map((m) => ({ role: m.role, content: m.content }));

    thread.push({ role: "user", content: question });
    const reply = { role: "assistant", content: "", sources: [] };
    thread.push(reply);
    renderThread();
    const node = messages.lastElementChild;
    node.classList.add("ask-ai-pending");
    scrollToEnd();
    sendBtn.disabled = true;
    sendBtn.textContent = "…";

    controller = new AbortController();
    let allSources = [];

    fetch(config.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question, history: history, page: location.href.split("#")[0] }),
      signal: controller.signal,
    })
      .then((res) => {
        if (!res.ok) {
          return res.json().catch(() => ({})).then((body) => {
            throw new Error(body.error || (`Request failed (${res.status})`));
          });
        }
        return readSSE(res.body, (event, data) => {
          if (event === "sources") {
            allSources = data;
          } else if (event === "delta") {
            reply.content += data.text || "";
            node.innerHTML = renderMarkdown(reply.content, allSources);
            scrollToEnd();
          } else if (event === "done") {
            reply.sources = data.sources || [];
          } else if (event === "error") {
            throw new Error(data.message || "Something went wrong.");
          }
        });
      })
      .then(() => {
        if (!reply.content.trim()) throw new Error("No answer was returned.");
        finish();
      })
      .catch((err) => {
        if (err && err.name === "AbortError") { finish(); return; }
        thread.pop(); // drop the empty assistant turn
        node.classList.remove("ask-ai-pending");
        const e = el("div", { class: "ask-ai-error" });
        e.textContent = (err?.message) || "Something went wrong.";
        node.replaceWith(e);
        controller = null;
        sendBtn.disabled = false;
        saveThread();
      });

    function finish() {
      node.classList.remove("ask-ai-pending");
      node.innerHTML = renderMarkdown(reply.content, reply.sources);
      if (reply.sources.length) node.appendChild(renderSources(reply.sources));
      controller = null;
      sendBtn.disabled = false;
      saveThread();
      scrollToEnd();
    }
  }

  /* Parse a text/event-stream body, calling onEvent(eventName, parsedData). */
  function readSSE(body, onEvent) {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    function pump() {
      return reader.read().then((r) => {
        buffer += decoder.decode(r.value || new Uint8Array(), { stream: !r.done });
        let idx = buffer.indexOf("\n\n");
        while (idx >= 0) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          let event = "message";
          let data = "";
          for (const line of frame.split("\n")) {
            if (line.indexOf("event:") === 0) event = line.slice(6).trim();
            else if (line.indexOf("data:") === 0) data += line.slice(5).trim();
          }
          if (data) onEvent(event, JSON.parse(data));
          idx = buffer.indexOf("\n\n");
        }
        if (!r.done) return pump();
      });
    }
    return pump();
  }

  /* ------------------------------------------------------------ markdown */
  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function inline(text, sources) {
    let out = escapeHtml(text);
    out = out.replace(/`([^`]+)`/g, (_, code) => `<code>${code}</code>`);
    out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    out = out.replace(/(^|[\s(])_([^_]+)_(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>");
    out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, (_, label, href) => `<a href="${href}" target="_blank" rel="noopener">${label}</a>`);
    out = out.replace(/\[(\d+)\]/g, (_m, n) => {
      let src = null;
      for (let i = 0; i < sources.length; i++) if (String(sources[i].n) === n) src = sources[i];
      if (!src) return "";
      return `<a class="ask-ai-cite" href="${escapeHtml(src.url)}" target="_blank" rel="noopener" title="${escapeHtml(`${src.title} › ${src.heading}`)}">${n}</a>`;
    });
    return out;
  }

  /* Supports paragraphs, bullet/numbered lists, fenced code, inline code,
     bold, italics, links and [n] citations. Anything else renders as text. */
  function renderMarkdown(md, sources) {
    let html = "";
    const lines = md.split("\n");
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      if (/^```/.test(line)) {
        const code = [];
        i++;
        while (i < lines.length && !/^```/.test(lines[i])) code.push(lines[i++]);
        i++;
        html += `<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`;
        continue;
      }
      if (/^\s*([-*]|\d+\.)\s+/.test(line)) {
        const ordered = /^\s*\d+\./.test(line);
        const items = [];
        while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
          items.push(lines[i].replace(/^\s*([-*]|\d+\.)\s+/, ""));
          i++;
          while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
            items[items.length - 1] += ` ${lines[i].trim()}`;
            i++;
          }
        }
        html += (ordered ? "<ol>" : "<ul>") + items.map((t) => `<li>${inline(t, sources)}</li>`).join("") + (ordered ? "</ol>" : "</ul>");
        continue;
      }
      if (/^#{1,6}\s/.test(line)) {
        html += `<p><strong>${inline(line.replace(/^#{1,6}\s+/, ""), sources)}</strong></p>`;
        i++;
        continue;
      }
      if (!line.trim()) { i++; continue; }
      const para = [];
      while (i < lines.length && lines[i].trim() && !/^```|^\s*([-*]|\d+\.)\s+|^#{1,6}\s/.test(lines[i])) para.push(lines[i++]);
      html += `<p>${inline(para.join(" "), sources)}</p>`;
    }
    return html;
  }

  /* ----------------------------------------------- search dialog shortcut */
  const searchInput = document.querySelector(".md-search__input");
  const searchOutput = document.querySelector(".md-search__output");
  if (searchInput && searchOutput) {
    const cta = el("button", { class: "ask-ai-search-cta", type: "button", hidden: "" });
    cta.innerHTML = `${SPARK}<span></span>`;
    cta.addEventListener("click", () => {
      const q = searchInput.value.trim();
      const toggle = document.querySelector("[data-md-toggle=search]");
      if (toggle) toggle.checked = false;
      ask(q.length > 3 && !/\?$/.test(q) ? `${q}?` : q);
    });
    searchOutput.insertBefore(cta, searchOutput.firstChild);
    searchInput.addEventListener("input", () => {
      const q = searchInput.value.trim();
      cta.hidden = q.length < 3;
      cta.querySelector("span").textContent = `Ask AI: “${q}”`;
    });
  }

  /* --------------------------------------------------------------- utils */
  function el(tag, attrs) {
    const node = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach((k) => { node.setAttribute(k, attrs[k]); });
    return node;
  }

  try {
    if (sessionStorage.getItem(OPEN_KEY) === "1" && thread.length) setOpen(true);
  } catch (_e) { /* ignore */ }
})();
