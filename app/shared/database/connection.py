from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.shared.database.models import Base
from config.paths import get_user_data_dir

# Database configuration
DB_PATH = get_user_data_dir() / "events.db"
DB_URL = f"sqlite:///{DB_PATH}"

# Ensure the directory for the database exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

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


def init_db(engine_to_bind=None) -> None:
    """Initialize the database, creating tables if they don't exist"""
    # Use the provided engine or the default one
    db_engine = engine_to_bind or engine

    # Create all tables
    Base.metadata.create_all(bind=db_engine)


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
