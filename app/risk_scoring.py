"""Explainable SME risk-scoring pipeline.

Designed for a high-informality, low-data market (see thesis section 2.3 / 7.1):
there is no credit-bureau or audit-quality data to lean on, so the model is built
entirely from financial ratios computable from a single annual filing, plus a
Benford's-Law digit-conformity check used as a cheap, indicative anomaly flag
-- NOT a fraud-detection proof. Every component is returned to the caller so the
score is explainable rather than a black box (thesis section 12.5).

Composite score is 0-100, built from four 0-25 sub-scores:
  - liquidity   (current ratio)
  - leverage    (debt-to-equity)
  - profitability (net margin + revenue growth, when >1 year of filings exists)
  - benford     (first-digit conformity of pooled filing figures)
"""

import math
from dataclasses import dataclass, field

STALE_AFTER_YEARS = 2

BENFORD_EXPECTED = {d: math.log10(1 + 1 / d) for d in range(1, 10)}
MIN_BENFORD_OBSERVATIONS = 10


@dataclass
class RiskResult:
    score: float | None
    tier: str | None
    liquidity_score: float | None
    leverage_score: float | None
    profitability_score: float | None
    benford_score: float | None
    based_on_filing_year: int | None
    stale: bool
    unavailable: bool
    reason: str | None
    notes: dict = field(default_factory=dict)


def _tier_for(score: float) -> str:
    if score >= 70:
        return "Low"
    if score >= 40:
        return "Medium"
    return "High"


def _score_liquidity(current_assets: float, current_liabilities: float) -> tuple[float, str]:
    if current_liabilities <= 0:
        return 0.0, "Current liabilities are zero or missing; liquidity cannot be assessed and is treated as high risk."
    ratio = current_assets / current_liabilities
    if ratio >= 2.0:
        pts = 25.0
    elif ratio >= 1.5:
        pts = 20.0
    elif ratio >= 1.2:
        pts = 15.0
    elif ratio >= 1.0:
        pts = 10.0
    elif ratio >= 0.7:
        pts = 5.0
    else:
        pts = 0.0
    return pts, f"Current ratio {ratio:.2f} (current assets / current liabilities)."


def _score_leverage(total_liabilities: float, equity: float) -> tuple[float, str]:
    if equity <= 0:
        return 0.0, "Equity is zero or negative; leverage is treated as maximally risky."
    ratio = total_liabilities / equity
    if ratio <= 0.5:
        pts = 25.0
    elif ratio <= 1.0:
        pts = 20.0
    elif ratio <= 1.5:
        pts = 15.0
    elif ratio <= 2.5:
        pts = 10.0
    elif ratio <= 4.0:
        pts = 5.0
    else:
        pts = 0.0
    return pts, f"Debt-to-equity {ratio:.2f} (total liabilities / equity)."


def _score_profitability(revenue: float, net_income: float, prior_revenue: float | None) -> tuple[float, str]:
    notes = []
    margin_pts = 0.0
    if revenue > 0:
        margin = net_income / revenue
        if margin >= 0.15:
            margin_pts = 15.0
        elif margin >= 0.08:
            margin_pts = 12.0
        elif margin >= 0.03:
            margin_pts = 8.0
        elif margin >= 0.0:
            margin_pts = 4.0
        else:
            margin_pts = 0.0
        notes.append(f"Net margin {margin:.1%}.")
    else:
        notes.append("Revenue is zero or missing; net margin could not be computed.")

    if prior_revenue is not None and prior_revenue > 0:
        growth = (revenue - prior_revenue) / prior_revenue
        if growth >= 0.10:
            growth_pts = 10.0
        elif growth >= 0.0:
            growth_pts = 7.0
        elif growth >= -0.10:
            growth_pts = 3.0
        else:
            growth_pts = 0.0
        notes.append(f"Revenue growth {growth:+.1%} year-on-year.")
    else:
        growth_pts = 5.0
        notes.append("Only one year of filings available; growth trend not assessed (neutral score applied).")

    return margin_pts + growth_pts, " ".join(notes)


def _leading_digit(value: float) -> int | None:
    value = abs(value)
    if value < 1:
        return None
    s = f"{value:.10g}".lstrip("0").lstrip(".")
    for ch in s:
        if ch.isdigit() and ch != "0":
            return int(ch)
    return None


def _score_benford(values: list[float]) -> tuple[float, str, dict | None]:
    digits = [_leading_digit(v) for v in values]
    digits = [d for d in digits if d is not None]
    n = len(digits)

    if n < MIN_BENFORD_OBSERVATIONS:
        note = (
            f"Only {n} usable line-item figures available across filings "
            f"(fewer than the recommended minimum of {MIN_BENFORD_OBSERVATIONS}); "
            "Benford's Law conformity is not statistically reliable at this sample size, "
            "so a neutral score is applied. Treat as indicative only."
        )
        return 12.0, note, None

    counts = {d: 0 for d in range(1, 10)}
    for d in digits:
        counts[d] += 1
    observed = {d: counts[d] / n for d in range(1, 10)}
    mad = sum(abs(observed[d] - BENFORD_EXPECTED[d]) for d in range(1, 10)) / 9

    # Nigrini (2012) MAD thresholds for the first-digit test.
    if mad <= 0.006:
        pts, level = 25.0, "close conformity"
    elif mad <= 0.012:
        pts, level = 20.0, "acceptable conformity"
    elif mad <= 0.015:
        pts, level = 12.0, "marginal conformity"
    else:
        pts, level = 4.0, "nonconformity"

    note = (
        f"Benford's Law first-digit test over {n} pooled figures: MAD={mad:.4f} ({level}). "
        "This flags unusual digit patterns as a low-cost anomaly signal, not proof of "
        "misstatement or fraud -- it should be read alongside the ratio scores, not in isolation."
    )
    distribution = {
        "n": n,
        "mad": round(mad, 4),
        "level": level,
        "digits": list(range(1, 10)),
        "observed": [round(observed[d], 4) for d in range(1, 10)],
        "expected": [round(BENFORD_EXPECTED[d], 4) for d in range(1, 10)],
    }
    return pts, note, distribution


def compute_risk_score(filings: list, current_year: int) -> RiskResult:
    """filings: ORM Filing rows for one SME, any order. Returns an explainable score,
    or an explicit unavailable/stale result rather than a silently wrong default
    (graceful degradation, thesis section 12.2)."""

    if not filings:
        return RiskResult(
            score=None, tier=None,
            liquidity_score=None, leverage_score=None, profitability_score=None, benford_score=None,
            based_on_filing_year=None, stale=False, unavailable=True,
            reason="RISK_MODEL_INSUFFICIENT_DATA",
            notes={"detail": "No filings are on record for this SME."},
        )

    ordered = sorted(filings, key=lambda f: f.year)
    latest = ordered[-1]
    prior = ordered[-2] if len(ordered) >= 2 else None

    liquidity_pts, liquidity_note = _score_liquidity(latest.current_assets, latest.current_liabilities)
    leverage_pts, leverage_note = _score_leverage(latest.total_liabilities, latest.equity)
    profitability_pts, profitability_note = _score_profitability(
        latest.revenue, latest.net_income, prior.revenue if prior else None
    )

    pooled_values: list[float] = []
    for f in ordered:
        pooled_values += [
            f.revenue, f.cogs, f.net_income, f.current_assets,
            f.current_liabilities, f.total_assets, f.total_liabilities, f.equity,
        ]
    benford_pts, benford_note, benford_distribution = _score_benford(pooled_values)

    total = liquidity_pts + leverage_pts + profitability_pts + benford_pts
    stale = (current_year - latest.year) > STALE_AFTER_YEARS

    notes = {
        "liquidity": liquidity_note,
        "leverage": leverage_note,
        "profitability": profitability_note,
        "benford": benford_note,
    }
    if benford_distribution is not None:
        notes["benford_distribution"] = benford_distribution
    if stale:
        notes["staleness"] = (
            f"Most recent filing is from {latest.year}, more than {STALE_AFTER_YEARS} years old. "
            "Score is shown but flagged as potentially outdated rather than hidden."
        )

    return RiskResult(
        score=round(total, 1),
        tier=_tier_for(total),
        liquidity_score=liquidity_pts,
        leverage_score=leverage_pts,
        profitability_score=profitability_pts,
        benford_score=benford_pts,
        based_on_filing_year=latest.year,
        stale=stale,
        unavailable=False,
        reason=None,
        notes=notes,
    )
