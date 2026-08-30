mountNav("market");

const listEl = document.getElementById("list");
const sectorFilter = document.getElementById("sectorFilter");
const tierFilter = document.getElementById("tierFilter");
const typeFilter = document.getElementById("typeFilter");

let all = [];

function render() {
  const sector = sectorFilter.value;
  const tier = tierFilter.value;
  const type = typeFilter.value;
  const filtered = all.filter(s =>
    (!sector || s.sector === sector) &&
    (!tier || s.risk_tier === tier) &&
    (!type || s.investment_type === type)
  );

  if (filtered.length === 0) {
    listEl.innerHTML = `<p class="muted">Asnjë NVM nuk përputhet me këto filtra.</p>`;
    return;
  }

  listEl.innerHTML = filtered.map(s => `
    <a class="sme-card" href="/sme.html?id=${encodeURIComponent(s.id)}">
      <h3>${esc(s.name)}</h3>
      <div class="sme-meta">${esc(sectorLabel(s.sector))} · ${esc(s.city)} · themeluar ${esc(s.founded_year)} · ${esc(s.employees)} punonjës</div>
      <div class="sme-desc">Kërkon ${fmtMoney(s.funding_goal)} kapital nga diaspora.</div>
      <div class="sme-card-footer">
        ${investmentTypeBadge(s.investment_type)}
        ${s.expected_return_pct != null ? `<span class="muted">~${s.expected_return_pct.toFixed(0)}%/vit</span>` : ""}
      </div>
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
    sectorFilter.innerHTML = `<option value="">Të gjithë sektorët</option>` +
      sectors.map(s => `<option value="${esc(s)}">${esc(sectorLabel(s))}</option>`).join("");
    render();
  } catch (e) {
    listEl.innerHTML = `<div class="notice notice-error">Nuk u ngarkuan dot NVM-të: ${esc(trErr(e))}</div>`;
  }
}

sectorFilter.addEventListener("change", render);
tierFilter.addEventListener("change", render);
typeFilter.addEventListener("change", render);
load();
