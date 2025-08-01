"""Application startup utilities with database initialization."""

import logging
import sqlite3

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.shared.database.connection import get_db_session, init_db

logger = logging.getLogger(__name__)


def ensure_database_ready() -> None:
    """Ensure the database is properly initialized and ready for use.
    This should be called once at application startup.
    """
    try:
        # Test if all required tables exist
        with get_db_session() as db:
            # Check both events and submissions tables
            db.execute(text("SELECT 1 FROM events LIMIT 1"))
            db.execute(text("SELECT 1 FROM submissions LIMIT 1"))
        logger.debug("Database is ready")

    except (OperationalError, sqlite3.OperationalError) as e:
        if "no such table" in str(e).lower():
            logger.debug("Database tables not found, initializing database...")
            init_db()
            logger.debug("Database initialized successfully")
        else:
            logger.exception("Database error")
            raise
    except Exception:
        logger.exception("Unexpected database error")
        raise


def startup_checks() -> None:
    """Run all startup checks and initialization.
    Call this from main entry points.
    """
    logger.debug("Running startup checks...")

    # Ensure database is ready
    ensure_database_ready()

    logger.debug("Startup checks completed")
