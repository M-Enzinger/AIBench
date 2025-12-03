import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import scenarios, experiments
from app.db.session import Base, engine
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
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


app.include_router(scenarios.router)
app.include_router(experiments.router)


@app.get("/")
def read_root():
    return {"message": "AIBench Experiment Platform API", "docs": "/docs"}
