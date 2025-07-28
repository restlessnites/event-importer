"""Tests for startup module."""

from unittest.mock import patch

import pytest

from app.startup import startup_checks


def test_startup_checks_creates_directories(tmp_path, monkeypatch):
    """Test that startup_checks creates necessary directories."""
    # Use a temporary directory for testing
    test_data_dir = tmp_path / "data"
    test_logs_dir = tmp_path / "logs"

    monkeypatch.setattr("app.startup.DATA_DIR", test_data_dir)
    monkeypatch.setattr("app.startup.LOGS_DIR", test_logs_dir)

    # Mock database initialization
    with patch("app.startup.init_db") as mock_init_db:
        startup_checks()

        # Check directories were created
        assert test_data_dir.exists()
        assert test_logs_dir.exists()

        # Check database was initialized
        mock_init_db.assert_called_once()


def test_startup_checks_configures_logging(monkeypatch):
    """Test that startup_checks configures logging properly."""
    with patch("app.startup.init_db"), \
         patch("app.startup.logging.basicConfig") as mock_config, \
         patch("app.startup.Path.mkdir"):

        startup_checks()

        # Check logging was configured
        mock_config.assert_called_once()
        call_args = mock_config.call_args[1]
        assert call_args["level"] is not None
        assert "handlers" in call_args


def test_startup_checks_handles_errors(monkeypatch):
    """Test that startup_checks handles initialization errors gracefully."""
    with patch("app.startup.init_db") as mock_init_db, \
         patch("app.startup.Path.mkdir"):

        # Simulate database initialization failure
        mock_init_db.side_effect = Exception("Database connection failed")

        # Should not raise exception
        try:
            startup_checks()
        except Exception:
            pytest.fail("startup_checks should handle errors gracefully")
