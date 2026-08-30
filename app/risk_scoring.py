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
        return 0.0, "Detyrimet korrente janë zero ose mungojnë; likuiditeti nuk mund të vlerësohet dhe trajtohet si rrezik i lartë."
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
    return pts, f"Likuiditeti korrent {ratio:.2f} (aktive korrente / detyrime korrente)."


def _score_leverage(total_liabilities: float, equity: float) -> tuple[float, str]:
    if equity <= 0:
        return 0.0, "Kapitali është zero ose negativ; leva trajtohet si rrezik maksimal."
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
    return pts, f"Raporti borxh-kapital {ratio:.2f} (detyrime gjithsej / kapital)."


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
        notes.append(f"Marzhi neto {margin:.1%}.")
    else:
        notes.append("Të ardhurat janë zero ose mungojnë; marzhi neto nuk mund të llogaritej.")

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
        notes.append(f"Rritja e të ardhurave {growth:+.1%} nga viti në vit.")
    else:
        growth_pts = 5.0
        notes.append("Vetëm një vit bilanci në dispozicion; prirja e rritjes nuk u vlerësua (aplikohet një vlerësim neutral).")

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
            f"Vetëm {n} shifra të përdorshme në dispozicion nga bilancet "
            f"(më pak se minimumi i rekomanduar prej {MIN_BENFORD_OBSERVATIONS}); "
            "përputhshmëria me Ligjin e Benford-it nuk është statistikisht e besueshme në këtë "
            "madhësi kampioni, prandaj aplikohet një vlerësim neutral. Trajtoje vetëm si indikativ."
        )
        return 12.0, note, None

    counts = {d: 0 for d in range(1, 10)}
    for d in digits:
        counts[d] += 1
    observed = {d: counts[d] / n for d in range(1, 10)}
    mad = sum(abs(observed[d] - BENFORD_EXPECTED[d]) for d in range(1, 10)) / 9

    # Nigrini (2012) MAD thresholds for the first-digit test.
    if mad <= 0.006:
        pts, level = 25.0, "përputhshmëri e ngushtë"
    elif mad <= 0.012:
        pts, level = 20.0, "përputhshmëri e pranueshme"
    elif mad <= 0.015:
        pts, level = 12.0, "përputhshmëri kufitare"
    else:
        pts, level = 4.0, "mospërputhshmëri"

    note = (
        f"Testi i shifrës së parë sipas Ligjit të Benford-it mbi {n} shifra të grupuara: MAD={mad:.4f} ({level}). "
        "Ky flamurizon modele të pazakonta shifrash si sinjal anomalie me kosto të ulët, jo si provë "
        "keqdeklarimi apo mashtrimi -- duhet lexuar bashkë me pikët e raporteve, jo veçmas."
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
            f"Bilanci më i fundit është nga {latest.year}, më shumë se {STALE_AFTER_YEARS} vjet i vjetër. "
            "Vlerësimi shfaqet por flamurizohet si potencialisht i vjetëruar, në vend që të fshihet."
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
