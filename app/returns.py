"""Illustrative expected-return estimates, shown to an investor before they
commit a simulated investment ("how much would I get back after a year?").

This is deliberately a simple, transparent lookup -- not a pricing model.
Real SME equity/debt/revenue-share returns depend on far more than a risk
tier (industry, terms negotiated, macro conditions...), and this prototype
has no real financial-market data to calibrate against. The rates below are
a plausible, clearly-labeled-as-illustrative risk premium: riskier tiers and
higher-upside instrument types get a higher nominal rate, mirroring the
ordinary risk/return relationship any finance-literate reviewer would expect,
without pretending to be an actual asset-pricing model.
"""

INVESTMENT_TYPES = {
    "equity": "Kapital (bashkëpronësi)",
    "debt": "Hua me kthim fiks",
    "revenue_share": "Ndarje të ardhurash",
}

# annual nominal % return by (investment_type, risk_tier)
_RETURN_TABLE = {
    "debt": {"Low": 6.0, "Medium": 9.0, "High": 13.0},
    "equity": {"Low": 8.0, "Medium": 12.0, "High": 18.0},
    "revenue_share": {"Low": 7.0, "Medium": 10.0, "High": 15.0},
}
_DEFAULT_TIER = "Medium"


def investment_type_label(investment_type: str) -> str:
    return INVESTMENT_TYPES.get(investment_type, investment_type)


def estimate_return_pct(investment_type: str, risk_tier: str | None) -> float:
    row = _RETURN_TABLE.get(investment_type, _RETURN_TABLE["equity"])
    return row.get(risk_tier or _DEFAULT_TIER, row[_DEFAULT_TIER])


def projected_value(amount: float, expected_return_pct: float) -> float:
    return round(amount * (1 + expected_return_pct / 100), 2)
