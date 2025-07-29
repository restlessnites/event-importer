"""Tests for the application validators."""

from unittest.mock import patch

import pytest

from app.validators import InstallationValidator


@pytest.fixture
def validator():
    """Fixture for InstallationValidator."""
    return InstallationValidator()


def test_installation_validator_all_checks_pass(validator, tmp_path):
    """Test that the validator returns True when all checks pass."""
    with (
        patch(
            "app.validators.APIKeyManager.are_required_keys_present", return_value=True
        ),
        patch("app.validators.init_db") as mock_init_db,
    ):
        success, messages = validator.validate(tmp_path)
        assert success is True
        assert messages == []
        mock_init_db.assert_called_once()


def test_installation_validator_api_keys_fail(validator, tmp_path):
    """Test that the validator returns False if API keys are missing."""
    with (
        patch(
            "app.validators.APIKeyManager.are_required_keys_present", return_value=False
        ),
        patch("app.validators.init_db"),
    ):
        success, messages = validator.validate(tmp_path)
        assert success is False
        assert "Required API keys are not fully configured." in messages


def test_installation_validator_database_fail(validator, tmp_path):
    """Test that the validator returns False if the database connection fails."""
    with (
        patch(
            "app.validators.APIKeyManager.are_required_keys_present", return_value=True
        ),
        patch("app.validators.init_db", side_effect=Exception("DB Error")),
    ):
        success, messages = validator.validate(tmp_path)
        assert success is False
        assert "Database connection failed: DB Error" in messages
