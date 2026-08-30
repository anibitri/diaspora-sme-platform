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
from app.returns import INVESTMENT_TYPES, estimate_return_pct
from app.risk_scoring import compute_risk_score
from app.synth_filings import PROFILES, make_filing_series

random.seed(42)
_RNG = random.Random(42)

INVESTMENT_TYPE_CYCLE = list(INVESTMENT_TYPES.keys())

SECTORS = ["Tourism & Hospitality", "Agro-processing", "Manufacturing", "IT Services", "Retail & Trade"]
CITIES = ["Tirana", "Durres", "Vlore", "Korce", "Shkoder", "Berat", "Saranda"]

# Lowercase Albanian sector phrase used inline in generated descriptions
# ("nje biznes ne sektorin e ...") -- kept separate from the frontend's
# SECTOR_LABELS_SQ (js/api.js) since that one is a display label, not a
# genitive phrase.
SECTOR_LABELS_SQ_LOWER = {
    "Tourism & Hospitality": "turizmit dhe mikpritjes",
    "Agro-processing": "përpunimit bujqësor",
    "Manufacturing": "prodhimit",
    "IT Services": "shërbimeve IT",
    "Retail & Trade": "tregtisë me pakicë",
}

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


def _make_nipt() -> str:
    """A plausible-looking Albanian NIPT (letter + 8 digits + letter) for seeded
    SMEs -- not a real registry number, just shaped like one for the demo."""
    import string
    letter1 = random.choice(string.ascii_uppercase)
    digits = "".join(random.choice(string.digits) for _ in range(8))
    letter2 = random.choice(string.ascii_uppercase)
    return f"{letter1}{digits}{letter2}"


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
                nipt=_make_nipt(),
                investment_type=INVESTMENT_TYPE_CYCLE[idx % len(INVESTMENT_TYPE_CYCLE)],
                sector=sector,
                city=random.choice(CITIES),
                description=(
                    f"{name} është një biznes në sektorin e {SECTOR_LABELS_SQ_LOWER.get(sector, sector)} me bazë "
                    f"në {random.choice(CITIES)}, Shqipëri, që kërkon kapital nga diaspora për të financuar "
                    f"kapitalin qarkullues dhe zgjerimin."
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

            for f in make_filing_series(_RNG, profile, start_year, n_years):
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
                                notes="Miratuar automatikisht gjatë krijimit të të dhënave demo."))
        elif i == len(smes) - 1:
            sme.status = "rejected"
            db.add(AdminAction(sme_id=sme.id, actor="seed-admin", action="reject",
                                notes="Histori e pamjaftueshme bilancesh për vetim fillestar (demo)."))
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
        db.refresh(sme)
        rs = max(sme.risk_scores, key=lambda r: r.computed_at) if sme.risk_scores else None
        tier = rs.tier if rs and not rs.unavailable else None
        db.add(Investment(
            investor_id=investor.id, sme_id=sme.id, amount=random.choice([100, 250, 500]),
            currency="EUR", status="committed", idempotency_key=f"seed-{investor.id}-{sme.id}",
            investment_type=sme.investment_type, expected_return_pct=estimate_return_pct(sme.investment_type, tier),
        ))
    db.commit()
