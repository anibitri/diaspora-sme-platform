const ADMIN_TOKEN_KEY = "dsme_admin_token";
const INVESTOR_KEY = "dsme_investor";

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

const api = {
  listSmes: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return apiFetch(`/api/smes${qs ? "?" + qs : ""}`);
  },
  getSme: (id) => apiFetch(`/api/smes/${id}`),
  recomputeScore: (id) =>
    apiFetch(`/api/smes/${id}/score`, { method: "POST", headers: adminHeaders() }),

  createInvestor: (payload) => apiFetch(`/api/investors`, { method: "POST", body: JSON.stringify(payload) }),
  getInvestorByEmail: (email) => apiFetch(`/api/investors/by-email/${encodeURIComponent(email)}`),
  getPortfolio: (investorId) => apiFetch(`/api/investors/${investorId}/portfolio`),

  createInvestment: (payload, idemKey) =>
    apiFetch(`/api/investments`, {
      method: "POST",
      headers: { "Idempotency-Key": idemKey },
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

function adminHeaders() {
  const token = localStorage.getItem(ADMIN_TOKEN_KEY) || "";
  return { "X-Admin-Token": token };
}

function setAdminToken(token) {
  localStorage.setItem(ADMIN_TOKEN_KEY, token);
}
function getAdminToken() {
  return localStorage.getItem(ADMIN_TOKEN_KEY) || "";
}

function setCurrentInvestor(investor) {
  localStorage.setItem(INVESTOR_KEY, JSON.stringify(investor));
}
function getCurrentInvestor() {
  const raw = localStorage.getItem(INVESTOR_KEY);
  return raw ? JSON.parse(raw) : null;
}
function clearCurrentInvestor() {
  localStorage.removeItem(INVESTOR_KEY);
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
  return `<span class="badge ${cls}"><span class="dot"></span>${label}${staleTag}</span>`;
}

function renderNav(active) {
  const investor = getCurrentInvestor();
  return `
  <div class="prototype-banner">Research prototype &mdash; simulated data, simulated transactions. No real money moves through this system.</div>
  <header class="topnav">
    <div class="topnav-inner">
      <div class="brand">Diaspora<span>Invest</span> Albania</div>
      <nav class="links">
        <a href="/index.html" class="${active === "market" ? "active" : ""}">Marketplace</a>
        <a href="/investor.html" class="${active === "investor" ? "active" : ""}">${investor ? "My portfolio" : "Investor login"}</a>
        <a href="/admin.html" class="${active === "admin" ? "active" : ""}">Admin / vetting</a>
      </nav>
    </div>
  </header>`;
}

function mountNav(active) {
  document.getElementById("nav").innerHTML = renderNav(active);
}
