mountNav("market");

const params = new URLSearchParams(location.search);
const smeId = params.get("id");
const contentEl = document.getElementById("content");

function filingsTable(filings) {
  if (!filings.length) return `<p class="muted">No filings on record.</p>`;
  const rows = filings.map(f => `
    <tr>
      <td>${esc(f.year)}</td>
      <td class="num">${fmtMoney(f.revenue)}</td>
      <td class="num">${fmtMoney(f.net_income)}</td>
      <td class="num">${fmtMoney(f.current_assets)}</td>
      <td class="num">${fmtMoney(f.current_liabilities)}</td>
      <td class="num">${fmtMoney(f.total_liabilities)}</td>
      <td class="num">${fmtMoney(f.equity)}</td>
      <td>${fmtDate(f.filed_date)}${f.is_late ? ' <span class="status-pill">late</span>' : ""}</td>
    </tr>`).join("");
  return `
    <table>
      <thead><tr>
        <th>Year</th><th class="num">Revenue</th><th class="num">Net income</th>
        <th class="num">Current assets</th><th class="num">Current liab.</th>
        <th class="num">Total liab.</th><th class="num">Equity</th><th>Filed</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function contactCard(sme) {
  const hasAny = sme.contact_name || sme.contact_email || sme.contact_phone || sme.website;
  if (!hasAny) return "";
  const rows = [];
  if (sme.contact_name) rows.push(`<div><span class="muted">Contact</span><br>${esc(sme.contact_name)}</div>`);
  if (sme.contact_email) rows.push(`<div><span class="muted">Email</span><br><a href="mailto:${esc(sme.contact_email)}">${esc(sme.contact_email)}</a></div>`);
  if (sme.contact_phone) rows.push(`<div><span class="muted">Phone</span><br><a href="tel:${esc(sme.contact_phone.replace(/\s+/g, ""))}">${esc(sme.contact_phone)}</a></div>`);
  if (sme.website) rows.push(`<div><span class="muted">Website</span><br><a href="${escUrl(sme.website)}" target="_blank" rel="noopener noreferrer">${esc(sme.website)}</a></div>`);
  return `
    <div class="card section-gap">
      <h2>Contact &amp; links</h2>
      <div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(180px,1fr))">${rows.join("")}</div>
    </div>`;
}

function scorePanel(rs) {
  if (!rs || rs.unavailable) {
    return `<div class="notice notice-warning">Risk score unavailable${rs && rs.reason ? " (" + esc(rs.reason) + ")" : ""}. This SME has no usable filing data yet.</div>`;
  }
  const staleNotice = rs.stale
    ? `<div class="notice notice-warning">This score is based on a filing from ${esc(rs.based_on_filing_year)}, more than 2 years old. Treat it as potentially outdated.</div>`
    : "";
  return `
    <div class="score-tile">
      <div class="value">${rs.score.toFixed(0)}<small>/100</small></div>
      ${tierBadge(rs.tier, false, rs.stale)}
    </div>
    ${staleNotice}
    <h3 class="section-gap">Score breakdown</h3>
    <div id="riskChart"></div>
    <p class="muted section-gap">Based on filing year ${esc(rs.based_on_filing_year)}. Computed ${fmtDate(rs.computed_at)}.</p>

    <h3 class="section-gap">Why this score — component notes</h3>
    <p class="muted">${esc(rs.notes.liquidity || "")}</p>
    <p class="muted">${esc(rs.notes.leverage || "")}</p>
    <p class="muted">${esc(rs.notes.profitability || "")}</p>
    <p class="muted">${esc(rs.notes.benford || "")}</p>

    ${rs.notes.benford_distribution ? `<h3 class="section-gap">Benford's Law: observed vs. expected first digit</h3><div id="benfordChart"></div>` : ""}

    <p class="muted section-gap">This score is a data-driven indicator, not a guarantee. It is built from
    self-reported filings and a low-cost anomaly check, not audited accounts or credit-bureau data.</p>
  `;
}

function investPanel(sme) {
  const investor = getInvestorProfile();
  if (sme.status !== "vetted") {
    return `<div class="notice notice-warning">This SME is not currently open for investment (status: ${esc(sme.status)}).</div>`;
  }
  if (!investor) {
    return `<div class="notice notice-warning">
      <a href="/investor.html">Log in or create an investor profile</a> to simulate an investment in ${esc(sme.name)}.
    </div>`;
  }
  return `
    <div id="investResult"></div>
    <label for="amount">Investment amount (EUR)</label>
    <input id="amount" type="number" min="25" step="5" value="100" />
    <p class="muted">Minimum EUR 25. Investing as <strong>${esc(investor.name)}</strong> (${esc(investor.email)}).</p>
    <button class="primary" id="investBtn" style="margin-top:8px">Simulate investment</button>
  `;
}

async function load() {
  try {
    const sme = await api.getSme(smeId);
    contentEl.innerHTML = `
      <a href="/index.html" class="muted">&larr; Back to marketplace</a>
      <h1 class="section-gap">${esc(sme.name)}</h1>
      <p class="sme-meta">${esc(sme.sector)} · ${esc(sme.city)} · founded ${esc(sme.founded_year)} · ${esc(sme.employees)} employees
        · <span class="status-pill">${esc(sme.status)}</span></p>
      <p>${esc(sme.description)}</p>
      <p><strong>Seeking:</strong> ${fmtMoney(sme.funding_goal)}</p>

      <div class="two-col section-gap">
        <div>
          <div class="card">
            <h2>Filing history</h2>
            ${filingsTable(sme.filings)}
          </div>
          ${contactCard(sme)}
          <div class="card section-gap">
            <h2>Simulate an investment</h2>
            <div id="investPanel">${investPanel(sme)}</div>
          </div>
        </div>
        <div class="card">
          <h2>Risk score</h2>
          <div id="scorePanel">${scorePanel(sme.risk_score)}</div>
        </div>
      </div>
    `;

    if (sme.risk_score && !sme.risk_score.unavailable) {
      renderRiskBreakdown(document.getElementById("riskChart"), sme.risk_score);
      if (sme.risk_score.notes.benford_distribution) {
        renderBenfordChart(document.getElementById("benfordChart"), sme.risk_score.notes.benford_distribution);
      }
    }

    const investBtn = document.getElementById("investBtn");
    if (investBtn) {
      investBtn.addEventListener("click", async () => {
        const amount = parseFloat(document.getElementById("amount").value);
        const resultEl = document.getElementById("investResult");
        investBtn.disabled = true;
        try {
          const inv = await api.createInvestment({ sme_id: sme.id, amount, currency: "EUR" }, uuid());
          resultEl.innerHTML = `<div class="notice notice-success">Committed ${fmtMoney(inv.amount)} to ${esc(sme.name)}. View it in <a href="/investor.html">your portfolio</a>.</div>`;
        } catch (e) {
          resultEl.innerHTML = `<div class="notice notice-error">${esc(e.message)}</div>`;
        } finally {
          investBtn.disabled = false;
        }
      });
    }
  } catch (e) {
    contentEl.innerHTML = `<div class="notice notice-error">Could not load this SME: ${esc(e.message)}</div>`;
  }
}

load();
