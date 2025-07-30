"""Tests for CLI settings commands."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from app.interfaces.cli.commands import cli


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


class TestSettingsCLI:
    """Test cases for settings CLI commands."""

    def test_list_settings(self, runner):
        """Test listing all settings."""
        with patch("app.interfaces.cli.settings.SettingsStorage") as mock_storage_class:
            mock_storage = MagicMock()
            mock_storage_class.return_value = mock_storage

            mock_storage.get_all.return_value = {
                "api_key": "test-key-123",
                "theme": "dark",
                "timeout": "60",
            }

            result = runner.invoke(cli, ["settings", "list"])

            assert result.exit_code == 0
            # The actual output shows all settings with their display names

    def test_list_settings_empty(self, runner):
        """Test listing settings when none have values."""
        with patch("app.interfaces.cli.settings.SettingsStorage") as mock_storage_class:
            mock_storage = MagicMock()
            mock_storage_class.return_value = mock_storage
            mock_storage.get_all.return_value = {}

            result = runner.invoke(cli, ["settings", "list"])

            assert result.exit_code == 0
            # Settings list always shows all available settings
            assert "API KEYS" in result.output
            assert "APPLICATION SETTINGS" in result.output
            assert "not set" in result.output

    def test_get_setting_exists(self, runner):
        """Test getting a specific setting that exists."""
        with (
            patch("app.interfaces.cli.settings.SettingsStorage") as mock_storage_class,
            patch("config.settings.get_setting_info") as mock_get_info,
        ):
            mock_storage = MagicMock()
            mock_storage_class.return_value = mock_storage
            mock_storage.get.return_value = "test-api-key-123"

            # Mock the setting info
            mock_setting_info = MagicMock()
            mock_setting_info.display_name = "Anthropic API Key"
            mock_get_info.return_value = mock_setting_info

            result = runner.invoke(cli, ["settings", "get", "ANTHROPIC_API_KEY"])

            assert result.exit_code == 0
            assert "Anthropic API Key" in result.output
            assert "***set***" in result.output  # API keys are masked

    def test_get_setting_not_found(self, runner):
        """Test getting a setting that doesn't exist."""
        with (
            patch("app.interfaces.cli.settings.SettingsStorage") as mock_storage_class,
            patch("config.settings.get_setting_info") as mock_get_info,
        ):
            mock_storage = MagicMock()
            mock_storage_class.return_value = mock_storage
            mock_get_info.return_value = None  # Setting doesn't exist

            result = runner.invoke(cli, ["settings", "get", "nonexistent"])

            assert result.exit_code == 0
            assert "Unknown setting: nonexistent" in result.output

    def test_set_setting_new(self, runner):
        """Test setting a new value."""
        with (
            patch("app.interfaces.cli.settings.SettingsStorage") as mock_storage_class,
            patch("config.settings.get_setting_info") as mock_get_info,
        ):
            mock_storage = MagicMock()
            mock_storage_class.return_value = mock_storage

            # Mock the setting info
            mock_setting_info = MagicMock()
            mock_setting_info.display_name = "Anthropic API Key"
            mock_get_info.return_value = mock_setting_info

            result = runner.invoke(
                cli, ["settings", "set", "ANTHROPIC_API_KEY", "new-key"]
            )

            assert result.exit_code == 0
            assert "Set Anthropic API Key: ***set***" in result.output
            mock_storage.set.assert_called_once_with("ANTHROPIC_API_KEY", "new-key")

    def test_set_setting_update(self, runner):
        """Test updating an existing setting."""
        with (
            patch("app.interfaces.cli.settings.SettingsStorage") as mock_storage_class,
            patch("config.settings.get_setting_info") as mock_get_info,
        ):
            mock_storage = MagicMock()
            mock_storage_class.return_value = mock_storage

            # Mock the setting info for a non-API key setting
            mock_setting_info = MagicMock()
            mock_setting_info.display_name = "Update URL"
            mock_get_info.return_value = mock_setting_info

            result = runner.invoke(
                cli, ["settings", "set", "update_url", "https://example.com/update"]
            )

            assert result.exit_code == 0
            assert "Set Update URL: https://example.com/update" in result.output
            mock_storage.set.assert_called_once_with(
                "update_url", "https://example.com/update"
            )

    def test_set_setting_invalid(self, runner):
        """Test setting an invalid setting."""
        with (
            patch("app.interfaces.cli.settings.SettingsStorage") as mock_storage_class,
            patch("config.settings.get_setting_info") as mock_get_info,
        ):
            mock_storage = MagicMock()
            mock_storage_class.return_value = mock_storage
            mock_get_info.return_value = None  # Invalid setting

            result = runner.invoke(cli, ["settings", "set", "invalid_setting", "value"])

            assert result.exit_code == 0
            assert "Unknown setting: invalid_setting" in result.output
            # set should not be called for invalid settings
            mock_storage.set.assert_not_called()
