mountNav("investor");
const contentEl = document.getElementById("content");

function authForm(mode) {
  const isSignup = mode === "signup";
  return `
    <div class="two-col">
      <div>
        <h1>${isSignup ? "Krijo profilin tënd si investitor" : "Mirë se erdhe përsëri"}</h1>
        <p class="lede">
          Urë të lejon të vësh shuma të vogla kapitali direkt pas NVM-ve shqiptare të
          vlerësuara, me një vlerësim rreziku transparent për çdo listim.
        </p>
        <ul class="lede">
          <li>Çdo listim kalon vetim përpara se të shfaqet në treg.</li>
          <li>Vlerësimet e rrezikut tregojnë ndarjen e plotë — kurrë një numër i mbyllur.</li>
          <li>Ky prototip simulon transaksionet; asnjë fond real nuk lëviz.</li>
        </ul>
      </div>
      <div class="card">
        <div id="formError"></div>
        <form id="authForm">
          ${isSignup ? `
            <label for="name">Emri i plotë</label>
            <input id="name" required placeholder="Elira Hoxha" />
          ` : ""}
          <label for="email">Email</label>
          <input id="email" type="email" required placeholder="ti@shembull.com" />
          ${isSignup ? `
            <label for="country">Vendi i banimit</label>
            <input id="country" required placeholder="Mbretëria e Bashkuar" />
          ` : ""}
          <label for="password">Fjalëkalimi</label>
          <input id="password" type="password" required minlength="${isSignup ? 8 : 1}"
            placeholder="${isSignup ? "Të paktën 8 karaktere" : "Fjalëkalimi yt"}" />
          <button class="primary" type="submit" style="margin-top:14px">${isSignup ? "Krijo profilin" : "Hyr"}</button>
        </form>
        <p class="muted section-gap">
          ${isSignup ? "Ke tashmë një profil?" : "I ri këtu?"}
          <a href="#" id="toggleMode">${isSignup ? "Hyr" : "Krijo një profil"}</a>
        </p>
        ${!isSignup ? `<p class="muted">Llogari demo: elira.demo@example.com / demo1234</p>` : ""}
      </div>
    </div>
  `;
}

function portfolioView(portfolio) {
  const { investor, investments, total_committed } = portfolio;
  const totalProjected = investments.reduce((sum, i) => sum + i.amount * (1 + i.expected_return_pct / 100), 0);
  const rows = investments.length
    ? investments.map(i => `
      <tr>
        <td><a href="/sme.html?id=${encodeURIComponent(i.sme_id)}">${esc(i.sme_name)}</a></td>
        <td>${investmentTypeBadge(i.investment_type)}</td>
        <td class="num">${fmtMoney(i.amount, i.currency)}</td>
        <td class="num">${fmtMoney(i.projected_value_1y, i.currency)} <span class="muted">(~${i.expected_return_pct.toFixed(0)}%)</span></td>
        <td><span class="status-pill">${esc(statusLabel(i.status))}</span></td>
        <td>${fmtDate(i.created_at)}</td>
      </tr>`).join("")
    : `<tr><td colspan="6" class="muted">Ende pa investime — shfleto <a href="/marketplace.html">tregun</a>.</td></tr>`;

  return `
    <h1>Mirë se erdhe, ${esc(investor.name)}</h1>
    <p class="muted">${esc(investor.email)} · ${esc(investor.country_of_residence)}</p>
    <div class="two-col section-gap">
      <div class="card">
        <h3>Totali i angazhuar (i simuluar)</h3>
        <div class="score-tile"><div class="value">${fmtMoney(total_committed)}</div></div>
      </div>
      <div class="card">
        <h3>Vlerë e projektuar pas 1 viti (ilustrues)</h3>
        <div class="score-tile"><div class="value">${fmtMoney(totalProjected)}</div></div>
      </div>
    </div>
    <div class="card section-gap">
      <h2>Investimet e mia</h2>
      <table>
        <thead><tr><th>NVM</th><th>Lloji</th><th class="num">Shuma</th><th class="num">Pas 1 viti</th><th>Statusi</th><th>Data</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="muted section-gap" style="font-size:11.5px">Vlerat e projektuara janë ilustrative, bazuar në llojin e investimit dhe
      nivelin e rrezikut në kohën e angazhimit — jo një garanci kthimi.</p>
    </div>
    <button id="logoutBtn" style="margin-top:16px">Dil</button>
  `;
}

async function showPortfolio() {
  try {
    const portfolio = await api.getPortfolio();
    contentEl.innerHTML = portfolioView(portfolio);
    document.getElementById("logoutBtn").addEventListener("click", () => {
      clearInvestorSession();
      render("login");
    });
  } catch (e) {
    if (e.status === 401) {
      clearInvestorSession();
      render("login");
    } else {
      contentEl.innerHTML = `<div class="notice notice-error">Nuk u ngarkua dot portofoli: ${esc(trErr(e))}</div>`;
    }
  }
}

function attachFormHandler(mode) {
  document.getElementById("toggleMode").addEventListener("click", (ev) => {
    ev.preventDefault();
    render(mode === "signup" ? "login" : "signup");
  });

  document.getElementById("authForm").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const errEl = document.getElementById("formError");
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    try {
      let result;
      if (mode === "signup") {
        const name = document.getElementById("name").value.trim();
        const country = document.getElementById("country").value.trim();
        result = await api.investorSignup({ name, email, country_of_residence: country, password });
      } else {
        result = await api.investorLogin({ email, password });
      }
      setInvestorSession(result.token, result.investor);
      render("portfolio");
    } catch (e) {
      errEl.innerHTML = `<div class="notice notice-error">${esc(trErr(e))}</div>`;
    }
  });
}

function render(mode) {
  if (mode === "portfolio" || (mode === undefined && getInvestorProfile())) {
    contentEl.innerHTML = `<div class="spinner-text">Duke ngarkuar…</div>`;
    showPortfolio();
    return;
  }
  const m = mode === "login" ? "login" : "signup";
  contentEl.innerHTML = authForm(m);
  attachFormHandler(m);
}

render();
