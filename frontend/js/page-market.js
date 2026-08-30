mountNav("market");

const listEl = document.getElementById("list");
const sectorFilter = document.getElementById("sectorFilter");
const tierFilter = document.getElementById("tierFilter");

let all = [];

function render() {
  const sector = sectorFilter.value;
  const tier = tierFilter.value;
  const filtered = all.filter(s => (!sector || s.sector === sector) && (!tier || s.risk_tier === tier));

  if (filtered.length === 0) {
    listEl.innerHTML = `<p class="muted">No SMEs match these filters.</p>`;
    return;
  }

  listEl.innerHTML = filtered.map(s => `
    <a class="sme-card" href="/sme.html?id=${encodeURIComponent(s.id)}">
      <h3>${esc(s.name)}</h3>
      <div class="sme-meta">${esc(s.sector)} · ${esc(s.city)} · founded ${esc(s.founded_year)} · ${esc(s.employees)} employees</div>
      <div class="sme-desc">Seeking ${fmtMoney(s.funding_goal)} in diaspora capital.</div>
      <div class="sme-card-footer">
        ${tierBadge(s.risk_tier, s.risk_unavailable, s.risk_stale)}
        <span class="muted">${s.risk_score != null ? s.risk_score.toFixed(0) + "/100" : ""}</span>
      </div>
    </a>
  `).join("");
}

async function load() {
  try {
    all = await api.listSmes({ status: "vetted" });
    const sectors = [...new Set(all.map(s => s.sector))].sort();
    sectorFilter.innerHTML = `<option value="">All sectors</option>` + sectors.map(s => `<option>${esc(s)}</option>`).join("");
    render();
  } catch (e) {
    listEl.innerHTML = `<div class="notice notice-error">Could not load SMEs: ${esc(e.message)}</div>`;
  }
}

sectorFilter.addEventListener("change", render);
tierFilter.addEventListener("change", render);
load();
