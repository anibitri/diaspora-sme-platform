# Engineering Checklist Audit

Date: 2026-08-12

This audits the prototype against a production-readiness checklist (architecture,
security, error handling, data handling, testing, scaling, deployment, CI/CD,
monitoring, documentation), verified against the actual code rather than
recalled from memory. Intended as thesis appendix material / a discussion point
for the limitations chapter — nothing here was auto-fixed; it's a snapshot of
what's true today.

Status legend: ✅ done · ⚠️ partial/caveat · ❌ not implemented · 🆕 bug found during this audit · N/A not applicable yet

## Architecture

| Item | Status | Notes |
|---|---|---|
| Risk-scoring as separate service | ❌ | `risk_scoring.py` is a pure, stateless module (no DB access, plain functions in → dataclass out) called in-process from `smes.py`. It's *logically* separable — nothing would need to change inside it — but it's not physically deployed as its own service/process. |
| SME/filing/score as separate versioned entities | ✅ | Three real tables (`SME`, `Filing`, `RiskScore`). `RiskScore` is append-only/versioned (`computed_at`, never overwritten). `Filing` is per-year, but see gap below — no amend/correction path once submitted. |
| Simulated payment ledger, clearly flagged | ✅ | `Investment` rows only (`status="committed"`), banner + README flag it as simulated everywhere. It's a flat commitment list, not a double-entry ledger — fine for what this is, but don't call it a "ledger" in the thesis text without that caveat. |
| Investor/SME/admin separated at data-model level | ⚠️ | Investor and SME are separate tables with independent password auth and independently-typed session tokens (verified live: an investor token gets `AUTH_INSUFFICIENT_PERMISSIONS` against an SME-only endpoint — real server-side enforcement, not UI hiding). **But** admin isn't a data-model entity at all — no `Admin` table, just one shared header token. "Separation at the data-model level" is only 2/3 true. |

## Security

| Item | Status | Notes |
|---|---|---|
| bcrypt/argon2, never custom auth | ❌ **Direct miss** | PBKDF2-HMAC-SHA256 (260k iterations, salted) is used — cryptographically sound and OWASP-acceptable, but not bcrypt/argon2, and neither package is installed. The session token is also hand-rolled HMAC signing rather than a vetted library (`itsdangerous`/`PyJWT`). This is the one item where a library should have been used and wasn't. |
| TLS everywhere, encrypt at rest | ❌ (intentional) | No TLS — there's no real deployment target for a local `uvicorn` dev server to terminate TLS against. No field-level encryption at rest either; `password_hash` is hashed (not reversible) but everything else is plaintext in SQLite. Documented as prototype scope, not silently skipped. |
| Parameterized queries only | ✅ | Verified: zero raw SQL anywhere, 100% SQLAlchemy ORM. |
| Rate-limit auth **and investment** endpoints | ⚠️ **Direct miss** | Login/signup (investor, SME, admin) are rate-limited. `POST /api/investments` is not — confirmed, no limiter dependency on it. |
| RBAC enforced server-side | ✅ | Verified live, not assumed: hit `/api/smes/me` with a valid *investor* token → correctly rejected. Admin routes require a completely separate credential. |
| No PII/financial data in plaintext logs | ✅/⚠️ | True today, but only because there's no application logging at all yet (see Monitoring). Uvicorn's default access log records method/path/status, not bodies. This control hasn't actually been exercised against a real logging setup. |
| Dependency/vulnerability scanning | ❌ | `pip-audit` isn't installed, nothing runs it. |
| Virus-scan uploaded documents | N/A | There's no document upload feature — SME signup takes typed financial figures, not files. Correctly out of scope until an upload feature exists. |

## Error handling

| Item | Status |
|---|---|
| One consistent error schema | ✅ Verified — `{error_code, message, details}` on every path (`AppError`, validation errors, and the generic 500 handler all normalize to this). |
| Namespaced error codes | ⚠️ `AUTH_*`, `VALIDATION_*`, `SME_*`, `INVESTMENT_*`, `SYSTEM_*` are all live. `RISK_MODEL_*` is defined in `errors.py` but **dead code** — never actually thrown, because the graceful-degradation path (missing filings) returns a 200 with `unavailable: true` rather than an error. Arguably the more correct behavior, but the helper function is unused. |
| Fail loudly, flag stale/missing scores | ✅ Verified in the UI (stale-score banner, "score unavailable" badge). |
| Idempotency keys on investments | ✅ Verified working (duplicate key returns the original investment, no double-count). |

## Data handling

| Item | Status |
|---|---|
| Defensive validation on messy QKB ingestion | ⚠️ The scoring logic itself degrades gracefully (div-by-zero guards, neutral Benford score under 10 observations, explicit unavailable state with no filings) — that part's solid. But there's no bulk/CSV ingestion pipeline at all right now, only the single-filing signup form with typed, browser-validated number inputs. "Assume messy data" is untested because nothing messy can currently get in. |
| DB transactions around investment commits | ✅ Single atomic `add`+`commit` per investment, with `IntegrityError` rollback-and-recover for idempotency races. No multi-step operation exists yet that would need explicit transaction demarcation beyond this. |
| Version filings and scores | ⚠️ `RiskScore` is versioned. `Filing` is not — once an SME submits a filing, there's no endpoint to amend or add a subsequent year. A real SME can never update their numbers after signup. |

## Testing

❌ **None exists** — no `tests/`, no pytest installed. Explicitly deferred in the README as production-only. This is the biggest real gap relative to "unit tests for risk-scoring as the highest-value tests."

## Scaling

| Item | Status |
|---|---|
| Explicit "not over-engineering" note | ✅ in spirit (README's "what this doesn't do" section), though there's no literal Scaling section. |
| Stateless API design | ✅ Auth is a signed token, not a server-side session store — genuinely stateless. The one exception is the in-memory rate limiter (already documented as not multi-worker-safe). |
| Pagination on SME listing | ❌ `GET /api/smes` returns the full list, no `limit`/`offset`. |
| Indexing on FK/filter columns | ❌ Confirmed: none of the 5 foreign-key columns (`Filing.sme_id`, `RiskScore.sme_id`, `Investment.sme_id`/`investor_id`, `AdminAction.sme_id`) have `index=True`. Irrelevant at 20-row prototype scale, cheap to add. |
| Scoring pipeline horizontally separable | ⚠️ Same nuance as Architecture #1 — logically yes, physically no. |

## Deployment

❌ No Dockerfile, no docker-compose. ⚠️ `ADMIN_TOKEN` reads from an env var with a documented fallback (not hardcoded-only), but there's no `.env`/`.env.example` pattern and no dev/staging/prod split — just one implicit config.

## CI/CD

❌ None — no `.github/workflows`, consistent with no tests existing to run yet.

## Monitoring/reliability

❌ No structured logging, no Sentry, no health-check endpoint, no DB backup script.

## Documentation

| Item | Status |
|---|---|
| README a marker could run cold | ✅ likely, but hadn't been re-verified via a true from-scratch install since `requirements.txt` was last patched — worth a clean-venv sanity check. |
| OpenAPI/Swagger | 🆕 **Bug found during this audit**: FastAPI auto-generates `/docs`, but the app's own `Content-Security-Policy` (added during the security pass) blocks the CDN-hosted Swagger UI assets (`cdn.jsdelivr.net`), so `/docs` renders broken/blank in a real browser. `/openapi.json` itself still works. This is a real regression that should be fixed regardless of what else gets prioritized. |
| Inline comments on scoring logic | ✅ Already has a substantial module docstring and per-branch rationale (Nigrini thresholds cited, why under-10-observations gets a neutral score, etc.). |

---

**Net read:** most Architecture/Error-handling/Data-handling items are already true and were verified live rather than assumed. The concrete misses against what was explicitly asked for are **bcrypt/argon2 instead of PBKDF2**, **rate-limiting on investments**, and the **Swagger CSP bug**. Testing, Docker, CI, and Monitoring are genuinely absent, consistent with earlier scope decisions but now explicitly in tension with this checklist.
