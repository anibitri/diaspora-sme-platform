mountNav("admin");
const contentEl = document.getElementById("content");

function tokenGate() {
  return `
    <h1>Admin / vetim</h1>
    <p class="lede">Simulon si një operator platforme do të shqyrtonte NVM-të përpara se t'i
      listonte. Ky është një token demo i përbashkët, jo autentikim real.</p>
    <div class="card" style="max-width:420px">
      <label for="token">Token admini</label>
      <input id="token" type="password" placeholder="demo-admin-token" />
      <button class="primary" id="tokenBtn" style="margin-top:12px">Hyr</button>
      <p class="muted" style="margin-top:8px">Ndihmë: <code>demo-admin-token</code></p>
    </div>
  `;
}

function smeRow(s) {
  const actions = [];
  if (s.status === "pending") {
    actions.push(`<button class="primary" data-action="approve" data-id="${s.id}">Mirato</button>`);
    actions.push(`<button class="danger" data-action="reject" data-id="${s.id}">Refuzo</button>`);
  } else if (s.status === "vetted") {
    actions.push(`<button class="danger" data-action="delist" data-id="${s.id}">Hiq nga lista</button>`);
  }
  const contact = s.contact_email
    ? `<a class="contact-link" href="mailto:${esc(s.contact_email)}" title="Kontakto ${esc(s.contact_name || s.name)}">✉ ${esc(s.contact_email)}</a>`
    : `<span class="muted">—</span>`;
  return `
    <tr>
      <td><a href="/sme.html?id=${encodeURIComponent(s.id)}">${esc(s.name)}</a></td>
      <td>${esc(sectorLabel(s.sector))}</td>
      <td>${tierBadge(s.risk_tier, s.risk_unavailable, s.risk_stale)}</td>
      <td>${contact}</td>
      <td><span class="status-pill">${esc(statusLabel(s.status))}</span></td>
      <td>${actions.join(" ")}</td>
    </tr>`;
}

const STATUS_HEADINGS_SQ = { pending: "në pritje", vetted: "aktive", rejected: "të refuzuara", delisted: "të hequra" };

async function renderQueue() {
  const statuses = ["pending", "vetted", "rejected", "delisted"];
  const lists = await Promise.all(statuses.map(s => api.adminListSmes(s)));
  return statuses.map((status, idx) => {
    const rows = lists[idx];
    if (!rows.length && status !== "pending") return "";
    return `
      <h3 class="section-gap">${esc(STATUS_HEADINGS_SQ[status])} (${rows.length})</h3>
      ${rows.length ? `<table><thead><tr><th>NVM</th><th>Sektori</th><th>Rreziku</th><th>Kontakti</th><th>Statusi</th><th>Veprime</th></tr></thead>
      <tbody>${rows.map(smeRow).join("")}</tbody></table>` : `<p class="muted">Asnjë.</p>`}
    `;
  }).join("");
}

const ACTION_LABELS_SQ = { approve: "miratim", reject: "refuzim", delist: "heqje nga lista", submit: "dorëzim" };

async function renderAuditLog() {
  const log = await api.adminAuditLog();
  if (!log.length) return `<p class="muted">Ende asnjë veprim i regjistruar.</p>`;
  const rows = log.map(a => `
    <tr>
      <td>${fmtDate(a.created_at)}</td>
      <td>${esc(a.actor)}</td>
      <td><span class="status-pill">${esc(ACTION_LABELS_SQ[a.action] || a.action)}</span></td>
      <td>${a.sme_id ?? "-"}</td>
      <td class="muted">${esc(a.notes || "")}</td>
    </tr>`).join("");
  return `<table><thead><tr><th>Kur</th><th>Aktori</th><th>Veprimi</th><th>ID e NVM-së</th><th>Shënime</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function attachActionHandlers() {
  document.querySelectorAll("button[data-action]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      const action = btn.dataset.action;
      const notes = prompt(`Shënime për këtë vendim (opsionale):`, "") || "";
      btn.disabled = true;
      try {
        if (action === "approve") await api.adminApprove(id, notes);
        if (action === "reject") await api.adminReject(id, notes);
        if (action === "delist") await api.adminDelist(id, notes);
        await renderAll();
      } catch (e) {
        alert(trErr(e));
        btn.disabled = false;
      }
    });
  });
}

async function renderAll() {
  try {
    const [queueHtml, auditHtml] = await Promise.all([renderQueue(), renderAuditLog()]);
    contentEl.innerHTML = `
      <h1>Admin / vetim</h1>
      <p class="lede">Miraton ose refuzon NVM-të në pritje, dhe heq nga lista ato tashmë të
        vlerësuara. Çdo vendim shkruhet në regjistrin e auditimit më poshtë. Klikoni emrin e
        biznesit për të parë historikun e plotë të bilanceve, të dhënat e kontaktit dhe ndarjen
        e vlerësimit të rrezikut përpara se të vendosni. Kontakti i biznesit është gjithashtu i
        disponueshëm direkt në tabelë, si lidhje email.</p>
      <div class="card section-gap">${queueHtml}</div>
      <div class="card section-gap">
        <h2>Regjistri i auditimit</h2>
        ${auditHtml}
      </div>
      <button id="logoutBtn" style="margin-top:16px">Pastro token-in e adminit</button>
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
      contentEl.innerHTML = `<div class="notice notice-error">${esc(trErr(e))}</div>`;
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
  contentEl.innerHTML = `<div class="spinner-text">Duke ngarkuar…</div>`;
  renderAll();
}

render();
