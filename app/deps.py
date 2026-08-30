"""Prototype-only admin auth.

This is a single shared-secret header check, NOT real authentication. It exists
purely to demonstrate role separation (investor vs. admin surface) in the UI and
API, per thesis section 5 ("Admin/vetting layer"). A production platform would
need real auth with MFA and per-admin accounts (thesis section 12.1) -- explicitly
out of scope for this prototype (thesis section 10).
"""

import os

from fastapi import Header, Request

from app.errors import AppError, auth_error
from app.rate_limit import rate_limit_auth

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "demo-admin-token")


def require_admin(request: Request, x_admin_token: str | None = Header(default=None)) -> str:
    if x_admin_token != ADMIN_TOKEN:
        try:
            rate_limit_auth(request)
        except AppError:
            raise
        raise auth_error(
            "INSUFFICIENT_PERMISSIONS",
            "A valid admin token is required for this action.",
            {"hint": "Set ADMIN_TOKEN env var; defaults to demo-admin-token (prototype only)."},
        )
    return "admin"
