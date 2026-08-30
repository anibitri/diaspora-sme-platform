import datetime as dt
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

PASSWORD_MIN_LENGTH = 8
NIPT_REGEX = r"^[A-Za-z][0-9]{8}[A-Za-z]$"
InvestmentType = Literal["equity", "debt", "revenue_share"]


# ---------------------------------------------------------------------------
# QKB lookup demo
# ---------------------------------------------------------------------------

class QKBLookupIn(BaseModel):
    nipt: str = Field(min_length=10, max_length=10)
    business_name: str = Field(default="", max_length=200)

    @field_validator("nipt")
    @classmethod
    def nipt_format(cls, v: str) -> str:
        import re
        if not re.match(NIPT_REGEX, v.strip()):
            raise ValueError("NIPT must look like a letter, 8 digits, then a letter (e.g. L71926023W).")
        return v.strip().upper()


class QKBFilingOut(BaseModel):
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


class QKBLookupOut(BaseModel):
    nipt: str
    business_name: str
    source: str
    retrieved_at: dt.datetime
    filings: list[QKBFilingOut]
    disclaimer: str


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
    contact_name: str = ""
    contact_email: str | None = None
    investment_type: str = "equity"
    expected_return_pct: float | None = None
    risk_score: float | None = None
    risk_tier: str | None = None
    risk_stale: bool = False
    risk_unavailable: bool = False

    model_config = {"from_attributes": True}


class SMEDetailOut(BaseModel):
    id: int
    name: str
    nipt: str
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
    investment_type: str
    expected_return_pct: float | None = None
    filings: list[FilingOut]
    risk_score: RiskScoreOut | None

    model_config = {"from_attributes": True}


class SMESignupFiling(BaseModel):
    # One year of a filing pulled from the QKB lookup demo (or entered
    # manually as a fallback). total_assets is deliberately NOT collected
    # here -- it is derived server-side as total_liabilities + equity so a
    # submitted filing can never violate the fundamental accounting identity
    # (assets = liabilities + equity).
    year: int = Field(ge=1900, le=2100)
    revenue: float = Field(gt=0)
    cogs: float = Field(ge=0)
    net_income: float
    current_assets: float = Field(ge=0)
    current_liabilities: float = Field(ge=0)
    total_liabilities: float = Field(ge=0)
    equity: float


class SMESignup(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    nipt: str = Field(min_length=10, max_length=10)
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

    # What kind of investment this business is offering (app.returns.INVESTMENT_TYPES).
    investment_type: InvestmentType = "equity"

    # Up to four years of filings, normally populated from the QKB lookup
    # demo on the signup form (see app/qkb.py) rather than typed by hand.
    filings: list[SMESignupFiling] = Field(min_length=1, max_length=4)

    @field_validator("nipt")
    @classmethod
    def nipt_format(cls, v: str) -> str:
        import re
        if not re.match(NIPT_REGEX, v.strip()):
            raise ValueError("NIPT must look like a letter, 8 digits, then a letter (e.g. L71926023W).")
        return v.strip().upper()

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
    investment_type: str
    expected_return_pct: float
    projected_value_1y: float

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
