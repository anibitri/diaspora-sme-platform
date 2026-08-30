from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import create_session_token, get_current_investor, hash_password, verify_password
from app.database import get_db
from app.errors import AppError, auth_error
from app.models import Investor
from app.rate_limit import rate_limit_auth
from app.routers.investments import _out as _investment_out
from app.schemas import (
    InvestorLogin,
    InvestorOut,
    InvestorSessionOut,
    InvestorSignup,
    PortfolioOut,
)

router = APIRouter(prefix="/api/investors", tags=["investors"])


@router.post("/signup", response_model=InvestorSessionOut, dependencies=[Depends(rate_limit_auth)])
def signup(payload: InvestorSignup, db: Session = Depends(get_db)):
    if db.query(Investor).filter(Investor.email == payload.email).one_or_none():
        raise AppError("AUTH_EMAIL_TAKEN", "An investor account with that email already exists. Try logging in.", 409)

    investor = Investor(
        name=payload.name, email=payload.email,
        country_of_residence=payload.country_of_residence,
        password_hash=hash_password(payload.password),
    )
    db.add(investor)
    db.commit()
    db.refresh(investor)
    token = create_session_token("investor", investor.id)
    return InvestorSessionOut(token=token, investor=investor)


@router.post("/login", response_model=InvestorSessionOut, dependencies=[Depends(rate_limit_auth)])
def login(payload: InvestorLogin, db: Session = Depends(get_db)):
    investor = db.query(Investor).filter(Investor.email == payload.email).one_or_none()
    if investor is None or not verify_password(payload.password, investor.password_hash):
        raise auth_error("INVALID_CREDENTIALS", "Incorrect email or password.")
    token = create_session_token("investor", investor.id)
    return InvestorSessionOut(token=token, investor=investor)


@router.get("/me", response_model=InvestorOut)
def get_me(investor: Investor = Depends(get_current_investor)):
    return investor


@router.get("/me/portfolio", response_model=PortfolioOut)
def get_my_portfolio(investor: Investor = Depends(get_current_investor)):
    investments = [_investment_out(inv) for inv in investor.investments]
    total = sum(i.amount for i in investments if i.status == "committed")
    return PortfolioOut(investor=investor, investments=investments, total_committed=total)
