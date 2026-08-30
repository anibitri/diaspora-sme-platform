import datetime as dt
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.errors import sme_error
from app.models import AdminAction, RiskScore, SME
from app.returns import estimate_return_pct
from app.risk_scoring import compute_risk_score
from app.schemas import AdminActionOut, AdminDecision, SMESummaryOut

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

CURRENT_YEAR = dt.date.today().year


def _summary(sme: SME) -> SMESummaryOut:
    rs = max(sme.risk_scores, key=lambda r: r.computed_at) if sme.risk_scores else None
    tier = rs.tier if rs and not rs.unavailable else None
    return SMESummaryOut(
        id=sme.id, name=sme.name, sector=sme.sector, city=sme.city,
        founded_year=sme.founded_year, employees=sme.employees, funding_goal=sme.funding_goal,
        status=sme.status,
        contact_name=sme.contact_name, contact_email=sme.contact_email,
        investment_type=sme.investment_type, expected_return_pct=estimate_return_pct(sme.investment_type, tier),
        risk_score=rs.score if rs else None, risk_tier=rs.tier if rs else None,
        risk_stale=rs.stale if rs else False, risk_unavailable=rs.unavailable if rs else True,
    )


def _ensure_scored(db: Session, sme: SME) -> None:
    if sme.risk_scores or not sme.filings:
        return
    result = compute_risk_score(sme.filings, CURRENT_YEAR)
    db.add(RiskScore(
        sme_id=sme.id, based_on_filing_year=result.based_on_filing_year,
        score=result.score, tier=result.tier,
        liquidity_score=result.liquidity_score, leverage_score=result.leverage_score,
        profitability_score=result.profitability_score, benford_score=result.benford_score,
        stale=result.stale, unavailable=result.unavailable, reason=result.reason,
        notes_json=json.dumps(result.notes),
    ))


@router.get("/smes", response_model=list[SMESummaryOut])
def list_for_vetting(status: str | None = "pending", db: Session = Depends(get_db)):
    query = db.query(SME)
    if status:
        query = query.filter(SME.status == status)
    return [_summary(sme) for sme in query.order_by(SME.created_at).all()]


@router.post("/smes/{sme_id}/approve", response_model=SMESummaryOut)
def approve_sme(sme_id: int, payload: AdminDecision, db: Session = Depends(get_db)):
    sme = db.get(SME, sme_id)
    if sme is None:
        raise sme_error("NOT_FOUND", f"No SME found with id {sme_id}.")
    if sme.status == "vetted":
        raise sme_error("ALREADY_VETTED", f"{sme.name} is already vetted.", http_status=400)

    _ensure_scored(db, sme)
    sme.status = "vetted"
    db.add(AdminAction(sme_id=sme.id, actor="admin", action="approve", notes=payload.notes))
    db.commit()
    db.refresh(sme)
    return _summary(sme)


@router.post("/smes/{sme_id}/reject", response_model=SMESummaryOut)
def reject_sme(sme_id: int, payload: AdminDecision, db: Session = Depends(get_db)):
    sme = db.get(SME, sme_id)
    if sme is None:
        raise sme_error("NOT_FOUND", f"No SME found with id {sme_id}.")

    sme.status = "rejected"
    db.add(AdminAction(sme_id=sme.id, actor="admin", action="reject", notes=payload.notes))
    db.commit()
    db.refresh(sme)
    return _summary(sme)


@router.post("/smes/{sme_id}/delist", response_model=SMESummaryOut)
def delist_sme(sme_id: int, payload: AdminDecision, db: Session = Depends(get_db)):
    sme = db.get(SME, sme_id)
    if sme is None:
        raise sme_error("NOT_FOUND", f"No SME found with id {sme_id}.")
    if sme.status != "vetted":
        raise sme_error("NOT_FOUND", f"{sme.name} is not currently listed.", http_status=400)

    sme.status = "delisted"
    db.add(AdminAction(sme_id=sme.id, actor="admin", action="delist", notes=payload.notes))
    db.commit()
    db.refresh(sme)
    return _summary(sme)


@router.get("/audit-log", response_model=list[AdminActionOut])
def audit_log(db: Session = Depends(get_db)):
    return db.query(AdminAction).order_by(AdminAction.created_at.desc()).limit(200).all()
