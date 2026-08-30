"""Password hashing and signed session tokens.

No third-party auth dependency: PBKDF2-HMAC-SHA256 (stdlib `hashlib`, OWASP-
recommended iteration count) for passwords, and a small HMAC-signed bearer
token (stdlib `hmac`/`hashlib`, not a full JWT library) for sessions. This is
real password auth and tamper-evident session verification -- a genuine step
up from the earlier create-by-email prototype -- but it is still hand-rolled
for a research prototype: no MFA, no token revocation list, no per-device
session management. See thesis section 12.1 for what a production platform
would still need on top of this.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import auth_error
from app.models import Investor, SME

PBKDF2_ITERATIONS = 260_000
TOKEN_TTL_SECONDS = 60 * 60 * 12  # 12 hours

_SECRET_PATH = Path(__file__).resolve().parent.parent / "data" / ".session_secret"


def _load_or_create_secret() -> bytes:
    _SECRET_PATH.parent.mkdir(exist_ok=True)
    if _SECRET_PATH.exists():
        return _SECRET_PATH.read_bytes()
    secret = secrets.token_bytes(32)
    _SECRET_PATH.write_bytes(secret)
    return secret


_SECRET = _load_or_create_secret()


# --- passwords --------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored or "$" not in stored:
        return False
    salt_hex, digest_hex = stored.split("$", 1)
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(candidate, expected)


# --- session tokens -----------------------------------------------------

def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def create_session_token(subject_type: str, subject_id: int) -> str:
    payload = {"t": subject_type, "id": subject_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _b64encode(json.dumps(payload).encode())
    signature = _b64encode(hmac.new(_SECRET, body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def _decode_session_token(token: str) -> dict:
    try:
        body, signature = token.split(".", 1)
        expected = _b64encode(hmac.new(_SECRET, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature mismatch")
        payload = json.loads(_b64decode(body))
    except Exception:
        raise auth_error("INVALID_TOKEN", "Invalid or malformed session token. Please log in again.")
    if payload.get("exp", 0) < time.time():
        raise auth_error("TOKEN_EXPIRED", "Your session has expired. Please log in again.")
    return payload


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise auth_error("MISSING_TOKEN", "This action requires an active session. Please log in.")
    return authorization.split(" ", 1)[1].strip()


def get_current_investor(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> Investor:
    payload = _decode_session_token(_bearer_token(authorization))
    if payload.get("t") != "investor":
        raise auth_error("INSUFFICIENT_PERMISSIONS", "This action requires an investor session.")
    investor = db.get(Investor, payload["id"])
    if investor is None:
        raise auth_error("UNKNOWN_INVESTOR", "This investor account no longer exists.")
    return investor


def get_current_sme(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> SME:
    payload = _decode_session_token(_bearer_token(authorization))
    if payload.get("t") != "sme":
        raise auth_error("INSUFFICIENT_PERMISSIONS", "This action requires a business (SME) session.")
    sme = db.get(SME, payload["id"])
    if sme is None:
        raise auth_error("UNKNOWN_SME", "This business account no longer exists.")
    return sme
