"""Shared synthetic-filing generator.

Used by both `seed_data.py` (the initial simulated marketplace) and `qkb.py`
(the simulated "pull the last 4 years from QKB" demo on the signup form) so
there is exactly one place that guarantees every generated filing satisfies
the fundamental accounting identity: total assets = total liabilities +
equity, always *derived* rather than generated independently (see the
data-integrity note in the README).
"""

import datetime as dt
import random

PROFILES = ["strong", "strong", "average", "average", "average", "weak", "weak", "volatile", "distressed", "suspicious"]


def build_balance_sheet(revenue, equity_frac, debt_ratio, current_ratio_target, cl_frac, distressed=False):
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


def make_filing_series(rng: random.Random, profile: str, start_year: int, n_years: int):
    """profile in {'strong', 'average', 'weak', 'volatile', 'distressed', 'suspicious'}.

    `rng` is an explicit random.Random instance (not the global `random` module)
    so callers can seed it deterministically -- the QKB demo lookup relies on
    this to return the same figures for the same NIPT on repeat lookups."""
    filings = []
    revenue = rng.uniform(80_000, 400_000)
    suspicious_base = rng.choice([100_000, 150_000, 200_000, 250_000, 300_000])

    for i in range(n_years):
        year = start_year + i
        distressed = False

        if profile == "strong":
            revenue *= rng.uniform(1.08, 1.20)
            margin = rng.uniform(0.10, 0.18)
            current_ratio_target = rng.uniform(1.8, 2.6)
            debt_ratio = rng.uniform(0.2, 0.6)
            equity_frac = rng.uniform(0.35, 0.55)
            cl_frac = rng.uniform(0.3, 0.5)
        elif profile == "average":
            revenue *= rng.uniform(0.98, 1.10)
            margin = rng.uniform(0.03, 0.08)
            current_ratio_target = rng.uniform(1.1, 1.5)
            debt_ratio = rng.uniform(1.0, 1.8)
            equity_frac = rng.uniform(0.25, 0.45)
            cl_frac = rng.uniform(0.45, 0.65)
        elif profile == "weak":
            revenue *= rng.uniform(0.85, 1.02)
            margin = rng.uniform(-0.05, 0.02)
            current_ratio_target = rng.uniform(0.5, 0.95)
            debt_ratio = rng.uniform(2.5, 4.5)
            equity_frac = rng.uniform(0.12, 0.3)
            cl_frac = rng.uniform(0.55, 0.8)
        elif profile == "volatile":
            revenue *= rng.uniform(0.75, 1.35)
            margin = rng.uniform(-0.08, 0.14)
            current_ratio_target = rng.uniform(0.8, 2.0)
            debt_ratio = rng.uniform(0.8, 2.8)
            equity_frac = rng.uniform(0.2, 0.5)
            cl_frac = rng.uniform(0.4, 0.7)
        elif profile == "distressed":
            distressed = True
            revenue *= rng.uniform(0.7, 0.95)
            margin = rng.uniform(-0.18, -0.02)
            current_ratio_target = rng.uniform(0.35, 0.8)
            debt_ratio = rng.uniform(0.9, 1.4)  # total liabilities as a fraction of revenue
            equity_frac = rng.uniform(0.05, 0.25)  # magnitude of the equity deficit
            cl_frac = rng.uniform(0.5, 0.8)
        else:  # suspicious: round, Benford-unfriendly numbers, still balance-sheet consistent
            revenue = round(suspicious_base * (1 + i * 0.12), -3)
            margin = 0.10
            current_ratio_target = 1.5
            debt_ratio = 1.0
            equity_frac = 0.40
            cl_frac = 0.50

        net_income = round(revenue * margin, 0)
        cogs = revenue * rng.uniform(0.55, 0.75) if profile != "suspicious" else round(revenue * 0.6, -3)

        current_assets, current_liabilities, total_assets, total_liabilities, equity = build_balance_sheet(
            revenue, equity_frac, debt_ratio, current_ratio_target, cl_frac, distressed=distressed,
        )
        if profile == "suspicious":
            # round everything to the nearest thousand while preserving the identity exactly
            equity = round(equity, -3)
            total_liabilities = round(total_liabilities, -3)
            total_assets = total_liabilities + equity
            current_liabilities = round(current_liabilities, -3) or round(total_liabilities * 0.5, -3)
            current_assets = round(min(current_liabilities * 1.5, total_assets * 0.95), -3)

        filed_date = dt.date(year + 1, rng.choice([3, 4, 5, 6]), rng.randint(1, 28))
        is_late = filed_date.month >= 6

        filings.append(dict(
            year=year, revenue=round(revenue, 0), cogs=round(cogs, 0), net_income=net_income,
            current_assets=current_assets, current_liabilities=current_liabilities,
            total_assets=total_assets, total_liabilities=total_liabilities, equity=equity,
            filed_date=filed_date, is_late=is_late,
        ))
    return filings
