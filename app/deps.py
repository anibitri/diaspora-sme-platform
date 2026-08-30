"""Prototype-only admin auth.

This is a single shared-secret header check, NOT real authentication. It exists
purely to demonstrate role separation (investor vs. admin surface) in the UI and
API, per thesis section 5 ("Admin/vetting layer"). A production platform would
need real auth with MFA and per-admin accounts (thesis section 12.1) -- explicitly
out of scope for this prototype (thesis section 10).
"""

from fastapi import Header

from app.errors import auth_error

ADMIN_TOKEN = "demo-admin-token"


def require_admin(x_admin_token: str | None = Header(default=None)) -> str:
    if x_admin_token != ADMIN_TOKEN:
        raise auth_error(
            "INSUFFICIENT_PERMISSIONS",
            "A valid admin token is required for this action.",
            {"hint": "Send header X-Admin-Token: demo-admin-token (prototype only)."},
        )
    return "admin"
