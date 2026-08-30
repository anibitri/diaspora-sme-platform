import datetime as dt

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# SME / filings / risk score
# ---------------------------------------------------------------------------

class FilingOut(BaseModel):
    year: int
    revenue: float
    cogs: float
    net_income: float
    current_assets: float
    current_liabilities: float
    total_assets: float
    total_liabilities: float
    equity: float
    filed_date: dt.date
    is_late: bool

    model_config = {"from_attributes": True}


class RiskScoreOut(BaseModel):
    computed_at: dt.datetime
    based_on_filing_year: int | None
    score: float | None
    tier: str | None
    liquidity_score: float | None
    leverage_score: float | None
    profitability_score: float | None
    benford_score: float | None
    stale: bool
    unavailable: bool
    reason: str | None
    notes: dict

    model_config = {"from_attributes": True}


class SMESummaryOut(BaseModel):
    id: int
    name: str
    sector: str
    city: str
    founded_year: int
    employees: int
    funding_goal: float
    status: str
    risk_score: float | None = None
    risk_tier: str | None = None
    risk_stale: bool = False
    risk_unavailable: bool = False

    model_config = {"from_attributes": True}


class SMEDetailOut(BaseModel):
    id: int
    name: str
    sector: str
    city: str
    description: str
    founded_year: int
    employees: int
    funding_goal: float
    status: str
    filings: list[FilingOut]
    risk_score: RiskScoreOut | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Investors
# ---------------------------------------------------------------------------

class InvestorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    country_of_residence: str = Field(min_length=1, max_length=100)


class InvestorOut(BaseModel):
    id: int
    name: str
    email: str
    country_of_residence: str
    created_at: dt.datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Investments
# ---------------------------------------------------------------------------

class InvestmentCreate(BaseModel):
    investor_id: int
    sme_id: int
    amount: float = Field(gt=0)
    currency: str = Field(default="EUR", max_length=10)


class InvestmentOut(BaseModel):
    id: int
    investor_id: int
    sme_id: int
    sme_name: str | None = None
    amount: float
    currency: str
    status: str
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class PortfolioOut(BaseModel):
    investor: InvestorOut
    investments: list[InvestmentOut]
    total_committed: float


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class AdminActionOut(BaseModel):
    id: int
    sme_id: int | None
    actor: str
    action: str
    notes: str
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class AdminDecision(BaseModel):
    notes: str = Field(default="", max_length=1000)
