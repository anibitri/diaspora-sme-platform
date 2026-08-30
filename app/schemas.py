import datetime as dt

from pydantic import BaseModel, EmailStr, Field, field_validator

PASSWORD_MIN_LENGTH = 8


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
    contact_name: str
    contact_email: str | None
    contact_phone: str
    website: str
    has_login: bool
    filings: list[FilingOut]
    risk_score: RiskScoreOut | None

    model_config = {"from_attributes": True}


class SMESignup(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sector: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    founded_year: int = Field(ge=1900, le=2100)
    employees: int = Field(ge=0, le=100_000)
    funding_goal: float = Field(gt=0)

    contact_name: str = Field(min_length=1, max_length=200)
    contact_email: EmailStr
    contact_phone: str = Field(default="", max_length=50)
    website: str = Field(default="", max_length=300)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=200)

    # First-year filing, provided at signup so the SME enters the vetting
    # queue with real data instead of an empty shell. total_assets is
    # deliberately NOT collected here -- it is derived server-side as
    # total_liabilities + equity so a submitted filing can never violate
    # the fundamental accounting identity (assets = liabilities + equity).
    filing_year: int = Field(ge=1900, le=2100)
    revenue: float = Field(gt=0)
    cogs: float = Field(ge=0)
    net_income: float
    current_assets: float = Field(ge=0)
    current_liabilities: float = Field(ge=0)
    total_liabilities: float = Field(ge=0)
    equity: float

    @field_validator("website")
    @classmethod
    def website_scheme(cls, v: str) -> str:
        if v and not (v.startswith("http://") or v.startswith("https://")):
            return f"https://{v}"
        return v


class SMELogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class SMESessionOut(BaseModel):
    token: str
    sme: SMEDetailOut


# ---------------------------------------------------------------------------
# Investors
# ---------------------------------------------------------------------------

class InvestorSignup(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    country_of_residence: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=200)


class InvestorLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class InvestorOut(BaseModel):
    id: int
    name: str
    email: str
    country_of_residence: str
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class InvestorSessionOut(BaseModel):
    token: str
    investor: InvestorOut


# ---------------------------------------------------------------------------
# Investments
# ---------------------------------------------------------------------------

class InvestmentCreate(BaseModel):
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
