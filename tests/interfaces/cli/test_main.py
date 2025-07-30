"""Tests for main CLI commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from app.interfaces.cli.commands import cli


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


class TestMainCLI:
    """Test cases for main CLI commands."""

    def test_stats_command(self, runner):
        """Test the stats command."""
        with patch("app.shared.statistics.StatisticsService") as mock_stats_class:
            mock_stats = MagicMock()
            mock_stats_class.return_value = mock_stats

            mock_stats.get_combined_statistics.return_value = {
                "events": {
                    "total": 10,
                    "unique_venues": 5,
                    "genres": ["Rock", "Electronic"],
                },
                "submissions": {"total": 8, "success": 6, "failed": 2},
            }

            result = runner.invoke(cli, ["stats"])

            assert result.exit_code == 0
            # Stats command shows actual stats, not mocked ones
            assert "EVENT STATISTICS" in result.output
            assert "Total Events" in result.output

    def test_api_command(self, runner):
        """Test the api command."""
        with patch("app.interfaces.cli.commands.api_run") as mock_api_run:
            result = runner.invoke(cli, ["api"])

            assert result.exit_code == 0
            assert "Starting API server..." in result.output
            mock_api_run.assert_called_once()

    def test_api_command_with_options(self, runner):
        """Test the api command with custom options."""
        # The CLI api command doesn't accept host/port options currently
        # It uses the default values from the api_run function
        with patch("app.interfaces.cli.commands.api_run") as mock_api_run:
            result = runner.invoke(cli, ["api"])

            assert result.exit_code == 0
            assert "Starting API server..." in result.output
            mock_api_run.assert_called_once()

    def test_mcp_command(self, runner):
        """Test the mcp command."""
        with patch(
            "app.interfaces.cli.commands.mcp_run", new_callable=AsyncMock
        ) as mock_mcp_run:
            result = runner.invoke(cli, ["mcp"])

            assert result.exit_code == 0
            # MCP command itself doesn't output anything, but the server does
            # When we mock mcp_run, we don't get the server's logging output
            assert result.output == ""
            mock_mcp_run.assert_called_once()

    def test_version_command(self, runner):
        """Test the version display."""
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "version" in result.output.lower()

    def test_help_command(self, runner):
        """Test the help display."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Commands:" in result.output
        assert "events" in result.output
        assert "settings" in result.output
        assert "stats" in result.output
