# Diaspora-to-SME Investment Platform (Prototype)

A working prototype for the thesis *"A Diaspora-to-SME Investment Platform for
Albania: Channeling Remittance Capital into Local Enterprise Financing."* It
implements the three components described in the proposal's Section 5:

1. **Investor-facing web app** — sign up, browse vetted Albanian SMEs, view an
   explainable risk score, simulate committing an investment.
2. **SME onboarding + scoring pipeline** — a business signs up and submits its
   first filing directly; that filing is scored using financial ratios
   (liquidity, leverage, profitability) plus a Benford's Law digit-conformity
   check, combined into a transparent 0–100 composite score with a full
   breakdown, never a black-box number.
3. **Admin/vetting layer** — approve, reject, or delist SMEs, with an
   append-only audit log, simulating the governance step any real platform
   would legally require.

All data is simulated. No real payments, KYC/AML, or securities compliance are
implemented — this is a research prototype, not a fundable product (see
[What this prototype deliberately does not do](#what-this-prototype-deliberately-does-not-do)
below, which maps to thesis Section 12).

## Stack

Python (FastAPI + SQLAlchemy + SQLite) on the backend; dependency-free HTML/CSS/
vanilla JS on the frontend, served as static files by the same FastAPI process.
No build step, no third-party JS.

## Running it

Requires Python 3.11–3.13 (3.14 is too new for some dependencies as of writing).

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8420
```

Open http://127.0.0.1:8420. The SQLite database (`data/app.db`) is created and
auto-seeded with ~17 simulated SMEs (spanning Low/Medium/High risk tiers,
including at least one with negative equity) on first run. Delete `data/app.db`
and restart to reseed from scratch.

- **Marketplace** (`/index.html`) — browse vetted SMEs, filter by sector/risk tier.
- **SME detail** (`/sme.html?id=..`) — filing history, contact & links, full
  risk-score breakdown with charts, simulated investment form.
- **List your business** (`/sme-signup.html`) — a business registers, submits
  its first filing, and enters the admin vetting queue; logging back in shows
  its own vetting status.
- **Investor** (`/investor.html`) — real sign-up/login (password-based),
  portfolio view.
- **Admin** (`/admin.html`) — vetting queue and audit log. Token:
  `demo-admin-token` (enter it in the on-page prompt; see [Auth caveat](#auth-caveat)).

Demo credentials (pre-seeded so the portfolio view isn't empty on first look):
investor `elira.demo@example.com` / `demo1234`.

## The risk-scoring model

Implemented in [`app/risk_scoring.py`](app/risk_scoring.py). Designed for a
market with no credit-bureau or audit-quality data (thesis Section 2.3): every
component is computable from a single self-reported annual filing.

| Component | 0–25 pts | Signal |
|---|---|---|
| Liquidity | current ratio (current assets / current liabilities) |
| Leverage | debt-to-equity (total liabilities / equity); equity ≤ 0 scores 0 |
| Profitability | net margin + YoY revenue growth (when ≥2 years of filings exist) |
| Benford check | first-digit conformity (Nigrini MAD) across pooled filing figures |

The Benford component is explicitly **not** a fraud-detection proof — with
small SMEs there are rarely enough line items to be statistically reliable, so
the model applies a neutral score and says so when the sample is under 10
observations, rather than pretending confidence it doesn't have. This mirrors
the thesis's own honesty requirement about weak ground truth (Section 8, 10).
It's also worth being explicit that pooling structurally related line items
from one filing (revenue, assets, liabilities, equity) is a simplification —
a more rigorous design would test each account across many independent
filings separately; this is a low-cost prototype-grade signal, not a
forensic-accounting-grade one.

Scores are versioned (`risk_scores` table) — recomputing via the admin panel
adds a new row rather than overwriting history, so "when was this last
scored" is always answerable (thesis Section 12.5).

**Data integrity note:** every generated/submitted filing satisfies the
fundamental accounting identity — total assets = total liabilities + equity —
by construction. `total_assets` is never collected or generated independently;
it is always *derived*. An earlier version of the synthetic data generator
computed `total_assets` from an unrelated formula and produced balance sheets
that didn't balance, which would have undermined the ratios computed from
them. Both the seed generator (`app/seed_data.py`) and the SME signup endpoint
enforce this the same way, and `current_assets`/`current_liabilities` are
validated (client- and server-side) to never exceed their whole-balance-sheet
counterparts.

## Accounts & security

Three account types, each with its own auth:

| Account | How it authenticates | Notes |
|---|---|---|
| Investor | Password, via `/api/investors/signup` \| `/login` | Session-scoped: an investor can only invest as themselves and only view their own portfolio. |
| SME (business) | Password, via `/api/smes/signup` \| `/login` | Only businesses that self-register get a login. Seeded/sampled SMEs (representing QKB filing data, thesis Section 6) have none — `has_login: false`. |
| Admin | Shared token (`X-Admin-Token` header) | Deliberately simulated — see [Auth caveat](#auth-caveat). |

What's implemented, mapped to thesis Section 12.1's security checklist:

- **Password hashing** — PBKDF2-HMAC-SHA256, 260,000 iterations, random
  per-user salt (`app/auth.py`). No plaintext or reversibly-encrypted
  passwords stored anywhere.
- **Session tokens** — HMAC-signed, 12-hour expiry, verified server-side on
  every authenticated request; the investor/SME identity is *always* taken
  from the token, never from a client-supplied ID in the request body (an
  earlier version trusted a client-supplied `investor_id` on investment
  creation — fixed).
- **Rate limiting** on login/signup endpoints — 8 attempts per 5 minutes per
  IP+route (`app/rate_limit.py`), against credential stuffing.
- **Security response headers** on every response (`app/main.py`):
  `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
  `Permissions-Policy`, and a real `Content-Security-Policy` with a strict
  `script-src 'self'` — every page's JS lives in an external `.js` file
  specifically so this doesn't need `unsafe-inline` for scripts.
- **Output escaping** — all user- and business-submitted text (SME names,
  descriptions, contact details, admin notes) is HTML-escaped before being
  interpolated into the DOM (`esc()` in `js/api.js`). This matters more once
  businesses can self-register: SME name/description are now
  externally-submitted strings rendered to other users (investors, admin),
  so this is a real stored-XSS fix, not defense-in-depth theatre.
- **Balance-sheet validation** on SME signup — `current_assets` cannot exceed
  total assets, `current_liabilities` cannot exceed total liabilities;
  rejected with `VALIDATION_INVALID_AMOUNT` otherwise.

What's still **not** implemented (production-only, thesis Section 12.1):
MFA, per-admin accounts/roles, encryption at rest for the SQLite file, TLS
termination (this is a local dev server — a real deploy needs a reverse proxy
or `--ssl-keyfile`/`--ssl-certfile`), token revocation, dependency/vuln
scanning, virus scanning on uploads (no file upload exists yet), and a
distributed rate-limit store (the current limiter is in-process, fine for one
worker, not for a multi-process deployment).

## API design

Every error response follows one schema:

```json
{ "error_code": "INVESTMENT_BELOW_MINIMUM", "message": "...", "details": {...} }
```

Error codes are namespaced exactly as specified in thesis Section 12.2:
`AUTH_*`, `VALIDATION_*`, `SME_*`, `INVESTMENT_*`, `RISK_MODEL_*`, `SYSTEM_*`.
See [`app/errors.py`](app/errors.py).

Other implemented behaviors from that section:
- **Idempotency keys** on `POST /api/investments` (`Idempotency-Key` header) —
  a retried request after a dropped connection returns the original
  investment instead of double-counting it.
- **Graceful degradation** — an SME with no filings returns
  `risk_score: null` with an explicit `RISK_MODEL_INSUFFICIENT_DATA` reason,
  and a stale filing (>2 years old) is flagged rather than hidden or silently
  treated as current.

## What this prototype deliberately does not do

Per thesis Section 10 (Risks and Limitations) and Section 12 (Production-Grade
Requirements), this prototype is intentionally scoped down. It does **not**
implement: real payment rails (investments are simulated `commit` rows only);
KYC/AML checks; encryption at rest; securities-law or GDPR compliance;
automated tests, monitoring, or backup/disaster-recovery. (Real password auth
and session tokens *are* now implemented — see [Accounts & security](#accounts--security)
above — which is more than the very first prototype pass had.) These are
listed explicitly so the gap between prototype and a real deployment is a
documented design decision, not an oversight — exactly the framing the thesis
proposal calls for.

### Auth caveat

The admin token (`demo-admin-token`, overridable via the `ADMIN_TOKEN` env
var) is a single shared secret purely to demonstrate investor/admin role
separation in the UI and API (`app/deps.py`). It is not per-admin
authentication and would need to be replaced entirely (real accounts, MFA,
role-based permissions) for any non-prototype use.

## Project layout

```
app/
  main.py            FastAPI app: routing, static mount, security headers, startup seeding
  database.py         SQLAlchemy engine/session
  models.py            ORM models (SME, Filing, RiskScore, Investor, Investment, AdminAction)
  schemas.py            Pydantic request/response models
  errors.py             Namespaced error schema + exception handlers
  auth.py                Password hashing + signed session tokens + auth dependencies
  rate_limit.py           In-memory rate limiter for login/signup
  deps.py                  Prototype admin-auth dependency
  risk_scoring.py           Ratio + Benford's Law scoring pipeline
  seed_data.py                Simulated QKB-style SME/filing dataset
  routers/
    smes.py, investors.py, investments.py, admin.py
frontend/
  index.html, sme.html, sme-signup.html, investor.html, admin.html
  css/style.css
  js/api.js, js/charts.js          shared helpers (fetch wrapper, esc(), chart rendering)
  js/page-*.js                       one external script per page (required for strict CSP)
```

## Relation to the thesis's empirical component

This repo covers the **development component** (thesis Section 7.2) only:
the platform prototype and the risk-scoring pipeline. The **empirical
component** — the diaspora willingness-to-invest survey, real QKB filing
collection, and back-testing the score against weak ground truth (Section
7.1) — is separate fieldwork this codebase does not attempt; `seed_data.py`
generates synthetic filings standing in for a real QKB sample.
