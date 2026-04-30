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
  if (!value) return "未知";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function statusLabel(value) {
  const labels = {
    ready: "就绪",
    busy: "忙碌",
    offline: "离线",
    unknown: "未知",
    needs_login: "需登录",
    needs_provider: "需配置 Provider",
    error: "错误",
    todo: "待办",
    in_progress: "进行中",
    in_review: "评审中",
    done: "完成",
    other: "其他",
  };
  return labels[value] || value || "未知";
}

function eventTypeLabel(value) {
  const labels = {
    "user.input": "用户输入",
    "chat.message": "聊天消息",
    "tool.call": "工具调用",
    "tool.result": "工具结果",
    "system.notice": "系统通知",
    "heartbeat.updated": "心跳更新",
    "session.started": "会话开始",
    "session.ended": "会话结束",
    "task.claimed": "任务已认领",
    "task.released": "任务已释放",
    "task.status_changed": "任务状态变更",
    "task.completed": "任务已完成",
  };
  return labels[value] || value || "未知事件";
}

function eventBody(event) {
  const payload = event.payload || {};
  if (event.type === "system.notice" && payload.code === "no_ready_agents" && Array.isArray(payload.unavailable)) {
    const parts = payload.unavailable.map((item) => `${item.name}: ${statusLabel(item.status)}`);
    return `没有匹配到可用 Agent（${parts.join("，")}）`;
  }
  return payload.body || payload.message || payload.summary || "";
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
    ["总数", counts.total],
    ["待办", counts.todo],
    ["进行中", counts.in_progress],
    ["评审中", counts.in_review],
    ["完成", counts.done],
  ];
  dom.boardMetrics.innerHTML = cards.map(([label, value]) => `
    <article class="metric-card">
      <p class="metric-label">${escapeHtml(label)}</p>
      <p class="metric-value">${value}</p>
    </article>
  `).join("");

  dom.taskList.innerHTML = tasks.map((task) => {
    const claim = task.claimed_by ? `<p class="task-claim">认领者：${escapeHtml(task.claimed_by)}</p>` : "";
    const lease = task.lease_expires_at ? `<p class="task-lease">租约到期：${escapeHtml(formatDate(task.lease_expires_at))}</p>` : "";
    return `
      <article class="task-card status-${escapeHtml(task.status || "other")}">
        <div class="task-top">
          <h3>${escapeHtml(task.title || task.id)}</h3>
          <span class="status-pill">${escapeHtml(statusLabel(task.status || "unknown"))}</span>
        </div>
        <p class="task-meta">${escapeHtml(task.id)} · 负责人 ${escapeHtml(task.owner || "未指定")}</p>
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
    const task = heartbeat.task_id ? `<p class="agent-detail">任务：${escapeHtml(heartbeat.task_id)}</p>` : "";
    return `
      <article class="agent-card state-${escapeHtml(status)}">
        <div class="agent-top">
          <h3>${escapeHtml(agent.name)}</h3>
          <span class="status-pill">${escapeHtml(statusLabel(status))}</span>
        </div>
        <p class="agent-detail">探测：${escapeHtml(statusLabel(agent.probe))}</p>
        ${task}
        <p class="agent-detail">最近更新：${escapeHtml(formatDate(heartbeat.updated_at))}</p>
      </article>
    `;
  }).join("");
}

function renderThread() {
  const thread = state.liveThread.thread || {};
  const events = state.liveThread.events || [];
  dom.threadTitle.textContent = thread.title || "主 Agent 线程";
  dom.threadMeta.innerHTML = `
    <div class="meta-block">
      <p class="eyebrow">更新时间</p>
      <p class="meta-value">${escapeHtml(formatDate(thread.updated_at))}</p>
    </div>
    <div class="meta-block">
      <p class="eyebrow">事件数</p>
      <p class="meta-value">${events.length}</p>
    </div>
  `;

  dom.messageList.innerHTML = events.map((event) => {
    const type = event.type || "unknown";
    const payload = event.payload || {};
    const body = eventBody(event);
    const meta = event.meta || {};
    const chips = formatTargets(event.target);
    const status = meta.status ? `<span class="kind-chip">${escapeHtml(statusLabel(meta.status))}</span>` : "";
    const detail = type === "tool.result" ? `
      <div class="tool-detail">
        <span>工具 ${escapeHtml(payload.tool || "")}</span>
        <span>${payload.ok ? "成功" : "失败"}</span>
        <span>${escapeHtml(String(payload.duration_ms ?? ""))}ms</span>
      </div>
      ${payload.error ? `<pre class="message-body">${escapeHtml(payload.error)}</pre>` : ""}
    ` : "";
    return `
      <article class="message-card type-${escapeHtml(type.replaceAll(".", "-"))}">
        <div class="message-top">
          <div class="sender-line">
            <span class="sender">${escapeHtml(event.source || "system")}</span>
            <span class="kind-chip">${escapeHtml(eventTypeLabel(type))}</span>
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
  dom.statusLine.textContent = "刷新中…";
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
    dom.statusLine.textContent = "已就绪";
  } catch (error) {
    dom.statusLine.textContent = `刷新失败：${error.message}`;
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
  dom.statusLine.textContent = "消息路由中…";
  try {
    await fetchJson("/api/live-thread/messages", {
      method: "POST",
      body: JSON.stringify({ body }),
    });
    await refreshAll();
    dom.statusLine.textContent = "消息已发送";
  } catch (error) {
    dom.statusLine.textContent = `发送失败：${error.message}`;
  }
}

dom.refreshButton.addEventListener("click", refreshAll);
dom.chatForm.addEventListener("submit", sendMessage);
refreshAll();
window.setInterval(refreshAll, 5000);
