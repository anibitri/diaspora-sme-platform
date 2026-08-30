mountNav("investor");
const contentEl = document.getElementById("content");

function authForm(mode) {
  const isSignup = mode === "signup";
  return `
    <div class="two-col">
      <div>
        <h1>${isSignup ? "Create your investor profile" : "Welcome back"}</h1>
        <p class="lede">
          DiasporaInvest lets you put small amounts of capital directly behind vetted Albanian
          SMEs, with a transparent, filing-based risk score for every listing.
        </p>
        <ul class="lede">
          <li>Every listing is vetted before it appears in the marketplace.</li>
          <li>Risk scores show their full breakdown — never a black-box number.</li>
          <li>This prototype simulates transactions; no real funds move.</li>
        </ul>
      </div>
      <div class="card">
        <div id="formError"></div>
        <form id="authForm">
          ${isSignup ? `
            <label for="name">Full name</label>
            <input id="name" required placeholder="Elira Hoxha" />
          ` : ""}
          <label for="email">Email</label>
          <input id="email" type="email" required placeholder="you@example.com" />
          ${isSignup ? `
            <label for="country">Country of residence</label>
            <input id="country" required placeholder="United Kingdom" />
          ` : ""}
          <label for="password">Password</label>
          <input id="password" type="password" required minlength="${isSignup ? 8 : 1}"
            placeholder="${isSignup ? "At least 8 characters" : "Your password"}" />
          <button class="primary" type="submit" style="margin-top:14px">${isSignup ? "Create profile" : "Log in"}</button>
        </form>
        <p class="muted section-gap">
          ${isSignup ? "Already have a profile?" : "New here?"}
          <a href="#" id="toggleMode">${isSignup ? "Log in" : "Create one"}</a>
        </p>
        ${!isSignup ? `<p class="muted">Demo account: elira.demo@example.com / demo1234</p>` : ""}
      </div>
    </div>
  `;
}

function portfolioView(portfolio) {
  const { investor, investments, total_committed } = portfolio;
  const rows = investments.length
    ? investments.map(i => `
      <tr>
        <td><a href="/sme.html?id=${encodeURIComponent(i.sme_id)}">${esc(i.sme_name)}</a></td>
        <td class="num">${fmtMoney(i.amount, i.currency)}</td>
        <td><span class="status-pill">${esc(i.status)}</span></td>
        <td>${fmtDate(i.created_at)}</td>
      </tr>`).join("")
    : `<tr><td colspan="4" class="muted">No investments yet — browse the <a href="/index.html">marketplace</a>.</td></tr>`;

  return `
    <h1>Welcome, ${esc(investor.name)}</h1>
    <p class="muted">${esc(investor.email)} · ${esc(investor.country_of_residence)}</p>
    <div class="card section-gap">
      <h3>Total committed (simulated)</h3>
      <div class="score-tile"><div class="value">${fmtMoney(total_committed)}</div></div>
    </div>
    <div class="card section-gap">
      <h2>My investments</h2>
      <table>
        <thead><tr><th>SME</th><th class="num">Amount</th><th>Status</th><th>Date</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <button id="logoutBtn" style="margin-top:16px">Log out</button>
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
      contentEl.innerHTML = `<div class="notice notice-error">Could not load portfolio: ${esc(e.message)}</div>`;
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
      errEl.innerHTML = `<div class="notice notice-error">${esc(e.message)}</div>`;
    }
  });
}

function render(mode) {
  if (mode === "portfolio" || (mode === undefined && getInvestorProfile())) {
    contentEl.innerHTML = `<div class="spinner-text">Loading…</div>`;
    showPortfolio();
    return;
  }
  const m = mode === "login" ? "login" : "signup";
  contentEl.innerHTML = authForm(m);
  attachFormHandler(m);
}

render();
