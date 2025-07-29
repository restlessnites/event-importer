"""Tests for the TicketFairy submitter."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.ticketfairy.shared.submitter import TicketFairySubmitter


@pytest.mark.asyncio
async def test_submit_by_url_success():
    """Test successful submission by URL."""
    submitter = TicketFairySubmitter()

    # Mock the attributes on the instance
    submitter.transformer = MagicMock()
    submitter.transformer.transform = MagicMock(return_value={"transformed": True})

    submitter.client = MagicMock()
    submitter.client.submit = AsyncMock(return_value={"submitted": True})

    # Since submit_by_url calls submit_events, we need to mock that too
    submitter.submit_events = AsyncMock(return_value={"submitted": True})

    result = await submitter.submit_by_url("http://example.com", dry_run=False)

    submitter.submit_events.assert_called_once_with("url", False)
    assert result == {"submitted": True}


@pytest.mark.asyncio
async def test_submit_by_url_dry_run():
    """Test dry run submission by URL."""
    submitter = TicketFairySubmitter()

    # Mock the attributes on the instance
    submitter.transformer = MagicMock()
    submitter.transformer.transform = MagicMock(return_value={"transformed": True})

    submitter.client = MagicMock()
    submitter.client.submit = AsyncMock(
        return_value={"submitted": True, "dry_run": True}
    )

    # Since submit_by_url calls submit_events, we need to mock that too
    submitter.submit_events = AsyncMock(
        return_value={"submitted": True, "dry_run": True}
    )

    result = await submitter.submit_by_url("http://example.com", dry_run=True)

    submitter.submit_events.assert_called_once_with("url", True)
    assert result == {"submitted": True, "dry_run": True}
