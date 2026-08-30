from fastapi import APIRouter, Depends, Header
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import AppError, investment_error, sme_error
from app.models import Investment, Investor, SME
from app.schemas import InvestmentCreate, InvestmentOut

router = APIRouter(prefix="/api/investments", tags=["investments"])

MIN_INVESTMENT_EUR = 25.0


def _out(inv: Investment) -> InvestmentOut:
    return InvestmentOut(
        id=inv.id, investor_id=inv.investor_id, sme_id=inv.sme_id,
        sme_name=inv.sme.name if inv.sme else None,
        amount=inv.amount, currency=inv.currency, status=inv.status, created_at=inv.created_at,
    )


@router.post("", response_model=InvestmentOut)
def create_investment(
    payload: InvestmentCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    """Simulated investment commitment -- no real payment rails (thesis section 5).
    Honors an Idempotency-Key header so a retried request after a dropped
    connection cannot be double-counted (thesis section 12.2)."""

    if idempotency_key:
        existing = db.query(Investment).filter(Investment.idempotency_key == idempotency_key).one_or_none()
        if existing is not None:
            return _out(existing)

    investor = db.get(Investor, payload.investor_id)
    if investor is None:
        raise AppError("AUTH_UNKNOWN_INVESTOR", f"No investor found with id {payload.investor_id}.", 404)

    sme = db.get(SME, payload.sme_id)
    if sme is None:
        raise sme_error("NOT_FOUND", f"No SME found with id {payload.sme_id}.")

    if sme.status != "vetted":
        raise investment_error(
            "SME_CLOSED",
            f"{sme.name} is not currently open for investment (status: {sme.status}).",
            details={"sme_status": sme.status},
        )

    if payload.amount < MIN_INVESTMENT_EUR:
        raise investment_error(
            "BELOW_MINIMUM",
            f"The minimum simulated investment is EUR {MIN_INVESTMENT_EUR:.0f}.",
            details={"minimum": MIN_INVESTMENT_EUR},
        )

    investment = Investment(
        investor_id=investor.id, sme_id=sme.id, amount=payload.amount,
        currency=payload.currency, status="committed", idempotency_key=idempotency_key,
    )
    db.add(investment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(Investment).filter(Investment.idempotency_key == idempotency_key).one()
        return _out(existing)

    db.refresh(investment)
    return _out(investment)


@router.get("/{investment_id}", response_model=InvestmentOut)
def get_investment(investment_id: int, db: Session = Depends(get_db)):
    inv = db.get(Investment, investment_id)
    if inv is None:
        raise AppError("INVESTMENT_NOT_FOUND", f"No investment found with id {investment_id}.", 404)
    return _out(inv)
