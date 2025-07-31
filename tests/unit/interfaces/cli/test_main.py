"""Tests for main CLI commands."""

from unittest.mock import AsyncMock, patch

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
        with patch("app.interfaces.cli.commands.show_stats") as mock_show_stats:
            result = runner.invoke(cli, ["stats"])

            assert result.exit_code == 0
            mock_show_stats.assert_called_once()

    def test_api_command(self, runner):
        """Test the api command."""
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
            # The MCP command itself produces no output; the server does.
            # When we mock the run function, we expect no output here.
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
        assert "api" in result.output
        assert "mcp" in result.output
        assert "events" in result.output
        assert "settings" in result.output
        assert "stats" in result.output
