import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api import auth, scenarios, experiments
from app.db.session import Base, engine, SessionLocal
from app.services import auth as auth_service
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AIBench Experiment Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    # ensure database connectivity and default admin user
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    db: Session = SessionLocal()
    try:
        if not auth_service.get_user(db, email="admin@aibench.local"):
            default_password = "admin"
            auth_service.create_user(db, email="admin@aibench.local", password=default_password)
            logger.warning("Default admin created: admin@aibench.local / admin")
    finally:
        db.close()


app.include_router(auth.router)
app.include_router(scenarios.router)
app.include_router(experiments.router)


@app.get("/")
def read_root():
    return {"message": "AIBench Experiment Platform API", "docs": "/docs"}
