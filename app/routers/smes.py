import datetime as dt
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.errors import sme_error
from app.models import RiskScore, SME
from app.risk_scoring import compute_risk_score
from app.schemas import RiskScoreOut, SMEDetailOut, SMESummaryOut

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


@router.get("", response_model=list[SMESummaryOut])
def list_smes(
    status: str | None = "vetted",
    sector: str | None = None,
    risk_tier: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(SME)
    if status:
        query = query.filter(SME.status == status)
    if sector:
        query = query.filter(SME.sector == sector)

    out = []
    for sme in query.order_by(SME.name).all():
        rs = _ensure_score(db, sme)
        if risk_tier and (rs is None or rs.tier != risk_tier):
            continue
        out.append(SMESummaryOut(
            id=sme.id, name=sme.name, sector=sme.sector, city=sme.city,
            founded_year=sme.founded_year, employees=sme.employees, funding_goal=sme.funding_goal,
            status=sme.status,
            risk_score=rs.score if rs else None,
            risk_tier=rs.tier if rs else None,
            risk_stale=rs.stale if rs else False,
            risk_unavailable=rs.unavailable if rs else True,
        ))
    return out


@router.get("/{sme_id}", response_model=SMEDetailOut)
def get_sme(sme_id: int, db: Session = Depends(get_db)):
    sme = db.get(SME, sme_id)
    if sme is None:
        raise sme_error("NOT_FOUND", f"No SME found with id {sme_id}.")
    rs = _ensure_score(db, sme)
    return SMEDetailOut(
        id=sme.id, name=sme.name, sector=sme.sector, city=sme.city, description=sme.description,
        founded_year=sme.founded_year, employees=sme.employees, funding_goal=sme.funding_goal,
        status=sme.status, filings=sme.filings, risk_score=_risk_score_out(rs),
    )


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
