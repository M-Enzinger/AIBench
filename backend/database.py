import os
from contextlib import contextmanager
from sqlmodel import SQLModel, create_engine, Session

DB_PATH = os.getenv("AIBENCH_DB_PATH", "/app/data/aibench.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db():
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session():
    with Session(engine) as session:
        yield session
