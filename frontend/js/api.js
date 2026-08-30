const ADMIN_TOKEN_KEY = "dsme_admin_token";
const INVESTOR_TOKEN_KEY = "dsme_investor_token";
const INVESTOR_PROFILE_KEY = "dsme_investor_profile";
const SME_TOKEN_KEY = "dsme_sme_token";
const SME_PROFILE_KEY = "dsme_sme_profile";

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
    const err = new Error((body && body.message) || `Request failed (${res.status})`);
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
  return new Intl.NumberFormat("en-GB", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString("en-GB", { year: "numeric", month: "short", day: "numeric" });
}

function uuid() {
  if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
  return "idem-" + Date.now() + "-" + Math.random().toString(16).slice(2);
}

function tierBadge(tier, unavailable, stale) {
  if (unavailable) return `<span class="badge badge-neutral"><span class="dot"></span>Score unavailable</span>`;
  const cls = tier === "Low" ? "badge-low" : tier === "Medium" ? "badge-medium" : "badge-high";
  const label = tier ? `${tier} risk` : "Unscored";
  const staleTag = stale ? " (stale)" : "";
  return `<span class="badge ${cls}"><span class="dot"></span>${esc(label)}${esc(staleTag)}</span>`;
}

function renderNav(active) {
  const investor = getInvestorProfile();
  const sme = getSmeProfile();
  return `
  <div class="prototype-banner">Research prototype &mdash; simulated data, simulated transactions. No real money moves through this system.</div>
  <header class="topnav">
    <div class="topnav-inner">
      <div class="brand">Diaspora<span>Invest</span> Albania</div>
      <nav class="links">
        <a href="/index.html" class="${active === "market" ? "active" : ""}">Marketplace</a>
        <a href="/sme-signup.html" class="${active === "sme" ? "active" : ""}">${sme ? "My business" : "List your business"}</a>
        <a href="/investor.html" class="${active === "investor" ? "active" : ""}">${investor ? "My portfolio" : "Investor login"}</a>
        <a href="/admin.html" class="${active === "admin" ? "active" : ""}">Admin / vetting</a>
      </nav>
    </div>
  </header>`;
}

function mountNav(active) {
  document.getElementById("nav").innerHTML = renderNav(active);
}
