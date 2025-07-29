"""Tests for the application validators."""

from unittest.mock import patch

from sqlalchemy.exc import ArgumentError

from app.validators import InstallationValidator


def test_installation_validator_all_checks_pass():
    """Test that the validator returns True when all checks pass."""
    with (
        patch("app.validators.get_config") as mock_get_config,
        patch("app.validators.get_user_data_dir"),
        patch("app.validators.init_db"),
        patch("app.validators.get_db_session") as mock_get_db,
    ):
        # Configure mock config with all API keys
        mock_config = mock_get_config.return_value
        mock_config.api.anthropic_api_key = "test-key"
        mock_config.api.zyte_api_key = "test-key"
        mock_config.api.openai_api_key = "test-key"
        mock_config.api.ticketmaster_api_key = "test-key"
        mock_config.api.google_api_key = "test-key"
        mock_config.api.google_cse_id = "test-id"
        mock_config.api.ticketfairy_api_key = "test-key"

        mock_db = mock_get_db.return_value.__enter__.return_value
        mock_db.execute.return_value = None

        # Create validator after mocking
        validator = InstallationValidator()
        success, messages = validator.validate()
        assert success is True
        assert messages == []


def test_installation_validator_api_keys_fail():
    """Test that the validator returns False if API keys are missing."""
    with patch("app.validators.get_config") as mock_get_config:
        # Configure mock config with missing required keys
        mock_config = mock_get_config.return_value
        mock_config.api.anthropic_api_key = None
        mock_config.api.zyte_api_key = None
        mock_config.api.openai_api_key = None
        mock_config.api.ticketmaster_api_key = None
        mock_config.api.google_api_key = None
        mock_config.api.google_cse_id = None
        mock_config.api.ticketfairy_api_key = None

        # Create validator with mocked config
        fresh_validator = InstallationValidator()
        fresh_validator.config = mock_config

        # The validator checks all keys from api_keys_info
        success, messages = fresh_validator.validate()
        # If no keys are configured, all should be reported as missing
        assert success is False
        assert len(messages) == 7  # Should have exactly 7 missing API keys


def test_installation_validator_database_fail():
    """Test that the validator returns False if the database connection fails."""
    with (
        patch("app.validators.get_config") as mock_get_config,
        patch("app.validators.get_user_data_dir"),
        patch(
            "app.validators.get_db_session",
            side_effect=Exception("DB Error"),
        ),
    ):
        # Configure mock config with all API keys
        mock_config = mock_get_config.return_value
        mock_config.api.anthropic_api_key = "test-key"
        mock_config.api.zyte_api_key = "test-key"
        mock_config.api.openai_api_key = "test-key"
        mock_config.api.ticketmaster_api_key = "test-key"
        mock_config.api.google_api_key = "test-key"
        mock_config.api.google_cse_id = "test-id"
        mock_config.api.ticketfairy_api_key = "test-key"

        # Create validator after mocking
        validator = InstallationValidator()
        success, messages = validator.validate()
        assert success is False
        assert "Database connection failed: DB Error" in messages


def test_installation_validator_textual_sql_fail():
    """Test the validator with a textual SQL error."""

    error_message = "Textual SQL expression 'SELECT 1' should be explicitly declared as text('SELECT 1')"
    with (
        patch("app.validators.get_config") as mock_get_config,
        patch("app.validators.get_user_data_dir"),
        patch("app.validators.get_db_session") as mock_get_db,
    ):
        # Configure mock config with all API keys
        mock_config = mock_get_config.return_value
        mock_config.api.anthropic_api_key = "test-key"
        mock_config.api.zyte_api_key = "test-key"
        mock_config.api.openai_api_key = "test-key"
        mock_config.api.ticketmaster_api_key = "test-key"
        mock_config.api.google_api_key = "test-key"
        mock_config.api.google_cse_id = "test-id"
        mock_config.api.ticketfairy_api_key = "test-key"

        mock_db = mock_get_db.return_value.__enter__.return_value
        mock_db.execute.side_effect = ArgumentError(error_message)

        # Create validator after mocking
        validator = InstallationValidator()
        success, messages = validator.validate()
        assert success is False
        assert f"Database connection failed: {error_message}" in messages
