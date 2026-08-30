import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SME(Base):
    __tablename__ = "smes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    sector: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    founded_year: Mapped[int] = mapped_column(Integer)
    employees: Mapped[int] = mapped_column(Integer)
    funding_goal: Mapped[float] = mapped_column(Float, default=0.0)
    # pending -> vetted -> (delisted) | rejected
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    # Contact / links (thesis section 5: SMEs need to be reachable by interested investors).
    contact_name: Mapped[str] = mapped_column(String(200), default="")
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True, unique=True)
    contact_phone: Mapped[str] = mapped_column(String(50), default="")
    website: Mapped[str] = mapped_column(String(300), default="")

    # Auth: only set for SMEs that self-registered through the signup flow.
    # Seeded/sampled SMEs (thesis section 6: "sampled from public QKB filings")
    # have no login -- they represent filing data, not a platform account.
    password_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)

    filings: Mapped[list["Filing"]] = relationship(
        back_populates="sme", cascade="all, delete-orphan", order_by="Filing.year"
    )
    risk_scores: Mapped[list["RiskScore"]] = relationship(
        back_populates="sme", cascade="all, delete-orphan", order_by="RiskScore.computed_at"
    )
    investments: Mapped[list["Investment"]] = relationship(
        back_populates="sme", cascade="all, delete-orphan"
    )


class Filing(Base):
    """A single year's QKB-style annual filing for an SME (simulated data)."""

    __tablename__ = "filings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sme_id: Mapped[int] = mapped_column(ForeignKey("smes.id"))
    year: Mapped[int] = mapped_column(Integer)

    revenue: Mapped[float] = mapped_column(Float)
    cogs: Mapped[float] = mapped_column(Float)
    net_income: Mapped[float] = mapped_column(Float)
    current_assets: Mapped[float] = mapped_column(Float)
    current_liabilities: Mapped[float] = mapped_column(Float)
    total_assets: Mapped[float] = mapped_column(Float)
    total_liabilities: Mapped[float] = mapped_column(Float)
    equity: Mapped[float] = mapped_column(Float)

    filed_date: Mapped[dt.date] = mapped_column(DateTime)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)

    sme: Mapped["SME"] = relationship(back_populates="filings")


class RiskScore(Base):
    """A versioned, explainable risk-score snapshot for an SME."""

    __tablename__ = "risk_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sme_id: Mapped[int] = mapped_column(ForeignKey("smes.id"))
    computed_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    based_on_filing_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tier: Mapped[str | None] = mapped_column(String(20), nullable=True)

    liquidity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    leverage_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    profitability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    benford_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    stale: Mapped[bool] = mapped_column(Boolean, default=False)
    unavailable: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_json: Mapped[str] = mapped_column(Text, default="{}")

    sme: Mapped["SME"] = relationship(back_populates="risk_scores")


class Investor(Base):
    __tablename__ = "investors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    country_of_residence: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    investments: Mapped[list["Investment"]] = relationship(back_populates="investor")


class Investment(Base):
    """A simulated investment commitment. No real payment rails (prototype scope)."""

    __tablename__ = "investments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investor_id: Mapped[int] = mapped_column(ForeignKey("investors.id"))
    sme_id: Mapped[int] = mapped_column(ForeignKey("smes.id"))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="EUR")
    status: Mapped[str] = mapped_column(String(20), default="committed")
    idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True, unique=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    investor: Mapped["Investor"] = relationship(back_populates="investments")
    sme: Mapped["SME"] = relationship(back_populates="investments")


class AdminAction(Base):
    """Append-only audit log of admin/vetting decisions."""

    __tablename__ = "admin_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sme_id: Mapped[int | None] = mapped_column(ForeignKey("smes.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(50))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
