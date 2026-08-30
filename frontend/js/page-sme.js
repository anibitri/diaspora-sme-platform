mountNav("market");

const params = new URLSearchParams(location.search);
const smeId = params.get("id");
const contentEl = document.getElementById("content");

function filingsTable(filings) {
  if (!filings.length) return `<p class="muted">Asnjë bilanc i regjistruar.</p>`;
  const rows = filings.map(f => `
    <tr>
      <td>${esc(f.year)}</td>
      <td class="num">${fmtMoney(f.revenue)}</td>
      <td class="num">${fmtMoney(f.net_income)}</td>
      <td class="num">${fmtMoney(f.current_assets)}</td>
      <td class="num">${fmtMoney(f.current_liabilities)}</td>
      <td class="num">${fmtMoney(f.total_liabilities)}</td>
      <td class="num">${fmtMoney(f.equity)}</td>
      <td>${fmtDate(f.filed_date)}${f.is_late ? ' <span class="status-pill">e vonuar</span>' : ""}</td>
    </tr>`).join("");
  return `
    <table>
      <thead><tr>
        <th>Viti</th><th class="num">Të ardhura</th><th class="num">Fitimi neto</th>
        <th class="num">Aktive korrente</th><th class="num">Detyrime korrente</th>
        <th class="num">Detyrime gjithsej</th><th class="num">Kapitali</th><th>Depozituar</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function contactCard(sme) {
  const hasAny = sme.contact_name || sme.contact_email || sme.contact_phone || sme.website;
  if (!hasAny) return "";
  const rows = [];
  if (sme.contact_name) rows.push(`<div><span class="muted">Kontakti</span><br>${esc(sme.contact_name)}</div>`);
  if (sme.contact_email) rows.push(`<div><span class="muted">Email</span><br><a href="mailto:${esc(sme.contact_email)}">${esc(sme.contact_email)}</a></div>`);
  if (sme.contact_phone) rows.push(`<div><span class="muted">Telefon</span><br><a href="tel:${esc(sme.contact_phone.replace(/\s+/g, ""))}">${esc(sme.contact_phone)}</a></div>`);
  if (sme.website) rows.push(`<div><span class="muted">Website</span><br><a href="${escUrl(sme.website)}" target="_blank" rel="noopener noreferrer">${esc(sme.website)}</a></div>`);
  return `
    <div class="card section-gap">
      <h2>Kontakti &amp; lidhjet</h2>
      <div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(180px,1fr))">${rows.join("")}</div>
    </div>`;
}

function gradingExplainer() {
  return `
    <div class="grading-explainer section-gap">
      <h3>Si funksionon ky vlerësim</h3>
      <p>Vlerësimi kompozit shkon nga <strong>0 deri në 100 pikë</strong>, ndërtuar nga katër
      komponentë financiarë, secili deri në 25 pikë (shiko ndarjen më poshtë). Nivelet e
      rrezikut janë:</p>
      <ul class="tier-legend">
        <li><span class="badge badge-low"><span class="dot"></span>Rrezik i ulët</span><span class="muted">70–100 pikë</span></li>
        <li><span class="badge badge-medium"><span class="dot"></span>Rrezik mesatar</span><span class="muted">40–69 pikë</span></li>
        <li><span class="badge badge-high"><span class="dot"></span>Rrezik i lartë</span><span class="muted">0–39 pikë</span></li>
      </ul>
      <p class="muted">Vlerësimi bazohet në bilancet e biznesit (të marra nga QKB gjatë
      regjistrimit) dhe nuk zëvendëson një audit të pavarur.</p>
    </div>`;
}

function scorePanel(rs) {
  if (!rs || rs.unavailable) {
    return `<div class="notice notice-warning">Vlerësimi nuk është i disponueshëm${rs && rs.reason ? " (" + esc(rs.reason) + ")" : ""}. Ky biznes nuk ka ende bilance të përdorshme.</div>`;
  }
  const staleNotice = rs.stale
    ? `<div class="notice notice-warning">Ky vlerësim bazohet në një bilanc nga ${esc(rs.based_on_filing_year)}, më shumë se 2 vjet i vjetër. Trajtoje si potencialisht të vjetëruar.</div>`
    : "";
  return `
    <div class="score-tile">
      <div class="value">${rs.score.toFixed(0)}<small>/100</small></div>
      ${tierBadge(rs.tier, false, rs.stale)}
    </div>
    ${staleNotice}
    <h3 class="section-gap">Ndarja e vlerësimit</h3>
    <div id="riskChart"></div>
    <p class="muted section-gap">Bazuar në bilancin e vitit ${esc(rs.based_on_filing_year)}. Llogaritur më ${fmtDate(rs.computed_at)}.</p>

    <h3 class="section-gap">Përse ky vlerësim — shënime për komponentët</h3>
    <p class="muted">${esc(rs.notes.liquidity || "")}</p>
    <p class="muted">${esc(rs.notes.leverage || "")}</p>
    <p class="muted">${esc(rs.notes.profitability || "")}</p>
    <p class="muted">${esc(rs.notes.benford || "")}</p>

    ${rs.notes.benford_distribution ? `<h3 class="section-gap">Ligji i Benford-it: shifra e parë e vërejtur kundrejt asaj të pritur</h3><div id="benfordChart"></div>` : ""}

    <p class="muted section-gap">Ky vlerësim është një tregues i bazuar në të dhëna, jo një
    garanci. Ndërtohet nga bilance të vetëdeklaruara dhe një kontroll anomalie me kosto të ulët,
    jo nga llogari të audituara apo të dhëna nga byro krediti.</p>

    ${gradingExplainer()}
  `;
}

function returnPreviewHtml(amount, pct) {
  const projected = amount * (1 + pct / 100);
  return `
    <div class="return-preview">
      <div class="return-figure">${fmtMoney(projected)}</div>
      <p>Vlerë e projektuar pas 1 viti, me një kthim ilustrues prej ~${pct.toFixed(0)}%/vit për këtë lloj
      investimi dhe nivel rreziku. Nuk është një garanci — shiko shënimin më poshtë.</p>
    </div>`;
}

function investPanel(sme) {
  const investor = getInvestorProfile();
  if (sme.status !== "vetted") {
    return `<div class="notice notice-warning">Ky biznes nuk është aktualisht i hapur për investime (statusi: ${esc(statusLabel(sme.status))}).</div>`;
  }
  if (!investor) {
    return `<div class="notice notice-warning">
      <a href="/investor.html">Hyr ose krijo një profil investitori</a> për të simuluar një investim në ${esc(sme.name)}.
    </div>`;
  }
  const pct = sme.expected_return_pct != null ? sme.expected_return_pct : 0;
  return `
    <div id="investResult"></div>
    <label for="amount">Shuma e investimit (EUR)</label>
    <input id="amount" type="number" min="25" step="5" value="100" />
    <p class="muted">Minimumi EUR 25. Duke investuar si <strong>${esc(investor.name)}</strong> (${esc(investor.email)}).</p>
    <div id="returnPreview">${returnPreviewHtml(100, pct)}</div>
    <p class="muted" style="font-size:11.5px">Kthimi ilustrues bazohet në llojin e investimit (${esc(investmentTypeLabel(sme.investment_type))})
    dhe nivelin e rrezikut të biznesit — jo në një model real vlerësimi tregu.</p>
    <button class="primary" id="investBtn" style="margin-top:8px">Simulo investimin</button>
  `;
}

async function load() {
  try {
    const sme = await api.getSme(smeId);
    contentEl.innerHTML = `
      <a href="/marketplace.html" class="muted">&larr; Kthehu te tregu</a>
      <h1 class="section-gap">${esc(sme.name)}</h1>
      <p class="sme-meta">${esc(sectorLabel(sme.sector))} · ${esc(sme.city)} · themeluar ${esc(sme.founded_year)} · ${esc(sme.employees)} punonjës
        · NIPT ${esc(sme.nipt)} · <span class="status-pill">${esc(statusLabel(sme.status))}</span></p>
      <p>${esc(sme.description)}</p>
      <p><strong>Kërkon:</strong> ${fmtMoney(sme.funding_goal)} &nbsp; ${investmentTypeBadge(sme.investment_type)}
        ${sme.expected_return_pct != null ? `<span class="muted">kthim ilustrues ~${sme.expected_return_pct.toFixed(0)}%/vit</span>` : ""}</p>

      <div class="two-col section-gap">
        <div>
          <div class="card">
            <h2>Historiku i bilanceve</h2>
            ${filingsTable(sme.filings)}
          </div>
          ${contactCard(sme)}
          <div class="card section-gap">
            <h2>Simulo një investim</h2>
            <div id="investPanel">${investPanel(sme)}</div>
          </div>
        </div>
        <div class="card">
          <h2>Vlerësimi i rrezikut</h2>
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
      const amountInput = document.getElementById("amount");
      const previewEl = document.getElementById("returnPreview");
      const pct = sme.expected_return_pct != null ? sme.expected_return_pct : 0;
      amountInput.addEventListener("input", () => {
        const amt = parseFloat(amountInput.value);
        previewEl.innerHTML = returnPreviewHtml(Number.isFinite(amt) ? amt : 0, pct);
      });

      investBtn.addEventListener("click", async () => {
        const amount = parseFloat(amountInput.value);
        const resultEl = document.getElementById("investResult");
        investBtn.disabled = true;
        try {
          const inv = await api.createInvestment({ sme_id: sme.id, amount, currency: "EUR" }, uuid());
          resultEl.innerHTML = `<div class="notice notice-success">U angazhuan ${fmtMoney(inv.amount)} për ${esc(sme.name)}
            (${esc(investmentTypeLabel(inv.investment_type))}). Vlerë e projektuar pas 1 viti: <strong>${fmtMoney(inv.projected_value_1y)}</strong>
            (~${inv.expected_return_pct.toFixed(0)}%/vit, ilustrues). Shikoje te <a href="/investor.html">portofoli yt</a>.</div>`;
        } catch (e) {
          resultEl.innerHTML = `<div class="notice notice-error">${esc(trErr(e))}</div>`;
        } finally {
          investBtn.disabled = false;
        }
      });
    }
  } catch (e) {
    contentEl.innerHTML = `<div class="notice notice-error">Nuk u ngarkua dot ky biznes: ${esc(trErr(e))}</div>`;
  }
}

load();
