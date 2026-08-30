mountNav("sme");
const contentEl = document.getElementById("content");

const SECTORS = ["Tourism & Hospitality", "Agro-processing", "Manufacturing", "IT Services", "Retail & Trade"];
const THIS_YEAR = new Date().getFullYear();

function signupForm() {
  return `
    <h1>List your business</h1>
    <p class="lede">
      Submit your business for vetting. An admin reviews every submission before it appears
      in the investor-facing marketplace (thesis §5: SME onboarding &amp; vetting).
      This is a research prototype — no real funds or legal filings are involved.
    </p>
    <div class="card" style="max-width:640px">
      <div id="formError"></div>
      <form id="signupForm">
        <h3>Business</h3>
        <label for="name">Business name</label>
        <input id="name" required maxlength="200" />
        <div class="field-row">
          <div>
            <label for="sector">Sector</label>
            <select id="sector">${SECTORS.map(s => `<option>${esc(s)}</option>`).join("")}</select>
          </div>
          <div>
            <label for="city">City</label>
            <input id="city" required maxlength="100" placeholder="Tirana" />
          </div>
        </div>
        <div class="field-row">
          <div>
            <label for="founded_year">Founded year</label>
            <input id="founded_year" type="number" required min="1900" max="${THIS_YEAR}" value="${THIS_YEAR - 5}" />
          </div>
          <div>
            <label for="employees">Employees</label>
            <input id="employees" type="number" required min="0" value="10" />
          </div>
        </div>
        <label for="funding_goal">Funding goal (EUR)</label>
        <input id="funding_goal" type="number" required min="1" value="30000" />
        <label for="description">Description</label>
        <textarea id="description" rows="3" maxlength="2000" placeholder="What does the business do, and what would this capital be used for?"></textarea>

        <h3 class="section-gap">Contact &amp; links</h3>
        <div class="field-row">
          <div>
            <label for="contact_name">Contact person</label>
            <input id="contact_name" required maxlength="200" />
          </div>
          <div>
            <label for="contact_phone">Phone</label>
            <input id="contact_phone" maxlength="50" placeholder="+355 69 000 0000" />
          </div>
        </div>
        <label for="contact_email">Contact email (also your login)</label>
        <input id="contact_email" type="email" required maxlength="200" />
        <label for="website">Website (optional)</label>
        <input id="website" maxlength="300" placeholder="www.yourbusiness.al" />

        <h3 class="section-gap">Most recent annual filing</h3>
        <p class="muted">Total assets is calculated automatically as total liabilities + equity, so the
          balance sheet you submit always balances.</p>
        <div class="field-row">
          <div>
            <label for="filing_year">Filing year</label>
            <input id="filing_year" type="number" required min="1900" max="${THIS_YEAR}" value="${THIS_YEAR - 1}" />
          </div>
          <div>
            <label for="revenue">Revenue (EUR)</label>
            <input id="revenue" type="number" required min="0" step="any" value="150000" />
          </div>
        </div>
        <div class="field-row">
          <div>
            <label for="cogs">Cost of goods sold (EUR)</label>
            <input id="cogs" type="number" required min="0" step="any" value="90000" />
          </div>
          <div>
            <label for="net_income">Net income (EUR, negative if a loss)</label>
            <input id="net_income" type="number" required step="any" value="12000" />
          </div>
        </div>
        <div class="field-row">
          <div>
            <label for="current_assets">Current assets (EUR)</label>
            <input id="current_assets" type="number" required min="0" step="any" value="40000" />
          </div>
          <div>
            <label for="current_liabilities">Current liabilities (EUR)</label>
            <input id="current_liabilities" type="number" required min="0" step="any" value="30000" />
          </div>
        </div>
        <div class="field-row">
          <div>
            <label for="total_liabilities">Total liabilities (EUR)</label>
            <input id="total_liabilities" type="number" required min="0" step="any" value="60000" />
          </div>
          <div>
            <label for="equity">Equity (EUR, negative if a deficit)</label>
            <input id="equity" type="number" required step="any" value="70000" />
          </div>
        </div>

        <h3 class="section-gap">Account</h3>
        <label for="password">Password</label>
        <input id="password" type="password" required minlength="8" placeholder="At least 8 characters" />

        <button class="primary" type="submit" style="margin-top:16px">Submit for vetting</button>
      </form>
      <p class="muted section-gap">Already registered? <a href="#" id="toggleLogin">Log in</a></p>
    </div>
  `;
}

function loginForm() {
  return `
    <h1>Business login</h1>
    <p class="lede">Log in to see your listing's vetting status.</p>
    <div class="card" style="max-width:420px">
      <div id="formError"></div>
      <form id="loginForm">
        <label for="email">Contact email</label>
        <input id="email" type="email" required />
        <label for="password">Password</label>
        <input id="password" type="password" required />
        <button class="primary" type="submit" style="margin-top:14px">Log in</button>
      </form>
      <p class="muted section-gap">New business? <a href="#" id="toggleSignup">List your business</a></p>
    </div>
  `;
}

function statusView(sme) {
  const statusCopy = {
    pending: "Your listing has been submitted and is awaiting admin review.",
    vetted: "Your listing is live in the investor marketplace.",
    rejected: "Your listing was not approved for the marketplace.",
    delisted: "Your listing has been delisted and is no longer visible to investors.",
  };
  return `
    <h1>${esc(sme.name)}</h1>
    <p><span class="status-pill">${esc(sme.status)}</span></p>
    <p class="lede">${esc(statusCopy[sme.status] || "")}</p>
    <div class="card section-gap">
      <h2>Your risk score</h2>
      ${sme.risk_score && !sme.risk_score.unavailable
        ? `<div class="score-tile"><div class="value">${sme.risk_score.score.toFixed(0)}<small>/100</small></div>${tierBadge(sme.risk_score.tier, false, sme.risk_score.stale)}</div>
           <p class="muted section-gap">Full breakdown is visible to investors on your public listing once vetted. See it yourself at <a href="/sme.html?id=${encodeURIComponent(sme.id)}">your listing page</a>.</p>`
        : `<p class="muted">Not yet scored — add at least one filing for a score to appear.</p>`}
    </div>
    <button id="logoutBtn" style="margin-top:16px">Log out</button>
  `;
}

async function showStatus() {
  try {
    const sme = await api.getMySme();
    setSmeSession(localStorage.getItem(SME_TOKEN_KEY), sme);
    contentEl.innerHTML = statusView(sme);
    document.getElementById("logoutBtn").addEventListener("click", () => {
      clearSmeSession();
      render("signup");
    });
  } catch (e) {
    if (e.status === 401) {
      clearSmeSession();
      render("login");
    } else {
      contentEl.innerHTML = `<div class="notice notice-error">Could not load your listing: ${esc(e.message)}</div>`;
    }
  }
}

function attachSignupHandler() {
  document.getElementById("toggleLogin").addEventListener("click", (ev) => { ev.preventDefault(); render("login"); });
  document.getElementById("signupForm").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const errEl = document.getElementById("formError");
    const val = (id) => document.getElementById(id).value;
    const num = (id) => parseFloat(document.getElementById(id).value);
    const payload = {
      name: val("name"), sector: val("sector"), city: val("city"),
      description: val("description"),
      founded_year: parseInt(val("founded_year"), 10), employees: parseInt(val("employees"), 10),
      funding_goal: num("funding_goal"),
      contact_name: val("contact_name"), contact_email: val("contact_email"),
      contact_phone: val("contact_phone"), website: val("website"),
      password: val("password"),
      filing_year: parseInt(val("filing_year"), 10),
      revenue: num("revenue"), cogs: num("cogs"), net_income: num("net_income"),
      current_assets: num("current_assets"), current_liabilities: num("current_liabilities"),
      total_liabilities: num("total_liabilities"), equity: num("equity"),
    };
    try {
      const result = await api.smeSignup(payload);
      setSmeSession(result.token, result.sme);
      render("status");
    } catch (e) {
      errEl.innerHTML = `<div class="notice notice-error">${esc(e.message)}</div>`;
    }
  });
}

function attachLoginHandler() {
  document.getElementById("toggleSignup").addEventListener("click", (ev) => { ev.preventDefault(); render("signup"); });
  document.getElementById("loginForm").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const errEl = document.getElementById("formError");
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    try {
      const result = await api.smeLogin({ email, password });
      setSmeSession(result.token, result.sme);
      render("status");
    } catch (e) {
      errEl.innerHTML = `<div class="notice notice-error">${esc(e.message)}</div>`;
    }
  });
}

function render(mode) {
  if (mode === "status" || (mode === undefined && getSmeProfile())) {
    contentEl.innerHTML = `<div class="spinner-text">Loading…</div>`;
    showStatus();
    return;
  }
  if (mode === "login") {
    contentEl.innerHTML = loginForm();
    attachLoginHandler();
    return;
  }
  contentEl.innerHTML = signupForm();
  attachSignupHandler();
}

render();
