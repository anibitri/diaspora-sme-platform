import datetime as dt

from fastapi import APIRouter, Depends

from app.errors import validation_error
from app.qkb import lookup
from app.rate_limit import rate_limit_auth
from app.schemas import QKBLookupIn, QKBLookupOut

router = APIRouter(prefix="/api/qkb", tags=["qkb"])

CURRENT_YEAR = dt.date.today().year


@router.post("/lookup", response_model=QKBLookupOut, dependencies=[Depends(rate_limit_auth)])
def qkb_lookup(payload: QKBLookupIn):
    """Simulated demo: "pulls" the last four years of filings for a NIPT from
    QKB. See app/qkb.py for why this is generated rather than fetched, and
    why it is still safe to treat as a stand-in for a real integration point
    (deterministic per NIPT, same accounting-identity guarantees as the rest
    of the platform's simulated data)."""
    if not payload.nipt:
        raise validation_error("INVALID_NIPT", "A NIPT is required to look up QKB filings.")
    return lookup(payload.nipt, payload.business_name, CURRENT_YEAR)
