mountNav("sme");
const contentEl = document.getElementById("content");

const SECTORS = ["Tourism & Hospitality", "Agro-processing", "Manufacturing", "IT Services", "Retail & Trade"];
const NIPT_RE = /^[A-Za-z][0-9]{8}[A-Za-z]$/;

// Filings pulled from the QKB lookup demo, populated once the business runs
// the lookup step below. Submission is blocked until this is set -- the
// whole point of the flow is that filing figures come from the (simulated)
// QKB pull, not typed by hand.
let qkbFilings = null;

function signupForm() {
  return `
    <h1>Regjistro biznesin</h1>
    <p class="lede">
      Dorëzo biznesin tënd për vetim. Një admin shqyrton çdo aplikim përpara se të shfaqet
      në tregun e investitorëve. Ky është një prototip kërkimor — asnjë fond real apo
      regjistrim ligjor nuk përfshihet.
    </p>
    <div class="card" style="max-width:680px">
      <div id="formError"></div>
      <form id="signupForm">
        <h3>Biznesi</h3>
        <label for="name">Emri i biznesit</label>
        <input id="name" required maxlength="200" />
        <div class="field-row">
          <div>
            <label for="nipt">NIPT</label>
            <input id="nipt" required maxlength="10" placeholder="L71926023W" style="text-transform:uppercase" />
          </div>
          <div>
            <label for="sector">Sektori</label>
            <select id="sector">${SECTORS.map(s => `<option value="${esc(s)}">${esc(sectorLabel(s))}</option>`).join("")}</select>
          </div>
        </div>
        <div class="field-row">
          <div>
            <label for="city">Qyteti</label>
            <input id="city" required maxlength="100" placeholder="Tiranë" />
          </div>
          <div>
            <label for="founded_year">Viti i themelimit</label>
            <input id="founded_year" type="number" required min="1900" max="${new Date().getFullYear()}" value="${new Date().getFullYear() - 5}" />
          </div>
        </div>
        <div class="field-row">
          <div>
            <label for="employees">Punonjës</label>
            <input id="employees" type="number" required min="0" value="10" />
          </div>
          <div>
            <label for="funding_goal">Qëllimi i financimit (EUR)</label>
            <input id="funding_goal" type="number" required min="1" value="30000" />
          </div>
        </div>
        <label for="investment_type">Lloji i investimit që ofron</label>
        <select id="investment_type">
          <option value="equity">Kapital (bashkëpronësi) — investitori merr një pjesë të pronësisë</option>
          <option value="debt">Hua me kthim fiks — investitori kthehet me interes</option>
          <option value="revenue_share">Ndarje të ardhurash — investitori merr një përqindje të të ardhurave</option>
        </select>
        <label for="description">Përshkrimi</label>
        <textarea id="description" rows="3" maxlength="2000" placeholder="Çfarë bën biznesi, dhe për çfarë do të përdorej ky kapital?"></textarea>

        <h3 class="section-gap">Kontakti &amp; lidhjet</h3>
        <div class="field-row">
          <div>
            <label for="contact_name">Personi i kontaktit</label>
            <input id="contact_name" required maxlength="200" />
          </div>
          <div>
            <label for="contact_phone">Telefoni</label>
            <input id="contact_phone" maxlength="50" placeholder="+355 69 000 0000" />
          </div>
        </div>
        <label for="contact_email">Email kontakti (edhe hyrja jote)</label>
        <input id="contact_email" type="email" required maxlength="200" />
        <label for="website">Website (opsionale)</label>
        <input id="website" maxlength="300" placeholder="www.biznesi-yt.al" />

        <h3 class="section-gap">Bilancet financiare (nga QKB)</h3>
        <div class="qkb-demo">
          <p class="qkb-demo-label">Demo: kërko në QKB</p>
          <p class="muted" style="margin:0 0 12px">
            Vendos NIPT-in më sipër, pastaj kliko butonin — platforma "tërheq" 4 vitet e fundit
            të bilanceve nga QKB dhe i shfaq të parsuara, në vend që t'i shtypësh me dorë. Ky
            është një demonstrim i simuluar (nuk ka lidhje reale me QKB) por çdo NIPT valid
            kthen gjithmonë të njëjtat shifra.
          </p>
          <button type="button" class="btn" id="qkbBtn">Kërko në QKB</button>
          <div id="qkbStatus" class="qkb-status"></div>
          <div id="qkbResult"></div>
        </div>

        <h3 class="section-gap">Llogaria</h3>
        <label for="password">Fjalëkalimi</label>
        <input id="password" type="password" required minlength="8" placeholder="Të paktën 8 karaktere" />

        <button class="primary" type="submit" id="submitBtn" style="margin-top:16px" disabled>Kërko në QKB më sipër për të vazhduar</button>
      </form>
      <p class="muted section-gap">Je regjistruar tashmë? <a href="#" id="toggleLogin">Hyr</a></p>
    </div>
  `;
}

function loginForm() {
  return `
    <h1>Hyrja e biznesit</h1>
    <p class="lede">Hyr për të parë statusin e vetimit të listimit tënd.</p>
    <div class="card" style="max-width:420px">
      <div id="formError"></div>
      <form id="loginForm">
        <label for="email">Email kontakti</label>
        <input id="email" type="email" required />
        <label for="password">Fjalëkalimi</label>
        <input id="password" type="password" required />
        <button class="primary" type="submit" style="margin-top:14px">Hyr</button>
      </form>
      <p class="muted section-gap">Biznes i ri? <a href="#" id="toggleSignup">Regjistro biznesin</a></p>
    </div>
  `;
}

function statusView(sme) {
  const statusCopy = {
    pending: "Listimi yt është dorëzuar dhe pret shqyrtimin e adminit.",
    vetted: "Listimi yt është aktiv në tregun e investitorëve.",
    rejected: "Listimi yt nuk u miratua për tregun.",
    delisted: "Listimi yt është hequr nga lista dhe nuk shfaqet më te investitorët.",
  };
  return `
    <h1>${esc(sme.name)}</h1>
    <p><span class="status-pill">${esc(statusLabel(sme.status))}</span> ${investmentTypeBadge(sme.investment_type)}</p>
    <p class="lede">${esc(statusCopy[sme.status] || "")}</p>
    <div class="card section-gap">
      <h2>Vlerësimi yt i rrezikut</h2>
      ${sme.risk_score && !sme.risk_score.unavailable
        ? `<div class="score-tile"><div class="value">${sme.risk_score.score.toFixed(0)}<small>/100</small></div>${tierBadge(sme.risk_score.tier, false, sme.risk_score.stale)}</div>
           <p class="muted section-gap">Ndarja e plotë është e dukshme për investitorët në listimin tënd publik pasi të vlerësohet. Shikoje vetë te <a href="/sme.html?id=${encodeURIComponent(sme.id)}">faqja jote e listimit</a>.</p>`
        : `<p class="muted">Ende pa u vlerësuar.</p>`}
    </div>
    <button id="logoutBtn" style="margin-top:16px">Dil</button>
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
      contentEl.innerHTML = `<div class="notice notice-error">Nuk u ngarkua dot listimi yt: ${esc(trErr(e))}</div>`;
    }
  }
}

function qkbResultTable(filings) {
  const rows = filings.map(f => `
    <tr>
      <td>${esc(f.year)}</td>
      <td class="num">${fmtMoney(f.revenue)}</td>
      <td class="num">${fmtMoney(f.net_income)}</td>
      <td class="num">${fmtMoney(f.current_assets)}</td>
      <td class="num">${fmtMoney(f.current_liabilities)}</td>
      <td class="num">${fmtMoney(f.total_liabilities)}</td>
      <td class="num">${fmtMoney(f.equity)}</td>
    </tr>`).join("");
  return `
    <div class="qkb-result-table">
      <table>
        <thead><tr>
          <th>Viti</th><th class="num">Të ardhura</th><th class="num">Fitimi neto</th>
          <th class="num">Aktive korrente</th><th class="num">Detyrime korrente</th>
          <th class="num">Detyrime gjithsej</th><th class="num">Kapitali</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function attachQkbHandler() {
  document.getElementById("qkbBtn").addEventListener("click", async () => {
    const statusEl = document.getElementById("qkbStatus");
    const resultEl = document.getElementById("qkbResult");
    const submitBtn = document.getElementById("submitBtn");
    const nipt = document.getElementById("nipt").value.trim().toUpperCase();
    const name = document.getElementById("name").value.trim();

    if (!NIPT_RE.test(nipt)) {
      statusEl.className = "qkb-status err";
      statusEl.textContent = "NIPT-i duhet të jetë: një shkronjë, 8 shifra, një shkronjë (p.sh. L71926023W).";
      return;
    }

    statusEl.className = "qkb-status";
    statusEl.textContent = "Duke u lidhur me QKB…";
    resultEl.innerHTML = "";
    qkbFilings = null;
    submitBtn.disabled = true;
    submitBtn.textContent = "Kërko në QKB më sipër për të vazhduar";

    try {
      const data = await api.qkbLookup({ nipt, business_name: name });
      qkbFilings = data.filings.map(f => ({
        year: f.year, revenue: f.revenue, cogs: f.cogs, net_income: f.net_income,
        current_assets: f.current_assets, current_liabilities: f.current_liabilities,
        total_liabilities: f.total_liabilities, equity: f.equity,
      }));
      statusEl.className = "qkb-status ok";
      statusEl.textContent = `${data.filings.length} vite bilanci u morën nga ${data.source}.`;
      resultEl.innerHTML = qkbResultTable(data.filings) + `<p class="muted section-gap">${esc(data.disclaimer)}</p>`;
      submitBtn.disabled = false;
      submitBtn.textContent = "Dorëzo për vetim";
    } catch (e) {
      statusEl.className = "qkb-status err";
      statusEl.textContent = trErr(e);
    }
  });
}

function attachSignupHandler() {
  document.getElementById("toggleLogin").addEventListener("click", (ev) => { ev.preventDefault(); render("login"); });
  attachQkbHandler();
  document.getElementById("signupForm").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const errEl = document.getElementById("formError");
    const val = (id) => document.getElementById(id).value;
    const num = (id) => parseFloat(document.getElementById(id).value);

    if (!qkbFilings || !qkbFilings.length) {
      errEl.innerHTML = `<div class="notice notice-error">Kërko në QKB për të marrë bilancet financiare përpara se të dorëzosh.</div>`;
      return;
    }

    const payload = {
      name: val("name"), nipt: val("nipt").trim().toUpperCase(), sector: val("sector"), city: val("city"),
      description: val("description"), investment_type: val("investment_type"),
      founded_year: parseInt(val("founded_year"), 10), employees: parseInt(val("employees"), 10),
      funding_goal: num("funding_goal"),
      contact_name: val("contact_name"), contact_email: val("contact_email"),
      contact_phone: val("contact_phone"), website: val("website"),
      password: val("password"),
      filings: qkbFilings,
    };
    try {
      const result = await api.smeSignup(payload);
      setSmeSession(result.token, result.sme);
      render("status");
    } catch (e) {
      errEl.innerHTML = `<div class="notice notice-error">${esc(trErr(e))}</div>`;
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
      errEl.innerHTML = `<div class="notice notice-error">${esc(trErr(e))}</div>`;
    }
  });
}

function render(mode) {
  if (mode === "status" || (mode === undefined && getSmeProfile())) {
    contentEl.innerHTML = `<div class="spinner-text">Duke ngarkuar…</div>`;
    showStatus();
    return;
  }
  if (mode === "login") {
    contentEl.innerHTML = loginForm();
    attachLoginHandler();
    return;
  }
  qkbFilings = null;
  contentEl.innerHTML = signupForm();
  attachSignupHandler();
}

render();
