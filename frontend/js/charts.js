// Small, dependency-free charts for the risk-score explainability panel.
// Each sub-score is 0-25; the composite is their sum out of 100.

function renderRiskBreakdown(container, rs) {
  const rows = [
    ["Likuiditeti", rs.liquidity_score],
    ["Leva financiare", rs.leverage_score],
    ["Përfitueshmëria", rs.profitability_score],
    ["Kontrolli Benford", rs.benford_score],
  ];
  const bars = rows
    .map(([label, value]) => {
      const pct = value == null ? 0 : Math.round((value / 25) * 100);
      return `
      <div class="risk-bar-row">
        <div class="risk-bar-label">${label}</div>
        <div class="risk-bar-track"><div class="risk-bar-fill" style="width:${pct}%"></div></div>
        <div class="risk-bar-value">${value == null ? "-" : value.toFixed(0)}/25</div>
      </div>`;
    })
    .join("");
  container.innerHTML = `<div class="risk-chart">${bars}</div>`;
}

function renderBenfordChart(container, distribution) {
  if (!distribution) {
    container.innerHTML = "";
    return;
  }
  const max = Math.max(...distribution.observed, ...distribution.expected) * 1.15;
  const groups = distribution.digits
    .map((d, i) => {
      const obs = distribution.observed[i];
      const exp = distribution.expected[i];
      const obsH = Math.round((obs / max) * 100);
      const expH = Math.round((exp / max) * 100);
      return `
      <div class="benford-group">
        <div class="benford-bar observed" style="height:${obsH}%" title="Vërejtur: ${(obs * 100).toFixed(1)}%"></div>
        <div class="benford-bar expected" style="height:${expH}%" title="Pritur (Benford): ${(exp * 100).toFixed(1)}%"></div>
        <div class="benford-digit-label">${d}</div>
      </div>`;
    })
    .join("");

  container.innerHTML = `
    <div class="benford-chart-wrap">
      <div class="benford-chart">${groups}</div>
    </div>
    <div class="legend">
      <div class="legend-item"><span class="legend-swatch" style="background:var(--series-1)"></span>Vërejtur (bilancet e këtij biznesi)</div>
      <div class="legend-item"><span class="legend-swatch" style="background:var(--series-2)"></span>Pritur (Ligji i Benford-it)</div>
    </div>
    <p class="muted section-gap">Shpërndarja e shifrës së parë në ${distribution.n} shifra të grupuara nga bilancet. MAD=${distribution.mad} (${distribution.level}).</p>
  `;
}
