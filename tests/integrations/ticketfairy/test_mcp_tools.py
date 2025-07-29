"""Tests for the TicketFairy MCP tools."""

from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.ticketfairy.mcp_tools import handle_submit_ticketfairy


@pytest.mark.asyncio
async def test_handle_submit_ticketfairy_success():
    """Test successful submission."""
    with patch("app.integrations.ticketfairy.mcp_tools.TicketFairySubmitter") as mock:
        mock_submitter = mock.return_value
        mock_submitter.submit_by_url = AsyncMock(return_value={"success": True})

        arguments = {"url": "http://example.com", "dry_run": False}
        result = await handle_submit_ticketfairy(arguments)

        mock_submitter.submit_by_url.assert_called_once_with(
            "http://example.com", dry_run=False
        )
        assert result == {"success": True}


@pytest.mark.asyncio
async def test_handle_submit_ticketfairy_no_url():
    """Test submission with no URL."""
    arguments = {}
    result = await handle_submit_ticketfairy(arguments)
    assert result == {"success": False, "error": "URL is required"}


@pytest.mark.asyncio
async def test_handle_submit_ticketfairy_dry_run():
    """Test dry run submission."""
    with patch("app.integrations.ticketfairy.mcp_tools.TicketFairySubmitter") as mock:
        mock_submitter = mock.return_value
        mock_submitter.submit_by_url = AsyncMock(
            return_value={"success": True, "dry_run": True}
        )

        arguments = {"url": "http://example.com", "dry_run": True}
        result = await handle_submit_ticketfairy(arguments)

        mock_submitter.submit_by_url.assert_called_once_with(
            "http://example.com", dry_run=True
        )
        assert result == {"success": True, "dry_run": True}
