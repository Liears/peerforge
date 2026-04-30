const state = {
  board: { tasks: [] },
  liveThread: { thread: {}, events: [] },
  agents: [],
};

const dom = {
  refreshButton: document.querySelector("#refresh-button"),
  statusLine: document.querySelector("#status-line"),
  boardMetrics: document.querySelector("#board-metrics"),
  taskList: document.querySelector("#task-list"),
  threadTitle: document.querySelector("#thread-title"),
  threadMeta: document.querySelector("#thread-meta"),
  messageList: document.querySelector("#message-list"),
  chatForm: document.querySelector("#chat-form"),
  chatInput: document.querySelector("#chat-input"),
  agentList: document.querySelector("#agent-list"),
};

async function fetchJson(url, options = undefined) {
  const response = await fetch(url, {
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `${response.status} ${response.statusText}`);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function formatDate(value) {
  if (!value) return "unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatTargets(targets) {
  return (targets || []).map((target) => {
    if (target === "@all") {
      return `<span class="recipient-chip broadcast">@all</span>`;
    }
    const label = String(target).startsWith("@") ? target : `@${target}`;
    return `<span class="recipient-chip">${escapeHtml(label)}</span>`;
  }).join("");
}

function boardCounts(tasks) {
  const counts = { total: tasks.length, todo: 0, in_progress: 0, in_review: 0, done: 0, other: 0 };
  for (const task of tasks) {
    const status = task.status || "other";
    if (status in counts) counts[status] += 1;
    else counts.other += 1;
  }
  return counts;
}

function renderBoard() {
  const tasks = state.board.tasks || [];
  const counts = boardCounts(tasks);
  const cards = [
    ["Total", counts.total],
    ["Todo", counts.todo],
    ["In Progress", counts.in_progress],
    ["In Review", counts.in_review],
    ["Done", counts.done],
  ];
  dom.boardMetrics.innerHTML = cards.map(([label, value]) => `
    <article class="metric-card">
      <p class="metric-label">${escapeHtml(label)}</p>
      <p class="metric-value">${value}</p>
    </article>
  `).join("");

  dom.taskList.innerHTML = tasks.map((task) => {
    const claim = task.claimed_by ? `<p class="task-claim">claimed by ${escapeHtml(task.claimed_by)}</p>` : "";
    const lease = task.lease_expires_at ? `<p class="task-lease">lease ${escapeHtml(formatDate(task.lease_expires_at))}</p>` : "";
    return `
      <article class="task-card status-${escapeHtml(task.status || "other")}">
        <div class="task-top">
          <h3>${escapeHtml(task.title || task.id)}</h3>
          <span class="status-pill">${escapeHtml(task.status || "unknown")}</span>
        </div>
        <p class="task-meta">${escapeHtml(task.id)} · owner ${escapeHtml(task.owner || "n/a")}</p>
        ${claim}
        ${lease}
      </article>
    `;
  }).join("");
}

function renderAgents() {
  dom.agentList.innerHTML = state.agents.map((agent) => {
    const heartbeat = agent.heartbeat_raw || {};
    const status = agent.heartbeat || agent.probe || "offline";
    const task = heartbeat.task_id ? `<p class="agent-detail">task ${escapeHtml(heartbeat.task_id)}</p>` : "";
    return `
      <article class="agent-card state-${escapeHtml(status)}">
        <div class="agent-top">
          <h3>${escapeHtml(agent.name)}</h3>
          <span class="status-pill">${escapeHtml(status)}</span>
        </div>
        <p class="agent-detail">probe ${escapeHtml(agent.probe)}</p>
        ${task}
        <p class="agent-detail">updated ${escapeHtml(formatDate(heartbeat.updated_at))}</p>
      </article>
    `;
  }).join("");
}

function renderThread() {
  const thread = state.liveThread.thread || {};
  const events = state.liveThread.events || [];
  dom.threadTitle.textContent = thread.title || "Main agent thread";
  dom.threadMeta.innerHTML = `
    <div class="meta-block">
      <p class="eyebrow">Updated</p>
      <p class="meta-value">${escapeHtml(formatDate(thread.updated_at))}</p>
    </div>
    <div class="meta-block">
      <p class="eyebrow">Events</p>
      <p class="meta-value">${events.length}</p>
    </div>
  `;

  dom.messageList.innerHTML = events.map((event) => {
    const type = event.type || "unknown";
    const payload = event.payload || {};
    const body = payload.body || payload.message || payload.summary || "";
    const meta = event.meta || {};
    const chips = formatTargets(event.target);
    const status = meta.status ? `<span class="kind-chip">${escapeHtml(meta.status)}</span>` : "";
    const detail = type === "tool.result" ? `
      <div class="tool-detail">
        <span>tool ${escapeHtml(payload.tool || "")}</span>
        <span>${payload.ok ? "ok" : "error"}</span>
        <span>${escapeHtml(String(payload.duration_ms ?? ""))}ms</span>
      </div>
      ${payload.error ? `<pre class="message-body">${escapeHtml(payload.error)}</pre>` : ""}
    ` : "";
    return `
      <article class="message-card type-${escapeHtml(type.replaceAll(".", "-"))}">
        <div class="message-top">
          <div class="sender-line">
            <span class="sender">${escapeHtml(event.source || "system")}</span>
            <span class="kind-chip">${escapeHtml(type)}</span>
            ${status}
          </div>
          <span class="timestamp">${escapeHtml(formatDate(event.created_at))}</span>
        </div>
        <div class="recipient-row">${chips}</div>
        ${body ? `<pre class="message-body">${escapeHtml(body)}</pre>` : ""}
        ${detail}
      </article>
    `;
  }).join("");
  dom.messageList.scrollTop = dom.messageList.scrollHeight;
}

async function refreshAll() {
  dom.statusLine.textContent = "Refreshing…";
  try {
    const [board, liveThread, agentsPayload] = await Promise.all([
      fetchJson("/api/board"),
      fetchJson("/api/live-thread"),
      fetchJson("/api/agents"),
    ]);
    state.board = board;
    state.liveThread = liveThread;
    state.agents = agentsPayload.agents || [];
    renderBoard();
    renderAgents();
    renderThread();
    dom.statusLine.textContent = "Ready";
  } catch (error) {
    dom.statusLine.textContent = `Refresh failed: ${error.message}`;
  }
}

async function sendMessage(event) {
  event.preventDefault();
  const body = dom.chatInput.value.trim();
  if (!body) return;
  dom.chatInput.value = "";
  const optimisticEvent = {
    id: `optimistic_${Date.now()}`,
    type: "user.input",
    source: "user",
    target: ["@pending"],
    created_at: new Date().toISOString(),
    payload: { body },
  };
  state.liveThread.events = [...(state.liveThread.events || []), optimisticEvent];
  renderThread();
  dom.statusLine.textContent = "Routing message…";
  try {
    await fetchJson("/api/live-thread/messages", {
      method: "POST",
      body: JSON.stringify({ body }),
    });
    await refreshAll();
    dom.statusLine.textContent = "Message routed";
  } catch (error) {
    dom.statusLine.textContent = `Send failed: ${error.message}`;
  }
}

dom.refreshButton.addEventListener("click", refreshAll);
dom.chatForm.addEventListener("submit", sendMessage);
refreshAll();
window.setInterval(refreshAll, 5000);
