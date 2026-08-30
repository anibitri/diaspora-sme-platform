"""In-memory sliding-window rate limiter for auth endpoints.

Per thesis section 12.1: "rate-limiting on login endpoints" is explicitly
called out as a required control against credential-stuffing. This is a
process-local, in-memory limiter -- fine for a single-process prototype, but
a real deployment behind multiple workers would need a shared store (Redis)
instead. Documented as a known limitation, not hidden.
"""

import time
from collections import defaultdict, deque

from fastapi import Request

from app.errors import AppError

WINDOW_SECONDS = 300
MAX_ATTEMPTS = 8

_attempts: dict[str, deque] = defaultdict(deque)


def rate_limit_auth(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{request.url.path}"
    now = time.time()
    bucket = _attempts[key]

    while bucket and bucket[0] < now - WINDOW_SECONDS:
        bucket.popleft()

    if len(bucket) >= MAX_ATTEMPTS:
        raise AppError(
            "AUTH_RATE_LIMITED",
            "Too many attempts from this address. Please wait a few minutes and try again.",
            http_status=429,
            details={"retry_after_seconds": int(WINDOW_SECONDS - (now - bucket[0]))},
        )

    bucket.append(now)
