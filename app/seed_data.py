"""Generates a simulated QKB-style SME dataset for the prototype.

This is synthetic data standing in for a real QKB filings sample (thesis section
6/10: real QKB collection is out of scope for the prototype and left as a
documented data-access risk). Profiles are deliberately spread across strong,
average, weak, volatile, distressed, and fabricated-looking financials so the
marketplace demonstrates the full Low/Medium/High risk tier range -- including
negative equity -- and the Benford check has something to flag.

Every generated filing satisfies the fundamental accounting identity
(total assets = total liabilities + equity) by construction: total_assets is
always *derived* from total_liabilities + equity, never generated
independently, and current-period figures are capped so they never exceed
their whole-balance-sheet counterpart. Earlier versions of this generator
computed total_assets from an unrelated formula and produced balance sheets
that didn't balance -- worth flagging explicitly since a thesis reviewer with
finance literacy would notice immediately.

These seeded SMEs represent filings "sampled from QKB" (per thesis section 6)
rather than real platform signups, so they intentionally have no password/login
-- only businesses that go through POST /api/smes/signup get one.
"""

import datetime as dt
import random

from sqlalchemy.orm import Session

from app.auth import hash_password
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

FIRST_NAMES = ["Elira", "Arben", "Blerina", "Gentian", "Ledia", "Fatjon", "Anisa", "Dritan", "Klea", "Ermal"]
LAST_NAMES = ["Hoxha", "Krasniqi", "Berisha", "Shehu", "Doda", "Meta", "Kola", "Prifti", "Xhafa", "Gega"]

CURRENT_YEAR = dt.date.today().year


def _slugify(name: str) -> str:
    keep = "".join(c.lower() if c.isalnum() else " " for c in name)
    return "-".join(keep.split())


def _make_contact(name: str) -> dict:
    slug = _slugify(name)
    return {
        "contact_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        "contact_email": f"info@{slug}.al",
        "contact_phone": f"+355 {random.choice(['67', '68', '69'])} {random.randint(100, 999)} {random.randint(1000, 9999)}",
        "website": f"https://www.{slug}.al",
    }


def _build_balance_sheet(revenue, equity_frac, debt_ratio, current_ratio_target, cl_frac, distressed=False):
    """Returns (current_assets, current_liabilities, total_assets, total_liabilities, equity),
    always satisfying total_assets == total_liabilities + equity exactly."""
    if distressed:
        equity = -round(revenue * equity_frac, 0)
        total_liabilities = round(revenue * debt_ratio, 0)
    else:
        equity = round(revenue * equity_frac, 0)
        total_liabilities = round(equity * debt_ratio, 0)

    total_assets = total_liabilities + equity
    if total_assets <= revenue * 0.05:
        # guard against a degenerate near-zero/negative asset base
        total_assets = round(revenue * 0.15, 0)
        total_liabilities = total_assets - equity

    current_liabilities = round(total_liabilities * cl_frac, 0)
    current_assets = round(min(current_liabilities * current_ratio_target, total_assets * 0.95), 0)

    return current_assets, current_liabilities, total_assets, total_liabilities, equity


def _make_filing_series(profile: str, start_year: int, n_years: int):
    """profile in {'strong', 'average', 'weak', 'volatile', 'distressed', 'suspicious'}."""
    filings = []
    revenue = random.uniform(80_000, 400_000)
    suspicious_base = random.choice([100_000, 150_000, 200_000, 250_000, 300_000])

    for i in range(n_years):
        year = start_year + i
        distressed = False

        if profile == "strong":
            revenue *= random.uniform(1.08, 1.20)
            margin = random.uniform(0.10, 0.18)
            current_ratio_target = random.uniform(1.8, 2.6)
            debt_ratio = random.uniform(0.2, 0.6)
            equity_frac = random.uniform(0.35, 0.55)
            cl_frac = random.uniform(0.3, 0.5)
        elif profile == "average":
            revenue *= random.uniform(0.98, 1.10)
            margin = random.uniform(0.03, 0.08)
            current_ratio_target = random.uniform(1.1, 1.5)
            debt_ratio = random.uniform(1.0, 1.8)
            equity_frac = random.uniform(0.25, 0.45)
            cl_frac = random.uniform(0.45, 0.65)
        elif profile == "weak":
            revenue *= random.uniform(0.85, 1.02)
            margin = random.uniform(-0.05, 0.02)
            current_ratio_target = random.uniform(0.5, 0.95)
            debt_ratio = random.uniform(2.5, 4.5)
            equity_frac = random.uniform(0.12, 0.3)
            cl_frac = random.uniform(0.55, 0.8)
        elif profile == "volatile":
            revenue *= random.uniform(0.75, 1.35)
            margin = random.uniform(-0.08, 0.14)
            current_ratio_target = random.uniform(0.8, 2.0)
            debt_ratio = random.uniform(0.8, 2.8)
            equity_frac = random.uniform(0.2, 0.5)
            cl_frac = random.uniform(0.4, 0.7)
        elif profile == "distressed":
            distressed = True
            revenue *= random.uniform(0.7, 0.95)
            margin = random.uniform(-0.18, -0.02)
            current_ratio_target = random.uniform(0.35, 0.8)
            debt_ratio = random.uniform(0.9, 1.4)  # total liabilities as a fraction of revenue
            equity_frac = random.uniform(0.05, 0.25)  # magnitude of the equity deficit
            cl_frac = random.uniform(0.5, 0.8)
        else:  # suspicious: round, Benford-unfriendly numbers, still balance-sheet consistent
            revenue = round(suspicious_base * (1 + i * 0.12), -3)
            margin = 0.10
            current_ratio_target = 1.5
            debt_ratio = 1.0
            equity_frac = 0.40
            cl_frac = 0.50

        net_income = round(revenue * margin, 0)
        cogs = revenue * random.uniform(0.55, 0.75) if profile != "suspicious" else round(revenue * 0.6, -3)

        current_assets, current_liabilities, total_assets, total_liabilities, equity = _build_balance_sheet(
            revenue, equity_frac, debt_ratio, current_ratio_target, cl_frac, distressed=distressed,
        )
        if profile == "suspicious":
            # round everything to the nearest thousand while preserving the identity exactly
            equity = round(equity, -3)
            total_liabilities = round(total_liabilities, -3)
            total_assets = total_liabilities + equity
            current_liabilities = round(current_liabilities, -3) or round(total_liabilities * 0.5, -3)
            current_assets = round(min(current_liabilities * 1.5, total_assets * 0.95), -3)

        filed_date = dt.date(year + 1, random.choice([3, 4, 5, 6]), random.randint(1, 28))
        is_late = filed_date.month >= 6

        filings.append(dict(
            year=year, revenue=round(revenue, 0), cogs=round(cogs, 0), net_income=net_income,
            current_assets=current_assets, current_liabilities=current_liabilities,
            total_assets=total_assets, total_liabilities=total_liabilities, equity=equity,
            filed_date=filed_date, is_late=is_late,
        ))
    return filings


PROFILES = ["strong", "strong", "average", "average", "average", "weak", "weak", "volatile", "distressed", "suspicious"]


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
            contact = _make_contact(name)
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
                **contact,
                # No password_hash: seeded/sampled SMEs have no platform login (see module docstring).
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

    # Seed one demo investor (password below, documented in README) + a couple
    # of simulated investments for the portfolio demo.
    investor = Investor(
        name="Elira Hoxha", email="elira.demo@example.com", country_of_residence="United Kingdom",
        password_hash=hash_password("demo1234"),
    )
    db.add(investor)
    db.flush()

    vetted = [s for s in smes if s.status == "vetted"]
    for sme in vetted[:2]:
        db.add(Investment(
            investor_id=investor.id, sme_id=sme.id, amount=random.choice([100, 250, 500]),
            currency="EUR", status="committed", idempotency_key=f"seed-{investor.id}-{sme.id}",
        ))
    db.commit()
