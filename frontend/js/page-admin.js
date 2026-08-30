mountNav("admin");
const contentEl = document.getElementById("content");

function tokenGate() {
  return `
    <h1>Admin / vetting</h1>
    <p class="lede">Simulates how a platform operator would review SMEs before listing them
      (thesis §5). This is a shared-secret demo token, not real authentication.</p>
    <div class="card" style="max-width:420px">
      <label for="token">Admin token</label>
      <input id="token" type="password" placeholder="demo-admin-token" />
      <button class="primary" id="tokenBtn" style="margin-top:12px">Enter</button>
      <p class="muted" style="margin-top:8px">Hint: <code>demo-admin-token</code></p>
    </div>
  `;
}

function smeRow(s) {
  const actions = [];
  if (s.status === "pending") {
    actions.push(`<button class="primary" data-action="approve" data-id="${s.id}">Approve</button>`);
    actions.push(`<button class="danger" data-action="reject" data-id="${s.id}">Reject</button>`);
  } else if (s.status === "vetted") {
    actions.push(`<button class="danger" data-action="delist" data-id="${s.id}">Delist</button>`);
  }
  return `
    <tr>
      <td><a href="/sme.html?id=${encodeURIComponent(s.id)}">${esc(s.name)}</a></td>
      <td>${esc(s.sector)}</td>
      <td>${tierBadge(s.risk_tier, s.risk_unavailable, s.risk_stale)}</td>
      <td><span class="status-pill">${esc(s.status)}</span></td>
      <td>${actions.join(" ")}</td>
    </tr>`;
}

async function renderQueue() {
  const statuses = ["pending", "vetted", "rejected", "delisted"];
  const lists = await Promise.all(statuses.map(s => api.adminListSmes(s)));
  return statuses.map((status, idx) => {
    const rows = lists[idx];
    if (!rows.length && status !== "pending") return "";
    return `
      <h3 class="section-gap">${esc(status)} (${rows.length})</h3>
      ${rows.length ? `<table><thead><tr><th>SME</th><th>Sector</th><th>Risk</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody>${rows.map(smeRow).join("")}</tbody></table>` : `<p class="muted">None.</p>`}
    `;
  }).join("");
}

async function renderAuditLog() {
  const log = await api.adminAuditLog();
  if (!log.length) return `<p class="muted">No actions recorded yet.</p>`;
  const rows = log.map(a => `
    <tr>
      <td>${fmtDate(a.created_at)}</td>
      <td>${esc(a.actor)}</td>
      <td><span class="status-pill">${esc(a.action)}</span></td>
      <td>${a.sme_id ?? "-"}</td>
      <td class="muted">${esc(a.notes || "")}</td>
    </tr>`).join("");
  return `<table><thead><tr><th>When</th><th>Actor</th><th>Action</th><th>SME id</th><th>Notes</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function attachActionHandlers() {
  document.querySelectorAll("button[data-action]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      const action = btn.dataset.action;
      const notes = prompt(`Notes for this ${action} decision (optional):`, "") || "";
      btn.disabled = true;
      try {
        if (action === "approve") await api.adminApprove(id, notes);
        if (action === "reject") await api.adminReject(id, notes);
        if (action === "delist") await api.adminDelist(id, notes);
        await renderAll();
      } catch (e) {
        alert(e.message);
        btn.disabled = false;
      }
    });
  });
}

async function renderAll() {
  try {
    const [queueHtml, auditHtml] = await Promise.all([renderQueue(), renderAuditLog()]);
    contentEl.innerHTML = `
      <h1>Admin / vetting</h1>
      <p class="lede">Approve or reject pending SMEs, and delist ones already vetted. Every decision
        is written to an append-only audit log below. Click a business name to review its full
        filing history, contact details, and risk-score breakdown before deciding.</p>
      <div class="card section-gap">${queueHtml}</div>
      <div class="card section-gap">
        <h2>Audit log</h2>
        ${auditHtml}
      </div>
      <button id="logoutBtn" style="margin-top:16px">Clear admin token</button>
    `;
    attachActionHandlers();
    document.getElementById("logoutBtn").addEventListener("click", () => {
      setAdminToken("");
      render();
    });
  } catch (e) {
    if (e.status === 401) {
      setAdminToken("");
      render();
    } else {
      contentEl.innerHTML = `<div class="notice notice-error">${esc(e.message)}</div>`;
    }
  }
}

function render() {
  if (!getAdminToken()) {
    contentEl.innerHTML = tokenGate();
    document.getElementById("tokenBtn").addEventListener("click", () => {
      setAdminToken(document.getElementById("token").value.trim());
      render();
    });
    return;
  }
  contentEl.innerHTML = `<div class="spinner-text">Loading…</div>`;
  renderAll();
}

render();
