const state = {
  sessions: [],
  selectedSessionId: null,
  board: { tasks: [] },
};

const dom = {
  refreshButton: document.querySelector("#refresh-button"),
  statusLine: document.querySelector("#status-line"),
  boardMetrics: document.querySelector("#board-metrics"),
  sessionCount: document.querySelector("#session-count"),
  sessionList: document.querySelector("#session-list"),
  transcriptTitle: document.querySelector("#transcript-title"),
  transcriptMeta: document.querySelector("#transcript-meta"),
  messageList: document.querySelector("#message-list"),
};

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function formatDate(value) {
  if (!value) return "unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function boardMetrics(tasks) {
  const counts = {
    total: tasks.length,
    todo: 0,
    in_progress: 0,
    in_review: 0,
    done: 0,
    other: 0,
  };
  for (const task of tasks) {
    const status = task.status || "other";
    if (status in counts) {
      counts[status] += 1;
    } else {
      counts.other += 1;
    }
  }
  return counts;
}

function renderBoard() {
  const counts = boardMetrics(state.board.tasks || []);
  const cards = [
    ["Total", counts.total],
    ["Todo", counts.todo],
    ["In Progress", counts.in_progress],
    ["In Review", counts.in_review],
    ["Done", counts.done],
  ];
  dom.boardMetrics.innerHTML = cards
    .map(
      ([label, value]) => `
        <article class="metric-card">
          <p class="metric-label">${escapeHtml(label)}</p>
          <p class="metric-value">${value}</p>
        </article>
      `,
    )
    .join("");
}

function renderSessions() {
  dom.sessionCount.textContent = String(state.sessions.length);
  dom.sessionList.innerHTML = state.sessions
    .map((session) => {
      const active = session.id === state.selectedSessionId ? "active" : "";
      const agents = (session.agents || [])
        .map((agent) => `<span class="agent-chip">${escapeHtml(agent)}</span>`)
        .join("");
      return `
        <button class="session-card ${active}" data-session-id="${escapeHtml(session.id)}">
          <div>
            <h3>${escapeHtml(session.title)}</h3>
            <p>${escapeHtml(formatDate(session.created_at))}</p>
          </div>
          <p>${escapeHtml(session.task || "").slice(0, 140)}</p>
          <div class="agent-row">${agents}</div>
        </button>
      `;
    })
    .join("");

  for (const button of dom.sessionList.querySelectorAll(".session-card")) {
    button.addEventListener("click", () => loadSession(button.dataset.sessionId));
  }
}

function renderTranscript(payload) {
  const session = payload.session;
  const summary = payload.summary || {};
  const messages = payload.messages || [];
  state.selectedSessionId = session.id;

  dom.transcriptTitle.textContent = session.title;
  dom.transcriptMeta.innerHTML = `
    <div class="meta-block">
      <p class="eyebrow">Created</p>
      <p class="meta-value">${escapeHtml(formatDate(session.created_at))}</p>
    </div>
    <div class="meta-block">
      <p class="eyebrow">Agents</p>
      <p class="meta-value">${escapeHtml((session.agents || []).join(", ") || "none")}</p>
    </div>
    <div class="meta-block">
      <p class="eyebrow">Messages</p>
      <p class="meta-value">${messages.length}</p>
    </div>
  `;

  dom.messageList.classList.remove("empty-state");
  dom.messageList.innerHTML = messages
    .map((message) => {
      const recipients = Array.isArray(message.to) ? message.to : [];
      const mentions = recipients.length
        ? recipients
            .map((recipient) => {
              const label = recipient === "*" ? "@all" : `@${recipient}`;
              const klass = recipient === "*" ? "recipient-chip broadcast" : "recipient-chip";
              return `<span class="${klass}">${escapeHtml(label)}</span>`;
            })
            .join("")
        : "";
      const kind = escapeHtml(message.kind || "message");
      return `
        <article class="message-card kind-${kind}">
          <div class="message-top">
            <div class="sender-line">
              <span class="sender">${escapeHtml(message.from || "unknown")}</span>
              <span class="kind-chip kind-${kind}">${kind}</span>
              <span class="round-label">round ${escapeHtml(message.round ?? "?")}</span>
            </div>
            <span class="timestamp">${escapeHtml(formatDate(message.created_at))}</span>
          </div>
          ${mentions ? `<div class="mention-line recipient-row">${mentions}</div>` : ""}
          <pre class="message-body">${escapeHtml(message.body || "")}</pre>
        </article>
      `;
    })
    .join("");

  renderSessions();
}

async function loadSession(sessionId) {
  dom.statusLine.textContent = `Loading ${sessionId}…`;
  try {
    const payload = await fetchJson(`/api/sessions/${sessionId}`);
    renderTranscript(payload);
    dom.statusLine.textContent = `Loaded ${sessionId}`;
  } catch (error) {
    dom.statusLine.textContent = `Failed to load ${sessionId}: ${error.message}`;
  }
}

async function refreshAll() {
  dom.statusLine.textContent = "Refreshing dashboard…";
  try {
    const [sessionsPayload, boardPayload] = await Promise.all([
      fetchJson("/api/sessions"),
      fetchJson("/api/board"),
    ]);
    state.sessions = sessionsPayload.sessions || [];
    state.board = boardPayload;
    if (!state.selectedSessionId && state.sessions[0]) {
      state.selectedSessionId = state.sessions[0].id;
    }
    renderBoard();
    renderSessions();
    if (state.selectedSessionId) {
      await loadSession(state.selectedSessionId);
    } else {
      dom.statusLine.textContent = "No sessions found";
    }
  } catch (error) {
    dom.statusLine.textContent = `Refresh failed: ${error.message}`;
  }
}

dom.refreshButton.addEventListener("click", refreshAll);
refreshAll();
window.setInterval(refreshAll, 5000);
