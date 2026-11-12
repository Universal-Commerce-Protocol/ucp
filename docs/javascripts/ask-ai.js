/**
 * Copyright 2026 UCP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
 * "Ask AI about UCP". Dependency-free. Talks to the Worker in ask/ over
 * Server-Sent Events and renders a constrained subset of Markdown.
 * Config comes from the #ask-ai-config element rendered by overrides/main.html.
 */
(() => {
  const configEl = document.getElementById("ask-ai-config");
  if (!configEl) return;
  const config = {
    endpoint: configEl.dataset.endpoint || "",
    version: configEl.dataset.version || "",
  };
  if (!config.endpoint) return;

  const LABEL = "Ask AI about UCP";
  // Links in answers are rendered only when they point at the docs or the
  // project's GitHub; anything else stays plain text.
  const LINK_HOSTS = [location.host, "ucp.dev", "github.com"];
  const STORAGE_KEY = "ucp-ask-ai-thread";
  const OPEN_KEY = "ucp-ask-ai-open";
  const MAX_STORED_MESSAGES = 12;
  const EXAMPLES = [
    "How does a platform discover which capabilities a business supports?",
    "What happens between creating and completing a checkout?",
    "How do payment handlers fit into a checkout?",
  ];
  const ICON_CHAT =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2zm0 14H5.2L4 17.2V4h16v12z"/></svg>';
  const ICON_CLOSE =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 6.4 17.6 5 12 10.6 6.4 5 5 6.4l5.6 5.6L5 17.6 6.4 19l5.6-5.6 5.6 5.6 1.4-1.4-5.6-5.6z"/></svg>';

  /* ------------------------------------------------------------------ state */
  let thread = loadThread(); // [{role, content, sources?}]
  let controller = null;

  function loadThread() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  function saveThread() {
    try {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(thread.slice(-MAX_STORED_MESSAGES))
      );
    } catch {
      /* storage unavailable: conversation simply does not persist */
    }
  }

  /* --------------------------------------------------------------- markup */
  const openBtn = el("button", {
    class: "ask-ai-header-btn",
    type: "button",
    "aria-label": LABEL,
    "aria-expanded": "false",
    title: LABEL,
  });
  openBtn.innerHTML = `${ICON_CHAT}<span>${LABEL}</span>`;
  const headerInner = document.querySelector(".md-header__inner");
  const search = headerInner ? headerInner.querySelector(".md-search") : null;
  if (headerInner)
    headerInner.insertBefore(openBtn, search ? search.nextSibling : null);
  else document.body.appendChild(openBtn);

  const panel = el("section", {
    class: "ask-ai-panel",
    role: "dialog",
    "aria-label": LABEL,
    hidden: "",
  });
  const header = el("div", { class: "ask-ai-header" });
  const title = el("strong");
  title.textContent = LABEL;
  const clearBtn = el("button", { type: "button", class: "ask-ai-new" });
  clearBtn.textContent = "New conversation";
  const closeBtn = el("button", {
    type: "button",
    class: "ask-ai-close",
    "aria-label": "Close",
  });
  closeBtn.innerHTML = ICON_CLOSE;
  header.appendChild(title);
  header.appendChild(clearBtn);
  header.appendChild(closeBtn);

  const messages = el("div", {
    class: "ask-ai-messages",
    "aria-live": "polite",
  });
  const form = el("form", { class: "ask-ai-form" });
  const input = el("textarea", {
    rows: "1",
    placeholder: "Ask a question about UCP",
    maxlength: "600",
    "aria-label": "Your question",
  });
  const sendBtn = el("button", { type: "submit", class: "ask-ai-send" });
  sendBtn.textContent = "Ask";
  form.appendChild(input);
  form.appendChild(sendBtn);
  const footer = el("div", { class: "ask-ai-footer" });
  footer.textContent = `Generated from the ${config.version || "current"} documentation. Answers can be wrong; check the linked sections.`;

  panel.appendChild(header);
  panel.appendChild(messages);
  panel.appendChild(form);
  panel.appendChild(footer);
  document.body.appendChild(panel);

  /* -------------------------------------------------------------- behavior */
  openBtn.addEventListener("click", () => {
    if (!panel.hidden) {
      setOpen(false);
      return;
    }
    setOpen(true);
    input.focus();
  });
  closeBtn.addEventListener("click", () => setOpen(false));
  clearBtn.addEventListener("click", () => {
    if (controller) controller.abort();
    thread = [];
    saveThread();
    renderThread();
    input.focus();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !panel.hidden) setOpen(false);
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit
        ? form.requestSubmit()
        : form.dispatchEvent(new Event("submit", { cancelable: true }));
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
    openBtn.setAttribute("aria-expanded", open ? "true" : "false");
    try {
      sessionStorage.setItem(OPEN_KEY, open ? "1" : "0");
    } catch {
      /* ignore */
    }
    if (open) {
      renderThread();
      scrollToEnd();
    }
  }
  function autosize() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 112)}px`;
  }

  function renderThread() {
    messages.innerHTML = "";
    if (!thread.length) {
      const intro = el("div", { class: "ask-ai-intro" });
      const p = el("p");
      p.textContent =
        "Answers are generated from the UCP documentation and link to the sections they are based on.";
      intro.appendChild(p);
      const eyebrow = el("div", { class: "ask-ai-eyebrow" });
      eyebrow.textContent = "Try asking";
      intro.appendChild(eyebrow);
      const list = el("ul", { class: "ask-ai-examples" });
      for (const s of EXAMPLES) {
        const li = el("li");
        const b = el("button", { type: "button", class: "ask-ai-example" });
        b.textContent = s;
        b.addEventListener("click", () => ask(s));
        li.appendChild(b);
        list.appendChild(li);
      }
      intro.appendChild(list);
      messages.appendChild(intro);
      return;
    }
    for (const m of thread) messages.appendChild(renderMessage(m));
  }

  function renderMessage(m) {
    const node = el("div", { class: `ask-ai-msg ask-ai-msg-${m.role}` });
    if (m.role === "user") {
      node.textContent = m.content;
    } else {
      node.innerHTML = renderMarkdown(m.content, m.sources || []);
      if (m.sources?.length) node.appendChild(renderSources(m.sources));
      if (m.id) node.appendChild(renderFeedback(m));
    }
    return node;
  }

  /* "Was this helpful?" The rating is stored with the anonymous log entry
     and is what a future fine-tune would train on. */
  function renderFeedback(m) {
    const wrap = el("div", { class: "ask-ai-feedback" });
    if (m.helpful === true || m.helpful === false) {
      wrap.textContent = "Thanks for the feedback.";
      return wrap;
    }
    wrap.appendChild(document.createTextNode("Was this helpful? "));
    for (const [label, value] of [
      ["Yes", true],
      ["No", false],
    ]) {
      const b = el("button", { type: "button", class: "ask-ai-feedback-btn" });
      b.textContent = label;
      b.addEventListener("click", () => {
        m.helpful = value;
        saveThread();
        wrap.replaceWith(renderFeedback(m));
        fetch(config.endpoint.replace(/\/v1\/ask$/, "/v1/feedback"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: m.id, day: m.day, helpful: value }),
          keepalive: true,
        }).catch(() => {});
      });
      wrap.appendChild(b);
    }
    return wrap;
  }

  function renderSources(sources) {
    const wrap = el("div", { class: "ask-ai-sources" });
    const eyebrow = el("div", { class: "ask-ai-eyebrow" });
    eyebrow.textContent = "Sources";
    wrap.appendChild(eyebrow);
    const ol = el("ol");
    for (const s of sources) {
      const li = el("li", { value: String(s.n) });
      const a = el("a", { href: s.url, target: "_blank", rel: "noopener" });
      a.textContent = s.title;
      li.appendChild(a);
      if (s.heading && s.heading !== s.title) {
        const h = el("small");
        h.textContent = ` › ${s.heading}`;
        li.appendChild(h);
      }
      ol.appendChild(li);
    }
    wrap.appendChild(ol);
    return wrap;
  }

  function scrollToEnd() {
    messages.scrollTop = messages.scrollHeight;
  }

  /* ------------------------------------------------------------------ ask */
  function ask(question) {
    setOpen(true);
    const history = thread
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map((m) => ({ role: m.role, content: m.content }));

    thread.push({ role: "user", content: question });
    const reply = {
      role: "assistant",
      content: "",
      sources: [],
      id: null,
      day: null,
    };
    thread.push(reply);
    renderThread();
    const node = messages.lastElementChild;
    node.classList.add("ask-ai-pending");
    scrollToEnd();
    sendBtn.disabled = true;

    controller = new AbortController();
    let allSources = [];

    fetch(config.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: question,
        history: history,
        page: location.href.split("#")[0],
      }),
      signal: controller.signal,
    })
      .then((res) => {
        if (!res.ok) {
          return res
            .json()
            .catch(() => ({}))
            .then((body) => {
              throw new Error(body.error || `Request failed (${res.status})`);
            });
        }
        return readSSE(res.body, (event, data) => {
          if (event === "meta") {
            reply.id = data.id || null;
            reply.day = data.day || null;
          } else if (event === "sources") {
            allSources = data;
          } else if (event === "delta") {
            reply.content += data.text || "";
            node.innerHTML = renderMarkdown(reply.content, allSources);
            scrollToEnd();
          } else if (event === "replace") {
            reply.content = data.text || "";
            node.innerHTML = renderMarkdown(reply.content, allSources);
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
        if (err?.name === "AbortError") {
          finish();
          return;
        }
        thread.pop(); // drop the empty assistant turn
        node.classList.remove("ask-ai-pending");
        const e = el("div", { class: "ask-ai-error" });
        e.textContent = err?.message || "Something went wrong.";
        node.replaceWith(e);
        controller = null;
        sendBtn.disabled = false;
        saveThread();
      });

    function finish() {
      node.classList.remove("ask-ai-pending");
      node.innerHTML = renderMarkdown(reply.content, reply.sources);
      if (reply.sources.length) node.appendChild(renderSources(reply.sources));
      if (reply.id) node.appendChild(renderFeedback(reply));
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
        buffer += decoder.decode(r.value || new Uint8Array(), {
          stream: !r.done,
        });
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
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function inline(text, sources) {
    let out = escapeHtml(text);
    out = out.replace(/`([^`]+)`/g, (_, code) => `<code>${code}</code>`);
    out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    out = out.replace(/(^|[\s(])_([^_]+)_(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>");
    out = out.replace(
      /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
      (_whole, label, href) => {
        let host = "";
        try {
          host = new URL(href).host;
        } catch {
          return label;
        }
        if (!LINK_HOSTS.some((h) => host === h || host.endsWith(`.${h}`)))
          return label;
        return `<a href="${href}" target="_blank" rel="noopener">${label}</a>`;
      }
    );
    out = out.replace(/\[(\d+)\]/g, (_m, n) => {
      let src = null;
      for (const s of sources) if (String(s.n) === n) src = s;
      if (!src) return "";
      const label = escapeHtml(`${src.title} › ${src.heading}`);
      return `<sup><a class="ask-ai-cite" href="${escapeHtml(src.url)}" target="_blank" rel="noopener" title="${label}">${n}</a></sup>`;
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
        while (i < lines.length && !/^```/.test(lines[i]))
          code.push(lines[i++]);
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
          while (
            i < lines.length &&
            /^\s{2,}\S/.test(lines[i]) &&
            !/^\s*([-*]|\d+\.)\s+/.test(lines[i])
          ) {
            items[items.length - 1] += ` ${lines[i].trim()}`;
            i++;
          }
        }
        html += `${ordered ? "<ol>" : "<ul>"}${items.map((t) => `<li>${inline(t, sources)}</li>`).join("")}${ordered ? "</ol>" : "</ul>"}`;
        continue;
      }
      if (/^#{1,6}\s/.test(line)) {
        html += `<p><strong>${inline(line.replace(/^#{1,6}\s+/, ""), sources)}</strong></p>`;
        i++;
        continue;
      }
      if (!line.trim()) {
        i++;
        continue;
      }
      const para = [];
      while (
        i < lines.length &&
        lines[i].trim() &&
        !/^```|^\s*([-*]|\d+\.)\s+|^#{1,6}\s/.test(lines[i])
      )
        para.push(lines[i++]);
      html += `<p>${inline(para.join(" "), sources)}</p>`;
    }
    return html;
  }

  /* ----------------------------------------------- search dialog shortcut */
  const searchInput = document.querySelector(".md-search__input");
  const searchOutput = document.querySelector(".md-search__output");
  if (searchInput && searchOutput) {
    const cta = el("button", {
      class: "ask-ai-search-cta",
      type: "button",
      hidden: "",
    });
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
      cta.innerHTML = "";
      const b = el("b");
      b.textContent = `${LABEL}: `;
      cta.appendChild(b);
      cta.appendChild(document.createTextNode(`“${q}”`));
    });
  }

  /* --------------------------------------------------------------- utils */
  function el(tag, attrs) {
    const node = document.createElement(tag);
    if (attrs)
      for (const k of Object.keys(attrs)) node.setAttribute(k, attrs[k]);
    return node;
  }

  try {
    if (sessionStorage.getItem(OPEN_KEY) === "1" && thread.length)
      setOpen(true);
  } catch {
    /* ignore */
  }
})();
