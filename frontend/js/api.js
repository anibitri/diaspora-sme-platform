const ADMIN_TOKEN_KEY = "dsme_admin_token";
const INVESTOR_TOKEN_KEY = "dsme_investor_token";
const INVESTOR_PROFILE_KEY = "dsme_investor_profile";
const SME_TOKEN_KEY = "dsme_sme_token";
const SME_PROFILE_KEY = "dsme_sme_profile";
const THEME_KEY = "dsme_theme";

// Escape any string before it is interpolated into an innerHTML template.
// Required everywhere user- or business-submitted text (SME names, descriptions,
// contact details, admin notes) is rendered -- without it, a business signing up
// with a name like "<img src=x onerror=...>" would be a stored XSS vector.
function esc(value) {
  if (value == null) return "";
  return String(value).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

// Escape a value for safe use inside an href/src attribute (on top of esc()).
function escUrl(value) {
  if (!value) return "#";
  const s = String(value);
  if (!/^https?:\/\//i.test(s)) return "#";
  return esc(s);
}

// Best-effort Albanian translation of API error responses, keyed by the
// namespaced error_code (see app/errors.py). Falls back to the raw English
// message for anything not in the map (e.g. dynamic validation errors) so a
// user always sees *something* useful rather than a blank notice.
const ERROR_MESSAGES_SQ = {
  AUTH_EMAIL_TAKEN: "Ky email është përdorur tashmë.",
  AUTH_INVALID_CREDENTIALS: "Email ose fjalëkalim i pasaktë.",
  AUTH_RATE_LIMITED: "Shumë përpjekje nga kjo adresë. Provo përsëri pas pak minutash.",
  AUTH_INSUFFICIENT_PERMISSIONS: "Nevojitet një token admini i vlefshëm për këtë veprim.",
  VALIDATION_INVALID_AMOUNT: "Shifrat e dërguara nuk përputhen (aktivet/detyrimet korrente e kalojnë totalin).",
  VALIDATION_INVALID_NIPT: "NIPT-i duhet të jetë në formën: një shkronjë, 8 shifra, një shkronjë (p.sh. L71926023W).",
  VALIDATION_MISSING_FIELD: "Mungon një fushë e detyrueshme në formular.",
  VALIDATION_INVALID_INPUT: "Të dhënat e dërguara nuk janë të vlefshme.",
  SME_NOT_FOUND: "Nuk u gjet ky biznes.",
  SME_FILING_INCOMPLETE: "Ky biznes nuk ka ende asnjë bilanc financiar për t'u vlerësuar.",
  SME_ALREADY_VETTED: "Ky biznes është vlerësuar tashmë.",
  INVESTMENT_SME_CLOSED: "Ky biznes nuk është aktualisht i hapur për investime.",
  INVESTMENT_BELOW_MINIMUM: "Shuma është nën minimumin e lejuar për investim të simuluar.",
  INVESTMENT_KEY_REUSED: "Ky veprim është regjistruar tashmë nga një sesion tjetër.",
  INVESTMENT_NOT_FOUND: "Nuk u gjet ky investim.",
  RISK_MODEL_INSUFFICIENT_DATA: "Nuk ka ende të dhëna të mjaftueshme për të llogaritur një vlerësim.",
  SYSTEM_UNAVAILABLE: "Diçka shkoi keq nga ana jonë. Provo përsëri pas pak.",
};

function trErr(e) {
  const code = e && e.errorCode;
  if (code && ERROR_MESSAGES_SQ[code]) return ERROR_MESSAGES_SQ[code];
  return (e && e.message) || "Ndodhi një gabim i papritur.";
}

// Sector/status/tier values are stored in English in the database (they're
// the canonical filter values the backend matches on) -- these maps only
// translate the label shown to the user.
const SECTOR_LABELS_SQ = {
  "Tourism & Hospitality": "Turizëm & Mikpritje",
  "Agro-processing": "Përpunim bujqësor",
  "Manufacturing": "Prodhim",
  "IT Services": "Shërbime IT",
  "Retail & Trade": "Tregti me pakicë",
};
function sectorLabel(sector) {
  return SECTOR_LABELS_SQ[sector] || sector;
}

const INVESTMENT_TYPE_LABELS_SQ = {
  equity: "Kapital (bashkëpronësi)",
  debt: "Hua me kthim fiks",
  revenue_share: "Ndarje të ardhurash",
};
function investmentTypeLabel(type) {
  return INVESTMENT_TYPE_LABELS_SQ[type] || type;
}
function investmentTypeBadge(type) {
  return `<span class="badge badge-type">${esc(investmentTypeLabel(type))}</span>`;
}

const STATUS_LABELS_SQ = {
  pending: "Në pritje",
  vetted: "Aktiv",
  rejected: "Refuzuar",
  delisted: "Hequr nga lista",
  committed: "Konfirmuar",
};
function statusLabel(status) {
  return STATUS_LABELS_SQ[status] || status;
}

async function apiFetch(path, options = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
  const res = await fetch(path, { ...options, headers });
  let body = null;
  try {
    body = await res.json();
  } catch (e) {
    body = null;
  }
  if (!res.ok) {
    const err = new Error((body && body.message) || `Kërkesa dështoi (${res.status})`);
    err.errorCode = body && body.error_code;
    err.details = body && body.details;
    err.status = res.status;
    throw err;
  }
  return body;
}

function adminHeaders() {
  return { "X-Admin-Token": localStorage.getItem(ADMIN_TOKEN_KEY) || "" };
}
function investorAuthHeaders() {
  const token = localStorage.getItem(INVESTOR_TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}
function smeAuthHeaders() {
  const token = localStorage.getItem(SME_TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const api = {
  listSmes: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return apiFetch(`/api/smes${qs ? "?" + qs : ""}`);
  },
  getSme: (id) => apiFetch(`/api/smes/${id}`),
  recomputeScore: (id) =>
    apiFetch(`/api/smes/${id}/score`, { method: "POST", headers: adminHeaders() }),

  qkbLookup: (payload) => apiFetch(`/api/qkb/lookup`, { method: "POST", body: JSON.stringify(payload) }),

  smeSignup: (payload) => apiFetch(`/api/smes/signup`, { method: "POST", body: JSON.stringify(payload) }),
  smeLogin: (payload) => apiFetch(`/api/smes/login`, { method: "POST", body: JSON.stringify(payload) }),
  getMySme: () => apiFetch(`/api/smes/me`, { headers: smeAuthHeaders() }),

  investorSignup: (payload) => apiFetch(`/api/investors/signup`, { method: "POST", body: JSON.stringify(payload) }),
  investorLogin: (payload) => apiFetch(`/api/investors/login`, { method: "POST", body: JSON.stringify(payload) }),
  getPortfolio: () => apiFetch(`/api/investors/me/portfolio`, { headers: investorAuthHeaders() }),

  createInvestment: (payload, idemKey) =>
    apiFetch(`/api/investments`, {
      method: "POST",
      headers: { ...investorAuthHeaders(), "Idempotency-Key": idemKey },
      body: JSON.stringify(payload),
    }),

  adminListSmes: (status) =>
    apiFetch(`/api/admin/smes${status ? "?status=" + status : "?status="}`, { headers: adminHeaders() }),
  adminApprove: (id, notes) =>
    apiFetch(`/api/admin/smes/${id}/approve`, { method: "POST", headers: adminHeaders(), body: JSON.stringify({ notes }) }),
  adminReject: (id, notes) =>
    apiFetch(`/api/admin/smes/${id}/reject`, { method: "POST", headers: adminHeaders(), body: JSON.stringify({ notes }) }),
  adminDelist: (id, notes) =>
    apiFetch(`/api/admin/smes/${id}/delist`, { method: "POST", headers: adminHeaders(), body: JSON.stringify({ notes }) }),
  adminAuditLog: () => apiFetch(`/api/admin/audit-log`, { headers: adminHeaders() }),
};

function setAdminToken(token) {
  localStorage.setItem(ADMIN_TOKEN_KEY, token);
}
function getAdminToken() {
  return localStorage.getItem(ADMIN_TOKEN_KEY) || "";
}

function setInvestorSession(token, investor) {
  localStorage.setItem(INVESTOR_TOKEN_KEY, token);
  localStorage.setItem(INVESTOR_PROFILE_KEY, JSON.stringify(investor));
}
function getInvestorProfile() {
  const raw = localStorage.getItem(INVESTOR_PROFILE_KEY);
  return raw ? JSON.parse(raw) : null;
}
function clearInvestorSession() {
  localStorage.removeItem(INVESTOR_TOKEN_KEY);
  localStorage.removeItem(INVESTOR_PROFILE_KEY);
}

function setSmeSession(token, sme) {
  localStorage.setItem(SME_TOKEN_KEY, token);
  localStorage.setItem(SME_PROFILE_KEY, JSON.stringify(sme));
}
function getSmeProfile() {
  const raw = localStorage.getItem(SME_PROFILE_KEY);
  return raw ? JSON.parse(raw) : null;
}
function clearSmeSession() {
  localStorage.removeItem(SME_TOKEN_KEY);
  localStorage.removeItem(SME_PROFILE_KEY);
}

function fmtMoney(amount, currency = "EUR") {
  return new Intl.NumberFormat("sq-AL", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString("sq-AL", { year: "numeric", month: "short", day: "numeric" });
}

function uuid() {
  if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
  return "idem-" + Date.now() + "-" + Math.random().toString(16).slice(2);
}

const TIER_LABELS_SQ = { Low: "Rrezik i ulët", Medium: "Rrezik mesatar", High: "Rrezik i lartë" };

function tierBadge(tier, unavailable, stale) {
  if (unavailable) return `<span class="badge badge-neutral"><span class="dot"></span>Vlerësim jo i disponueshëm</span>`;
  const cls = tier === "Low" ? "badge-low" : tier === "Medium" ? "badge-medium" : "badge-high";
  const label = tier ? TIER_LABELS_SQ[tier] || tier : "Pa vlerësim";
  const staleTag = stale ? " (e vjetëruar)" : "";
  return `<span class="badge ${cls}"><span class="dot"></span>${esc(label)}${esc(staleTag)}</span>`;
}

const BRAND_MARK = `
  <svg class="brand-mark" width="26" height="26" viewBox="0 0 32 32" fill="none" aria-hidden="true">
    <path d="M4 22C4 22 9 14 16 14C23 14 28 22 28 22" stroke="#8C2A34" stroke-width="2.4" stroke-linecap="round"/>
    <circle cx="4" cy="24" r="2.2" fill="currentColor"/>
    <circle cx="28" cy="24" r="2.2" fill="currentColor"/>
  </svg>`;

const THEME_TOGGLE = `
  <button id="themeToggle" class="theme-toggle" type="button" aria-label="Ndrysho pamjen (të çelët / errët)" title="Ndrysho pamjen">
    <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="4.5"/><path d="M12 2.5v2.5M12 19v2.5M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2.5 12H5M19 12h2.5M4.2 19.8L6 18M18 6l1.8-1.8"/></svg>
    <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z"/></svg>
  </button>`;

function renderNav(active) {
  const investor = getInvestorProfile();
  const sme = getSmeProfile();
  return `
  <div class="prototype-banner">Prototip kërkimor &mdash; të dhëna dhe transaksione të simuluara. Asnjë para reale nuk lëviz përmes këtij sistemi.</div>
  <header class="topnav">
    <div class="topnav-inner">
      <a class="brand" href="/index.html">${BRAND_MARK}Urë</a>
      <div class="nav-right">
        <nav class="links">
          <a href="/index.html" class="${active === "home" ? "active" : ""}">Ballina</a>
          <a href="/marketplace.html" class="${active === "market" ? "active" : ""}">Tregu</a>
          <a href="/sme-signup.html" class="${active === "sme" ? "active" : ""}">${sme ? "Biznesi im" : "Regjistro biznesin"}</a>
          <a href="/investor.html" class="${active === "investor" ? "active" : ""}">${investor ? "Portofoli im" : "Hyr si investitor"}</a>
          <a href="/admin.html" class="${active === "admin" ? "active" : ""}">Admin</a>
        </nav>
        ${THEME_TOGGLE}
      </div>
    </div>
  </header>`;
}

function currentTheme() {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch (e) {
    return null;
  }
}

function applyTheme(theme) {
  if (theme === "light" || theme === "dark") {
    document.documentElement.setAttribute("data-theme", theme);
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
}

function systemPrefersDark() {
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function wireThemeToggle() {
  const btn = document.getElementById("themeToggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const active = currentTheme() || (systemPrefersDark() ? "dark" : "light");
    const next = active === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch (e) {
      // ignore -- theme just won't persist this session
    }
    applyTheme(next);
  });
}

function mountNav(active) {
  document.getElementById("nav").innerHTML = renderNav(active);
  wireThemeToggle();
}

function renderFooter() {
  return `
  <div class="footer-inner">
    <div class="footer-top">
      <div class="footer-brand">Urë</div>
      <div class="footer-links">
        <a href="/index.html">Ballina</a>
        <a href="/marketplace.html">Tregu</a>
        <a href="/sme-signup.html">Regjistro biznesin</a>
        <a href="/investor.html">Hyr si investitor</a>
        <a href="/admin.html">Admin</a>
      </div>
    </div>
    <p class="footer-disclaimer">
      Urë është një prototip kërkimor i ndërtuar për tezën <em>"A Diaspora-to-SME Investment
      Platform for Albania."</em> Bizneset, bilancet dhe vlerësimet e rrezikut këtu janë të
      simuluara për qëllime demonstrimi dhe nuk përbëjnë këshillë investimi apo ofertë reale
      për të investuar. Nuk zbatohen pagesa reale, KYC/AML apo përputhshmëri me legjislacionin
      e letrave me vlerë.
    </p>
  </div>`;
}

function mountFooter() {
  const el = document.getElementById("footer");
  if (el) el.innerHTML = renderFooter();
}
mountFooter();
