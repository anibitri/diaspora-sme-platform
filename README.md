# Diaspora-to-SME Investment Platform (Prototype)

A working prototype for the thesis *"A Diaspora-to-SME Investment Platform for
Albania: Channeling Remittance Capital into Local Enterprise Financing."* It
implements the three components described in the proposal's Section 5:

1. **Investor-facing web app** — browse vetted Albanian SMEs, view an
   explainable risk score, simulate committing an investment.
2. **SME scoring pipeline** — financial ratios (liquidity, leverage,
   profitability) plus a Benford's Law digit-conformity check, combined into a
   transparent 0–100 composite score with a full breakdown, never a
   black-box number.
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
No build step.

## Running it

Requires Python 3.11–3.13 (3.14 is too new for some dependencies as of writing).

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8420
```

Open http://127.0.0.1:8420. The SQLite database (`data/app.db`) is created and
auto-seeded with ~17 simulated SMEs (spanning Low/Medium/High risk tiers) on
first run. Delete `data/app.db` and restart to reseed from scratch.

- **Marketplace** (`/index.html`) — browse vetted SMEs, filter by sector/risk tier.
- **SME detail** (`/sme.html?id=..`) — filing history, full risk-score
  breakdown with charts, simulated investment form.
- **Investor** (`/investor.html`) — simulated sign-up/login by email, portfolio view.
- **Admin** (`/admin.html`) — vetting queue and audit log. Token: `demo-admin-token`
  (enter it in the on-page prompt; see [Auth caveat](#auth-caveat)).

A demo investor (`elira.demo@example.com`) is pre-seeded with two investments,
so the portfolio view isn't empty on first look.

## The risk-scoring model

Implemented in [`app/risk_scoring.py`](app/risk_scoring.py). Designed for a
market with no credit-bureau or audit-quality data (thesis Section 2.3): every
component is computable from a single self-reported annual filing.

| Component | 0–25 pts | Signal |
|---|---|---|
| Liquidity | current ratio (current assets / current liabilities) |
| Leverage | debt-to-equity (total liabilities / equity) |
| Profitability | net margin + YoY revenue growth (when ≥2 years of filings exist) |
| Benford check | first-digit conformity (Nigrini MAD) across pooled filing figures |

The Benford component is explicitly **not** a fraud-detection proof — with
small SMEs there are rarely enough line items to be statistically reliable, so
the model applies a neutral score and says so when the sample is under 10
observations, rather than pretending confidence it doesn't have. This mirrors
the thesis's own honesty requirement about weak ground truth (Section 8, 10).

Scores are versioned (`risk_scores` table) — recomputing via the admin panel
adds a new row rather than overwriting history, so "when was this last
scored" is always answerable (thesis Section 12.5).

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
real authentication (investor "login" is create-by-email with no password;
admin auth is one shared demo token, not per-admin accounts or MFA); KYC/AML
checks; encryption at rest; securities-law or GDPR compliance; automated
tests, monitoring, or backup/disaster-recovery. These are listed explicitly so
the gap between prototype and a real deployment is a documented design
decision, not an oversight — exactly the framing the thesis proposal calls for.

### Auth caveat

The admin token (`demo-admin-token`) is a hardcoded shared secret purely to
demonstrate investor/admin role separation in the UI and API
(`app/deps.py`). It is not real authentication and would need to be replaced
entirely for any non-prototype use.

## Project layout

```
app/
  main.py            FastAPI app: routing, static mount, startup seeding
  database.py         SQLAlchemy engine/session
  models.py            ORM models (SME, Filing, RiskScore, Investor, Investment, AdminAction)
  schemas.py            Pydantic request/response models
  errors.py             Namespaced error schema + exception handlers
  deps.py                Prototype admin-auth dependency
  risk_scoring.py         Ratio + Benford's Law scoring pipeline
  seed_data.py              Simulated QKB-style SME/filing dataset
  routers/
    smes.py, investors.py, investments.py, admin.py
frontend/
  index.html, sme.html, investor.html, admin.html
  css/style.css
  js/api.js, js/charts.js
```

## Relation to the thesis's empirical component

This repo covers the **development component** (thesis Section 7.2) only:
the platform prototype and the risk-scoring pipeline. The **empirical
component** — the diaspora willingness-to-invest survey, real QKB filing
collection, and back-testing the score against weak ground truth (Section
7.1) — is separate fieldwork this codebase does not attempt; `seed_data.py`
generates synthetic filings standing in for a real QKB sample.
