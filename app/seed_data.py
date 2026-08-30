"""Generates a simulated QKB-style SME dataset for the prototype.

This is synthetic data standing in for a real QKB filings sample (thesis section
6/10: real QKB collection is out of scope for the prototype and left as a
documented data-access risk). Profiles are deliberately spread across strong,
average, and weak financials -- including some with fabricated-looking, overly
round figures -- so the marketplace demonstrates the full Low/Medium/High risk
tier range and the Benford check has something to flag.
"""

import datetime as dt
import random

from sqlalchemy.orm import Session

from app.models import AdminAction, Filing, Investment, Investor, RiskScore, SME
from app.risk_scoring import compute_risk_score

random.seed(42)

SECTORS = ["Tourism & Hospitality", "Agro-processing", "Manufacturing", "IT Services", "Retail & Trade"]
CITIES = ["Tirana", "Durres", "Vlore", "Korce", "Shkoder", "Berat", "Saranda"]

NAME_STEMS = {
    "Tourism & Hospitality": ["Riviera Stay", "Albanian Coast Tours", "Guesthouse Illyria", "Lake View Retreat"],
    "Agro-processing": ["Malësia Foods", "Olive Grove Co-op", "Highland Dairy", "Sunfield Agro"],
    "Manufacturing": ["Adriatic Textiles", "Tirana Metalworks", "Balkan Furniture", "Precision Parts SHPK"],
    "IT Services": ["Tirana Softworks", "Eagle Code Studio", "Nexus Digital", "Skanderbeg Systems"],
    "Retail & Trade": ["Korce Trading House", "Family Market Group", "Durres Wholesale", "Northgate Retail"],
}

CURRENT_YEAR = dt.date.today().year


def _make_filing_series(profile: str, start_year: int, n_years: int):
    """profile in {'strong', 'average', 'weak', 'volatile', 'suspicious'}."""
    filings = []
    revenue = random.uniform(80_000, 400_000)
    for i in range(n_years):
        year = start_year + i

        if profile == "strong":
            revenue *= random.uniform(1.08, 1.20)
            margin = random.uniform(0.10, 0.18)
            current_ratio = random.uniform(1.8, 2.6)
            debt_equity = random.uniform(0.2, 0.6)
        elif profile == "average":
            revenue *= random.uniform(0.98, 1.10)
            margin = random.uniform(0.03, 0.08)
            current_ratio = random.uniform(1.1, 1.5)
            debt_equity = random.uniform(1.0, 1.8)
        elif profile == "weak":
            revenue *= random.uniform(0.85, 1.02)
            margin = random.uniform(-0.05, 0.02)
            current_ratio = random.uniform(0.5, 0.95)
            debt_equity = random.uniform(2.5, 4.5)
        elif profile == "volatile":
            revenue *= random.uniform(0.75, 1.35)
            margin = random.uniform(-0.08, 0.14)
            current_ratio = random.uniform(0.8, 2.0)
            debt_equity = random.uniform(0.8, 2.8)
        else:  # suspicious: round, Benford-unfriendly numbers
            revenue = round(random.choice([100_000, 150_000, 200_000, 250_000, 300_000]) * (1 + i * 0.1), -3)
            margin = 0.10
            current_ratio = 1.5
            debt_equity = 1.0

        net_income = revenue * margin
        cogs = revenue * random.uniform(0.55, 0.75) if profile != "suspicious" else round(revenue * 0.6, -3)
        current_liabilities = round(revenue * random.uniform(0.15, 0.35), 0) if profile != "suspicious" else round(revenue * 0.2, -3)
        current_assets = round(current_liabilities * current_ratio, 0) if profile != "suspicious" else round(current_liabilities * 1.5, -3)
        equity = round(revenue * random.uniform(0.3, 0.6), 0) if profile != "suspicious" else round(revenue * 0.4, -3)
        total_liabilities = round(equity * debt_equity, 0) if profile != "suspicious" else round(equity * 1.0, -3)
        total_assets = round(current_assets + total_liabilities + equity - current_liabilities, 0)

        filed_date = dt.date(year + 1, random.choice([3, 4, 5, 6]), random.randint(1, 28))
        is_late = filed_date.month >= 6

        filings.append(dict(
            year=year, revenue=round(revenue, 0), cogs=round(cogs, 0), net_income=round(net_income, 0),
            current_assets=current_assets, current_liabilities=current_liabilities,
            total_assets=total_assets, total_liabilities=total_liabilities, equity=equity,
            filed_date=filed_date, is_late=is_late,
        ))
    return filings


PROFILES = ["strong", "strong", "average", "average", "average", "weak", "weak", "volatile", "suspicious"]


def seed_if_empty(db: Session) -> None:
    if db.query(SME).count() > 0:
        return

    idx = 0
    smes = []
    for sector, names in NAME_STEMS.items():
        for name in names:
            profile = PROFILES[idx % len(PROFILES)]
            idx += 1
            n_years = random.choice([1, 2, 2, 3])
            start_year = CURRENT_YEAR - n_years
            sme = SME(
                name=name,
                sector=sector,
                city=random.choice(CITIES),
                description=(
                    f"{name} is a {sector.lower()} business based in {random.choice(CITIES)}, Albania, "
                    f"seeking diaspora capital to fund working-capital and expansion needs."
                ),
                founded_year=random.randint(CURRENT_YEAR - 15, CURRENT_YEAR - 2),
                employees=random.randint(3, 60),
                funding_goal=round(random.uniform(15_000, 120_000), -2),
                status="pending",
            )
            db.add(sme)
            db.flush()  # get sme.id

            for f in _make_filing_series(profile, start_year, n_years):
                db.add(Filing(sme_id=sme.id, **f))
            db.flush()

            smes.append(sme)

    db.commit()

    # Vet most SMEs so the public marketplace isn't empty; leave a couple pending
    # and one rejected, to demonstrate the admin workflow realistically.
    for i, sme in enumerate(smes):
        db.refresh(sme)
        result = compute_risk_score(sme.filings, CURRENT_YEAR)
        db.add(RiskScore(
            sme_id=sme.id,
            based_on_filing_year=result.based_on_filing_year,
            score=result.score, tier=result.tier,
            liquidity_score=result.liquidity_score, leverage_score=result.leverage_score,
            profitability_score=result.profitability_score, benford_score=result.benford_score,
            stale=result.stale, unavailable=result.unavailable, reason=result.reason,
            notes_json=__import__("json").dumps(result.notes),
        ))

        if i < len(smes) - 3:
            sme.status = "vetted"
            db.add(AdminAction(sme_id=sme.id, actor="seed-admin", action="approve",
                                notes="Auto-approved during prototype seeding."))
        elif i == len(smes) - 1:
            sme.status = "rejected"
            db.add(AdminAction(sme_id=sme.id, actor="seed-admin", action="reject",
                                notes="Insufficient filing history for initial vetting (seed demo)."))
        # else: leave status='pending' for the admin queue demo

    db.commit()

    # Seed one demo investor + a couple of simulated investments for the portfolio demo.
    investor = Investor(name="Elira Hoxha", email="elira.demo@example.com", country_of_residence="United Kingdom")
    db.add(investor)
    db.flush()

    vetted = [s for s in smes if s.status == "vetted"]
    for sme in vetted[:2]:
        db.add(Investment(
            investor_id=investor.id, sme_id=sme.id, amount=random.choice([100, 250, 500]),
            currency="EUR", status="committed", idempotency_key=f"seed-{investor.id}-{sme.id}",
        ))
    db.commit()
