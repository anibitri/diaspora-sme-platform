from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, SessionLocal, engine
from app.errors import register_exception_handlers
from app.routers import admin, investments, investors, smes
from app.seed_data import seed_if_empty

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Diaspora-to-SME Investment Platform (Prototype)")

register_exception_handlers(app)

app.include_router(smes.router)
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
