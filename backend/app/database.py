from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cot_data.db")

# SQLite-spesifinen asetus: check_same_thread=False tarvitaan FastAPI:n kanssa
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Luo taulut jos ne eivät vielä ole olemassa."""
    from app import models  # noqa: F401 – rekisteröi mallit
    Base.metadata.create_all(bind=engine)
