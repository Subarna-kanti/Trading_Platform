# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.db.data_model import Base

# --- Database URL ---
DATABASE_URL = "postgresql+psycopg2://trading_user:trade@localhost/trading_platform"

# --- SQLAlchemy Engine ---
engine = create_engine(DATABASE_URL, echo=True)

# --- Session Factory ---
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# --- Dependency for FastAPI ---
def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a new SQLAlchemy session per request.
    Yields a session and ensures it's closed after request ends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
