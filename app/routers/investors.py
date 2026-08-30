from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import AppError, validation_error
from app.models import Investor
from app.schemas import InvestorCreate, InvestorOut, InvestmentOut, PortfolioOut

router = APIRouter(prefix="/api/investors", tags=["investors"])


@router.post("", response_model=InvestorOut)
def create_or_get_investor(payload: InvestorCreate, db: Session = Depends(get_db)):
    """Simulated sign-up / login-by-email: no real auth (prototype scope,
    thesis section 10). Re-posting the same email returns the existing profile."""
    existing = db.query(Investor).filter(Investor.email == payload.email).one_or_none()
    if existing:
        return existing

    investor = Investor(name=payload.name, email=payload.email, country_of_residence=payload.country_of_residence)
    db.add(investor)
    db.commit()
    db.refresh(investor)
    return investor


@router.get("/by-email/{email}", response_model=InvestorOut)
def get_investor_by_email(email: str, db: Session = Depends(get_db)):
    investor = db.query(Investor).filter(Investor.email == email).one_or_none()
    if investor is None:
        raise AppError("AUTH_UNKNOWN_INVESTOR", "No investor profile found for that email.", 404)
    return investor


@router.get("/{investor_id}/portfolio", response_model=PortfolioOut)
def get_portfolio(investor_id: int, db: Session = Depends(get_db)):
    investor = db.get(Investor, investor_id)
    if investor is None:
        raise AppError("AUTH_UNKNOWN_INVESTOR", f"No investor found with id {investor_id}.", 404)

    investments = [
        InvestmentOut(
            id=inv.id, investor_id=inv.investor_id, sme_id=inv.sme_id,
            sme_name=inv.sme.name if inv.sme else None,
            amount=inv.amount, currency=inv.currency, status=inv.status, created_at=inv.created_at,
        )
        for inv in investor.investments
    ]
    total = sum(i.amount for i in investments if i.status == "committed")
    return PortfolioOut(investor=investor, investments=investments, total_committed=total)
