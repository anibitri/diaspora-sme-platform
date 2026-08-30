import datetime as dt
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import create_session_token, get_current_sme, hash_password, verify_password
from app.database import get_db
from app.deps import require_admin
from app.errors import AppError, auth_error, sme_error, validation_error
from app.models import AdminAction, Filing, RiskScore, SME
from app.rate_limit import rate_limit_auth
from app.returns import estimate_return_pct
from app.risk_scoring import compute_risk_score
from app.schemas import RiskScoreOut, SMEDetailOut, SMELogin, SMESessionOut, SMESignup, SMESummaryOut

router = APIRouter(prefix="/api/smes", tags=["smes"])

CURRENT_YEAR = dt.date.today().year


def _risk_score_out(rs: RiskScore | None) -> RiskScoreOut | None:
    if rs is None:
        return None
    return RiskScoreOut(
        computed_at=rs.computed_at,
        based_on_filing_year=rs.based_on_filing_year,
        score=rs.score,
        tier=rs.tier,
        liquidity_score=rs.liquidity_score,
        leverage_score=rs.leverage_score,
        profitability_score=rs.profitability_score,
        benford_score=rs.benford_score,
        stale=rs.stale,
        unavailable=rs.unavailable,
        reason=rs.reason,
        notes=json.loads(rs.notes_json or "{}"),
    )


def _latest_score(sme: SME) -> RiskScore | None:
    if not sme.risk_scores:
        return None
    return max(sme.risk_scores, key=lambda r: r.computed_at)


def _ensure_score(db: Session, sme: SME) -> RiskScore | None:
    """Lazily compute and cache a score the first time an SME is viewed."""
    existing = _latest_score(sme)
    if existing is not None:
        return existing
    if not sme.filings:
        return None
    result = compute_risk_score(sme.filings, CURRENT_YEAR)
    rs = RiskScore(
        sme_id=sme.id,
        based_on_filing_year=result.based_on_filing_year,
        score=result.score, tier=result.tier,
        liquidity_score=result.liquidity_score, leverage_score=result.leverage_score,
        profitability_score=result.profitability_score, benford_score=result.benford_score,
        stale=result.stale, unavailable=result.unavailable, reason=result.reason,
        notes_json=json.dumps(result.notes),
    )
    db.add(rs)
    db.commit()
    db.refresh(rs)
    return rs


def _detail_out(sme: SME, rs: RiskScore | None) -> SMEDetailOut:
    tier = rs.tier if rs and not rs.unavailable else None
    return SMEDetailOut(
        id=sme.id, name=sme.name, nipt=sme.nipt, sector=sme.sector, city=sme.city, description=sme.description,
        founded_year=sme.founded_year, employees=sme.employees, funding_goal=sme.funding_goal,
        status=sme.status,
        contact_name=sme.contact_name, contact_email=sme.contact_email,
        contact_phone=sme.contact_phone, website=sme.website,
        has_login=sme.password_hash is not None,
        investment_type=sme.investment_type,
        expected_return_pct=estimate_return_pct(sme.investment_type, tier),
        filings=sme.filings, risk_score=_risk_score_out(rs),
    )


@router.get("", response_model=list[SMESummaryOut])
def list_smes(
    status: str | None = "vetted",
    sector: str | None = None,
    risk_tier: str | None = None,
    investment_type: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(SME)
    if status:
        query = query.filter(SME.status == status)
    if sector:
        query = query.filter(SME.sector == sector)
    if investment_type:
        query = query.filter(SME.investment_type == investment_type)

    out = []
    for sme in query.order_by(SME.name).all():
        rs = _ensure_score(db, sme)
        if risk_tier and (rs is None or rs.tier != risk_tier):
            continue
        tier = rs.tier if rs and not rs.unavailable else None
        out.append(SMESummaryOut(
            id=sme.id, name=sme.name, sector=sme.sector, city=sme.city,
            founded_year=sme.founded_year, employees=sme.employees, funding_goal=sme.funding_goal,
            status=sme.status,
            contact_name=sme.contact_name, contact_email=sme.contact_email,
            investment_type=sme.investment_type,
            expected_return_pct=estimate_return_pct(sme.investment_type, tier),
            risk_score=rs.score if rs else None,
            risk_tier=rs.tier if rs else None,
            risk_stale=rs.stale if rs else False,
            risk_unavailable=rs.unavailable if rs else True,
        ))
    return out


@router.post("/signup", response_model=SMESessionOut, dependencies=[Depends(rate_limit_auth)])
def signup(payload: SMESignup, db: Session = Depends(get_db)):
    """A business registers itself and enters the admin vetting queue
    (thesis section 5: SME onboarding). Deliberately distinct from the
    seeded/sampled SMEs, which represent QKB filing data with no platform
    login (thesis section 6)."""
    if db.query(SME).filter(SME.contact_email == payload.contact_email).one_or_none():
        raise AppError("AUTH_EMAIL_TAKEN", "A business with that contact email is already registered.", 409)

    for f in payload.filings:
        total_assets = f.total_liabilities + f.equity
        if f.current_assets > total_assets + 0.01:
            raise validation_error(
                "INVALID_AMOUNT",
                f"Filing year {f.year}: current assets cannot exceed total assets (total liabilities + equity).",
            )
        if f.current_liabilities > f.total_liabilities + 0.01:
            raise validation_error(
                "INVALID_AMOUNT", f"Filing year {f.year}: current liabilities cannot exceed total liabilities."
            )

    sme = SME(
        name=payload.name, nipt=payload.nipt, sector=payload.sector, city=payload.city,
        description=payload.description,
        founded_year=payload.founded_year, employees=payload.employees, funding_goal=payload.funding_goal,
        status="pending", investment_type=payload.investment_type,
        contact_name=payload.contact_name, contact_email=payload.contact_email,
        contact_phone=payload.contact_phone, website=payload.website,
        password_hash=hash_password(payload.password),
    )
    db.add(sme)
    db.flush()

    filed_date = dt.date.today()
    for f in payload.filings:
        db.add(Filing(
            sme_id=sme.id, year=f.year,
            revenue=f.revenue, cogs=f.cogs, net_income=f.net_income,
            current_assets=f.current_assets, current_liabilities=f.current_liabilities,
            total_assets=f.total_liabilities + f.equity, total_liabilities=f.total_liabilities, equity=f.equity,
            filed_date=filed_date, is_late=False,
        ))
    db.add(AdminAction(sme_id=sme.id, actor="system", action="submit",
                        notes="Biznesi u vetregjistrua dhe u dorëzua për vetim."))
    db.commit()
    db.refresh(sme)

    token = create_session_token("sme", sme.id)
    return SMESessionOut(token=token, sme=_detail_out(sme, _ensure_score(db, sme)))


@router.post("/login", response_model=SMESessionOut, dependencies=[Depends(rate_limit_auth)])
def login(payload: SMELogin, db: Session = Depends(get_db)):
    sme = db.query(SME).filter(SME.contact_email == payload.email).one_or_none()
    if sme is None or not verify_password(payload.password, sme.password_hash):
        raise auth_error("INVALID_CREDENTIALS", "Incorrect email or password.")
    token = create_session_token("sme", sme.id)
    return SMESessionOut(token=token, sme=_detail_out(sme, _latest_score(sme)))


@router.get("/me", response_model=SMEDetailOut)
def get_me(sme: SME = Depends(get_current_sme), db: Session = Depends(get_db)):
    rs = _ensure_score(db, sme)
    return _detail_out(sme, rs)


@router.get("/{sme_id}", response_model=SMEDetailOut)
def get_sme(sme_id: int, db: Session = Depends(get_db)):
    sme = db.get(SME, sme_id)
    if sme is None:
        raise sme_error("NOT_FOUND", f"No SME found with id {sme_id}.")
    rs = _ensure_score(db, sme)
    return _detail_out(sme, rs)


@router.post("/{sme_id}/score", response_model=RiskScoreOut, dependencies=[Depends(require_admin)])
def recompute_score(sme_id: int, db: Session = Depends(get_db)):
    """Admin-triggered recompute -- creates a new versioned score row rather
    than overwriting the previous one, so investors can see when a score last
    changed (thesis section 12.5)."""
    sme = db.get(SME, sme_id)
    if sme is None:
        raise sme_error("NOT_FOUND", f"No SME found with id {sme_id}.")
    if not sme.filings:
        raise sme_error("FILING_INCOMPLETE", "Cannot score an SME with no filings on record.", http_status=400)

    result = compute_risk_score(sme.filings, CURRENT_YEAR)
    rs = RiskScore(
        sme_id=sme.id,
        based_on_filing_year=result.based_on_filing_year,
        score=result.score, tier=result.tier,
        liquidity_score=result.liquidity_score, leverage_score=result.leverage_score,
        profitability_score=result.profitability_score, benford_score=result.benford_score,
        stale=result.stale, unavailable=result.unavailable, reason=result.reason,
        notes_json=json.dumps(result.notes),
    )
    db.add(rs)
    db.commit()
    db.refresh(rs)
    return _risk_score_out(rs)
