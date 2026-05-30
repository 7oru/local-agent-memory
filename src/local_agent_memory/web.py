from __future__ import annotations

# ruff: noqa: E501


def index_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>local-agent-memory</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8f8;
      --panel: #ffffff;
      --line: #d9dfdd;
      --ink: #17201d;
      --muted: #61706b;
      --accent: #0f766e;
      --accent-2: #92400e;
      --danger: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    button, input, select, textarea {
      font: inherit;
    }
    button {
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      padding: 6px 10px;
      border-radius: 6px;
      cursor: pointer;
    }
    button.primary {
      background: var(--accent);
      border-color: var(--accent);
      color: white;
    }
    button.warn {
      color: var(--accent-2);
      border-color: #e6c68e;
    }
    button.danger {
      color: var(--danger);
      border-color: #f0b4ad;
    }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: white;
      color: var(--ink);
      padding: 7px 9px;
    }
    textarea {
      min-height: 90px;
      resize: vertical;
    }
    .shell {
      min-height: 100vh;
      display: grid;
      grid-template-columns: 220px minmax(0, 1fr) 360px;
    }
    .rail, .detail {
      background: #eef2f0;
      border-right: 1px solid var(--line);
      padding: 16px;
    }
    .detail {
      border-left: 1px solid var(--line);
      border-right: 0;
      background: #fbfcfc;
      overflow: auto;
    }
    h1 {
      margin: 0 0 18px;
      font-size: 18px;
      font-weight: 650;
      letter-spacing: 0;
    }
    h2 {
      margin: 0;
      font-size: 18px;
      letter-spacing: 0;
    }
    .nav {
      display: grid;
      gap: 8px;
    }
    .nav button {
      text-align: left;
      background: transparent;
    }
    .nav button.active {
      background: white;
      border-color: #a7b8b3;
      color: var(--accent);
      font-weight: 650;
    }
    main {
      min-width: 0;
      padding: 18px;
      overflow: auto;
    }
    .topbar, .toolbar, .actions, .form-grid {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .topbar {
      justify-content: space-between;
      margin-bottom: 16px;
    }
    .toolbar {
      margin-bottom: 12px;
    }
    .toolbar input {
      max-width: 260px;
    }
    .quick-add {
      display: grid;
      gap: 8px;
      margin-bottom: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--line);
    }
    .quick-add textarea {
      min-height: 74px;
    }
    .inline-check {
      display: flex;
      flex: 0 0 auto;
      align-items: center;
      gap: 6px;
      padding: 7px 0;
    }
    .inline-check input {
      width: auto;
    }
    .tab {
      display: none;
    }
    .tab.active {
      display: block;
    }
    table {
      width: 100%;
      table-layout: fixed;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 8px;
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      background: #f2f5f4;
    }
    tr {
      cursor: pointer;
    }
    tr:hover td {
      background: #f6fbfa;
    }
    .content-cell {
      max-width: 520px;
      overflow-wrap: anywhere;
    }
    .content-snippet {
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .status {
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 7px;
      background: #fafafa;
      font-size: 12px;
    }
    .stack {
      display: grid;
      gap: 10px;
    }
    label {
      display: grid;
      gap: 4px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }
    label span {
      color: var(--muted);
    }
    .form-grid {
      align-items: end;
    }
    .form-grid label {
      flex: 1 1 0;
    }
    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }
    .muted {
      color: var(--muted);
    }
    .notice {
      min-height: 20px;
      color: var(--muted);
    }
    @media (max-width: 980px) {
      .shell {
        grid-template-columns: 1fr;
      }
      .rail, .detail {
        border: 0;
        border-bottom: 1px solid var(--line);
      }
      .nav {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="rail">
      <h1>local-agent-memory</h1>
      <nav class="nav">
        <button class="active" data-tab-button="pinned">Pinned</button>
        <button data-tab-button="search">Search</button>
        <button data-tab-button="settings">Settings</button>
      </nav>
    </aside>
    <main>
      <div class="topbar">
        <h2 id="view-title">Pinned</h2>
        <div class="notice" id="notice"></div>
      </div>
      <section class="tab active" id="tab-pinned">
        <div class="toolbar">
          <input id="pinned-scope" value="global" aria-label="Pinned scope">
          <button class="primary" id="refresh-pinned">Refresh</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>ID</th><th>Kind</th><th>Scope</th><th>Source</th><th>Updated</th><th>Content</th>
            </tr>
          </thead>
          <tbody id="pinned-body"></tbody>
        </table>
      </section>
      <section class="tab" id="tab-search">
        <div class="quick-add">
          <label><span>Add Memory</span><textarea id="new-content" placeholder="Memory content"></textarea></label>
          <div class="form-grid">
            <label><span>Scope</span><input id="new-scope" value="global"></label>
            <label><span>Kind</span><input id="new-kind" value="note"></label>
          </div>
          <div class="form-grid">
            <label><span>Source ref</span><input id="new-source-ref"></label>
            <label class="inline-check"><input id="new-pin" type="checkbox"> Pin</label>
            <button class="primary" id="add-memory">Add</button>
          </div>
        </div>
        <div class="toolbar">
          <input id="search-query" placeholder="Search" aria-label="Search query">
          <input id="search-scope" placeholder="optional scope" aria-label="Search scope">
          <select id="search-status" aria-label="Search status">
            <option value="">active + pinned</option>
            <option value="active">active</option>
            <option value="pinned">pinned</option>
            <option value="expired">expired</option>
            <option value="deleted">deleted</option>
          </select>
          <button class="primary" id="run-search">Search</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>ID</th><th>Status</th><th>Kind</th><th>Scope</th><th>Source</th><th>Content</th>
            </tr>
          </thead>
          <tbody id="search-body"></tbody>
        </table>
      </section>
      <section class="tab" id="tab-settings">
        <div class="stack">
          <label><span>Database</span><input id="db-path" readonly></label>
          <div class="actions">
            <button class="primary" id="download-export">Export JSON</button>
          </div>
          <label>
            <span>MCP config</span>
            <textarea class="mono" id="mcp-config" readonly></textarea>
          </label>
        </div>
      </section>
    </main>
    <aside class="detail">
      <h2>Memory</h2>
      <div class="stack">
        <label><span>ID</span><input id="detail-id" readonly></label>
        <label><span>Content</span><textarea id="detail-content"></textarea></label>
        <div class="form-grid">
          <label><span>Kind</span><input id="detail-kind"></label>
          <label><span>Scope</span><input id="detail-scope"></label>
        </div>
        <div class="form-grid">
          <label><span>Status</span><input id="detail-status"></label>
          <label><span>Confidence</span><input id="detail-confidence" type="number" step="0.01"></label>
        </div>
        <div class="form-grid">
          <label><span>Source kind</span><input id="detail-source-kind" readonly></label>
          <label><span>Source ref</span><input id="detail-source-ref"></label>
        </div>
        <div class="form-grid">
          <label><span>Created</span><input id="detail-created" readonly></label>
          <label><span>Updated</span><input id="detail-updated" readonly></label>
        </div>
        <div class="actions">
          <button class="primary" id="save-memory">Save</button>
          <button id="pin-memory">Pin</button>
          <button id="unpin-memory">Unpin</button>
          <button class="warn" id="expire-memory">Expire</button>
          <button class="danger" id="delete-memory">Delete</button>
        </div>
        <label><span>Replacement</span><textarea id="replacement-content"></textarea></label>
        <button id="supersede-memory">Supersede</button>
      </div>
    </aside>
  </div>
  <script>
    const state = { selected: null };
    const $ = (id) => document.getElementById(id);
    const mcpConfig = {
      mcpServers: {
        "local-agent-memory": {
          command: "uv",
          args: ["--directory", "/path/to/local-agent-memory", "run", "lam", "mcp"],
          env: { LAM_DB_PATH: "~/.local-agent-memory/memory.db" }
        }
      }
    };

    function notice(text) {
      $("notice").textContent = text || "";
    }

    function setBusy(isBusy, message = "") {
      document.body.setAttribute("aria-busy", String(isBusy));
      document.querySelectorAll("button").forEach((button) => {
        button.disabled = isBusy;
      });
      if (message) notice(message);
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[char]));
    }

    function snippet(value, maxLength = 260) {
      const normalized = String(value ?? "").replace(/\\s+/g, " ").trim();
      if (normalized.length <= maxLength) return normalized;
      return `${normalized.slice(0, maxLength - 1)}...`;
    }

    async function api(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || response.statusText);
      }
      return response.json();
    }

    function renderRows(target, rows, includeStatus = false) {
      target.innerHTML = rows.map((memory) => `
        <tr data-id="${escapeHtml(memory.id)}">
          <td class="mono">${escapeHtml(memory.id)}</td>
          ${includeStatus ? `<td><span class="status">${escapeHtml(memory.status)}</span></td>` : ""}
          <td>${escapeHtml(memory.kind)}</td>
          <td>${escapeHtml(memory.scope)}</td>
          <td>${escapeHtml(memory.source_kind)} ${escapeHtml(memory.source_ref || "")}</td>
          ${includeStatus ? "" : `<td>${escapeHtml(memory.updated_at)}</td>`}
          <td class="content-cell"><div class="content-snippet">${escapeHtml(snippet(memory.content))}</div></td>
        </tr>
      `).join("");
      target.querySelectorAll("tr").forEach((row) => {
        row.addEventListener("click", () => loadMemory(row.dataset.id));
      });
    }

    async function loadPinned() {
      const scope = encodeURIComponent($("pinned-scope").value || "global");
      const rows = await api(`/pinned?scope=${scope}&content_limit=320`);
      renderRows($("pinned-body"), rows);
      notice(`${rows.length} pinned`);
    }

    async function runSearch() {
      const query = $("search-query").value.trim();
      const scope = $("search-scope").value.trim();
      const status = $("search-status").value;
      setBusy(true, query ? "Searching..." : "Loading memories...");
      try {
        const rows = query
          ? await api("/search", {
              method: "POST",
              body: JSON.stringify({
                query,
                scope: scope || null,
                status: status || null,
                include_inactive: Boolean(status),
                content_limit: 320
              })
            })
          : await api(`/memories?${new URLSearchParams({
              ...(scope ? { scope } : {}),
              ...(status ? { status, include_inactive: "true" } : {}),
              limit: "100",
              content_limit: "320"
            })}`);
        renderRows($("search-body"), rows, true);
        notice(query ? `${rows.length} results` : `${rows.length} memories`);
      } finally {
        setBusy(false);
      }
    }

    async function addMemory() {
      setBusy(true, "Adding...");
      const payload = {
        content: $("new-content").value,
        scope: $("new-scope").value || "global",
        kind: $("new-kind").value || "note",
        source_ref: $("new-source-ref").value || null,
        pin: $("new-pin").checked
      };
      try {
        const memory = await api("/memories", { method: "POST", body: JSON.stringify(payload) });
        $("new-content").value = "";
        $("new-source-ref").value = "";
        $("new-pin").checked = false;
        await loadMemory(memory.id);
        await refreshCurrent();
        notice(`added ${memory.id}`);
      } finally {
        setBusy(false);
      }
    }

    async function loadMemory(id) {
      const memory = await api(`/memories/${id}`);
      state.selected = memory;
      $("detail-id").value = memory.id;
      $("detail-content").value = memory.content;
      $("detail-kind").value = memory.kind;
      $("detail-scope").value = memory.scope;
      $("detail-status").value = memory.status;
      $("detail-confidence").value = memory.confidence;
      $("detail-source-kind").value = memory.source_kind;
      $("detail-source-ref").value = memory.source_ref || "";
      $("detail-created").value = memory.created_at;
      $("detail-updated").value = memory.updated_at;
    }

    function selectedId() {
      if (!state.selected?.id) throw new Error("No memory selected");
      return state.selected.id;
    }

    async function saveMemory() {
      const patch = {
        content: $("detail-content").value,
        kind: $("detail-kind").value,
        scope: $("detail-scope").value,
        status: $("detail-status").value,
        confidence: Number($("detail-confidence").value),
        source_ref: $("detail-source-ref").value || null
      };
      await api(`/memories/${selectedId()}`, { method: "PATCH", body: JSON.stringify(patch) });
      await refreshCurrent();
    }

    async function setStatus(status) {
      await api(`/memories/${selectedId()}`, {
        method: "PATCH",
        body: JSON.stringify({ status })
      });
      await refreshCurrent();
    }

    async function deleteMemory() {
      await api(`/memories/${selectedId()}`, { method: "DELETE" });
      await refreshCurrent();
    }

    async function supersedeMemory() {
      await api(`/memories/${selectedId()}/supersede`, {
        method: "POST",
        body: JSON.stringify({ content: $("replacement-content").value })
      });
      $("replacement-content").value = "";
      await refreshCurrent();
    }

    async function refreshCurrent() {
      if (state.selected?.id) await loadMemory(state.selected.id).catch(() => {});
      await loadPinned();
      if ($("search-query").value) await runSearch();
    }

    async function loadSettings() {
      const health = await api("/health");
      $("db-path").value = health.db_path;
      $("mcp-config").value = JSON.stringify(mcpConfig, null, 2);
    }

    async function downloadExport() {
      const payload = await api("/export");
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = Object.assign(document.createElement("a"), {
        href: url,
        download: "local-agent-memory-export.json"
      });
      link.click();
      URL.revokeObjectURL(url);
    }

    document.querySelectorAll("[data-tab-button]").forEach((button) => {
      button.addEventListener("click", () => {
        document.querySelectorAll("[data-tab-button]").forEach((item) => {
          item.classList.toggle("active", item === button);
        });
        document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
        $(`tab-${button.dataset.tabButton}`).classList.add("active");
        $("view-title").textContent = button.textContent;
        if (button.dataset.tabButton === "settings") loadSettings().catch((error) => notice(error.message));
      });
    });
    $("refresh-pinned").addEventListener("click", () => loadPinned().catch((error) => notice(error.message)));
    $("run-search").addEventListener("click", () => runSearch().catch((error) => notice(error.message)));
    $("add-memory").addEventListener("click", () => addMemory().catch((error) => {
      setBusy(false);
      notice(error.message);
    }));
    ["search-query", "search-scope"].forEach((id) => {
      $(id).addEventListener("keydown", (event) => {
        if (event.key === "Enter") runSearch().catch((error) => notice(error.message));
      });
    });
    $("save-memory").addEventListener("click", () => saveMemory().catch((error) => notice(error.message)));
    $("pin-memory").addEventListener("click", () => setStatus("pinned").catch((error) => notice(error.message)));
    $("unpin-memory").addEventListener("click", () => setStatus("active").catch((error) => notice(error.message)));
    $("expire-memory").addEventListener("click", () => setStatus("expired").catch((error) => notice(error.message)));
    $("delete-memory").addEventListener("click", () => deleteMemory().catch((error) => notice(error.message)));
    $("supersede-memory").addEventListener("click", () => supersedeMemory().catch((error) => notice(error.message)));
    $("download-export").addEventListener("click", () => downloadExport().catch((error) => notice(error.message)));
    loadPinned().catch((error) => notice(error.message));
  </script>
</body>
</html>"""
