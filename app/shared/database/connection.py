from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

# Database configuration
DB_PATH = Path("data") / "events.db"  # This creates data/events.db
DB_URL = f"sqlite:///{DB_PATH}"

# Create engine with SQLite optimizations
engine = create_engine(
    DB_URL,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,
    connect_args={
        "check_same_thread": False,  # Allow SQLite to be used across threads
        "timeout": 20,  # 20 second timeout for database locks
    },
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize the database, creating tables if they don't exist"""
    # Ensure data directory exists (not nested)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Log the actual database path for debugging
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Database path: {DB_PATH.absolute()}")

    # Create all tables
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session_sync() -> Session:
    """Get a database session (for dependency injection)"""
    return SessionLocal()
