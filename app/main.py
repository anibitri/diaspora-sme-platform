from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import Base, SessionLocal, engine
from app.errors import register_exception_handlers
from app.routers import admin, investments, investors, qkb, smes
from app.seed_data import seed_if_empty

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline security response headers (thesis section 12.1).

    script-src is strict ('self' only, no inline/eval) because every page
    script lives in an external .js file -- that's what makes this CSP
    meaningful rather than decorative. style-src allows 'unsafe-inline'
    because the risk-score bar charts set widths via inline style attributes;
    tightening that further would mean moving chart geometry into CSS custom
    properties, which isn't worth it for a prototype's threat model (style
    injection alone is a much narrower attack surface than script injection).
    This is not a substitute for TLS termination, which a local dev server
    doesn't provide -- see the README for what a real deployment still needs.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        )
        return response


app = FastAPI(title="Diaspora-to-SME Investment Platform (Prototype)")

app.add_middleware(SecurityHeadersMiddleware)
register_exception_handlers(app)

app.include_router(smes.router)
app.include_router(qkb.router)
app.include_router(investors.router)
app.include_router(investments.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
