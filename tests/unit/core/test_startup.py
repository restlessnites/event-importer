"""Tests for startup module."""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

from app.startup import ensure_database_ready, startup_checks


def test_startup_checks_calls_ensure_database_ready():
    """Test that startup_checks calls ensure_database_ready."""
    with patch("app.startup.ensure_database_ready") as mock_ensure_db:
        startup_checks()

        # Check that ensure_database_ready was called
        mock_ensure_db.assert_called_once()


def test_ensure_database_ready_initializes_missing_tables():
    """Test that missing tables trigger database initialization."""
    with (
        patch("app.startup.get_db_session") as mock_get_db,
        patch("app.startup.init_db") as mock_init_db,
    ):
        # Mock the context manager and session
        mock_session = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_session
        mock_context.__exit__.return_value = None
        mock_get_db.return_value = mock_context

        # Simulate "no such table" error
        error = OperationalError(
            "statement", "params", sqlite3.OperationalError("no such table: events")
        )
        mock_session.execute.side_effect = error

        ensure_database_ready()

        # Check that init_db was called
        mock_init_db.assert_called_once()


def test_ensure_database_ready_reraises_other_errors():
    """Test that non-table errors are re-raised."""
    with patch("app.startup.get_db_session") as mock_get_db:
        # Mock the context manager and session
        mock_session = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_session
        mock_context.__exit__.return_value = None
        mock_get_db.return_value = mock_context

        # Simulate different database error
        error = OperationalError(
            "statement", "params", sqlite3.OperationalError("database is locked")
        )
        mock_session.execute.side_effect = error

        # Should re-raise the error
        with pytest.raises(OperationalError):
            ensure_database_ready()
