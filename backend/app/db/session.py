# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from dotenv import load_dotenv
import os

load_dotenv()

# --- Database URL ---
DATABASE_URL = os.environ.get("DATABASE_URL")

# --- SQLAlchemy Engine ---
engine = create_engine(
    DATABASE_URL,
    pool_size=10,  # default 5
    max_overflow=20,  # default 10
    pool_timeout=50,
    echo=True,
)

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
