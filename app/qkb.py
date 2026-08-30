"""Simulated QKB (Qendra Kombetare e Biznesit) filing lookup.

There is no public, machine-readable QKB API a student prototype can call for
real financial filings (thesis section 10: real QKB data collection is
explicitly out of scope, left as fieldwork for the empirical component). This
module stands in for that integration point so the SME signup flow can still
demonstrate the intended shape of the real thing: a business enters its NIPT
(tax ID), the platform "pulls" the last four years of filings from QKB, and
those parsed figures -- not manually typed numbers -- are what get scored.

The data returned is generated, not fetched -- but it is *deterministic* per
NIPT (seeded from a hash of it), so looking the same NIPT up twice returns
the same four years, the way a real read-only lookup would. This reuses the
exact generator (`app.synth_filings`) that produces the rest of the
platform's simulated filings, so the numbers have the same realistic shape
and still satisfy the fundamental accounting identity.
"""

import datetime as dt
import hashlib
import random
import re

from app.synth_filings import PROFILES, make_filing_series

NIPT_PATTERN = re.compile(r"^[A-Za-z][0-9]{8}[A-Za-z]$")
LOOKUP_YEARS = 4


def is_valid_nipt(nipt: str) -> bool:
    return bool(NIPT_PATTERN.match(nipt.strip()))


def _seed_for(nipt: str) -> int:
    digest = hashlib.sha256(nipt.strip().upper().encode()).hexdigest()
    return int(digest[:8], 16)


def fetch_qkb_filings(nipt: str, current_year: int) -> list[dict]:
    """Deterministically "retrieves" the last `LOOKUP_YEARS` years of filings
    for a NIPT. Same NIPT always returns the same series."""
    rng = random.Random(_seed_for(nipt))
    profile = rng.choice(PROFILES)
    start_year = current_year - LOOKUP_YEARS
    return make_filing_series(rng, profile, start_year, LOOKUP_YEARS)


def lookup(nipt: str, business_name: str, current_year: int = None) -> dict:
    current_year = current_year or dt.date.today().year
    filings = fetch_qkb_filings(nipt, current_year)
    return {
        "nipt": nipt.strip().upper(),
        "business_name": business_name,
        "source": "QKB (demo i simuluar)",
        "retrieved_at": dt.datetime.utcnow(),
        "filings": filings,
        "disclaimer": (
            "Ky është një demonstrim i simuluar i integrimit me QKB për qëllime të "
            "këtij prototipi kërkimor. Nuk është lidhje e vërtetë me sistemin e QKB-së; "
            "shifrat gjenerohen në mënyrë deterministe nga NIPT-i, nuk tërhiqen nga të dhëna reale."
        ),
    }
