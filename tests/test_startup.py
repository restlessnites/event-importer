"""Tests for startup module."""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

from app.startup import ensure_database_ready, startup_checks


def test_startup_checks_creates_directories(tmp_path, monkeypatch):
    """Test that startup_checks creates necessary directories."""
    # Mock Path to use our temp directory
    tmp_path / "data"

    with patch("app.startup.Path") as mock_path_class, \
         patch("app.startup.ensure_database_ready"):

        # Setup mock
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path.mkdir = MagicMock()
        mock_path_class.return_value = mock_path

        startup_checks()

        # Check Path was called with "data"
        mock_path_class.assert_called_with("data")
        # Check mkdir was called
        mock_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)


def test_startup_checks_skips_existing_directory():
    """Test that startup_checks doesn't create directory if it exists."""
    with patch("app.startup.Path") as mock_path_class, \
         patch("app.startup.ensure_database_ready"):

        # Setup mock - directory already exists
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        startup_checks()

        # Check mkdir was NOT called
        mock_path.mkdir.assert_not_called()


def test_ensure_database_ready_initializes_missing_tables():
    """Test that missing tables trigger database initialization."""
    with patch("app.startup.get_db_session") as mock_get_db, \
         patch("app.startup.init_db") as mock_init_db:

        # Mock the context manager and session
        mock_session = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_session
        mock_context.__exit__.return_value = None
        mock_get_db.return_value = mock_context

        # Simulate "no such table" error
        error = OperationalError("statement", "params", sqlite3.OperationalError("no such table: events"))
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
        error = OperationalError("statement", "params", sqlite3.OperationalError("database is locked"))
        mock_session.execute.side_effect = error

        # Should re-raise the error
        with pytest.raises(OperationalError):
            ensure_database_ready()
