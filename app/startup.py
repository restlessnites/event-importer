"""Application startup utilities with database initialization."""

import logging
import sqlite3
from pathlib import Path
from sqlalchemy.exc import OperationalError
from sqlalchemy import text

from app.shared.database.connection import init_db, get_db_session

logger = logging.getLogger(__name__)


def ensure_database_ready():
    """
    Ensure the database is properly initialized and ready for use.
    This should be called once at application startup.
    """
    try:
        # Test if database is accessible by trying a simple query
        with get_db_session() as db:
            db.execute(text("SELECT 1 FROM events LIMIT 1"))
        logger.debug("Database is ready")
        
    except (OperationalError, sqlite3.OperationalError) as e:
        if "no such table" in str(e).lower():
            logger.info("Database tables not found, initializing database...")
            init_db()
            logger.info("Database initialized successfully")
        else:
            logger.error(f"Database error: {e}")
            raise
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        raise



def startup_checks():
    """
    Run all startup checks and initialization.
    Call this from main entry points.
    """
    logger.info("Running startup checks...")
    
    # Ensure database is ready
    ensure_database_ready()
    
    # Check data directory exists
    data_dir = Path("data")
    if not data_dir.exists():
        logger.info("Creating data directory...")
        data_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Startup checks completed")