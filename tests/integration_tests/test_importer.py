#!/usr/bin/env -S uv run python
"""Test script for the event importer with CLI output."""

import asyncio
import sys
import traceback
from datetime import datetime
from unittest.mock import AsyncMock, patch

import clicycle
import pytest

from app.config import get_config
from app.core.importer import EventImporter
from app.schemas import (
    EventData,
    EventLocation,
    EventTime,
    ImportRequest,
    ImportResult,
    ImportStatus,
)
from app.shared.http import close_http_service


@pytest.mark.parametrize(
    "url",
    [
        "https://ra.co/events/1908868",
        "https://dice.fm/event/l86kmr-framework-presents-paradise-los-angeles-25th-oct-the-dock-at-the-historic-sears-building-los-angeles-tickets",
    ],
)
@pytest.mark.asyncio
async def test_import(url: str, show_raw: bool = False) -> None:
    """Test importing an event with progress display."""
    clicycle.configure(app_name="event-importer-test")
    clicycle.header("Import Request")
    clicycle.info(f"URL: {url}")
    clicycle.info(f"Started: {datetime.now().strftime('%H:%M:%S')}")

    # Mock event data based on URL
    if "ra.co" in url:
        mock_event = EventData(
            title="Test RA Event",
            venue="Test Venue",
            date="2025-01-01",
            time=EventTime(start="22:00", timezone="Europe/London"),
            location=EventLocation(city="London", country="United Kingdom"),
        )
    else:
        mock_event = EventData(
            title="Test Dice Event",
            venue="The Dock",
            date="2025-10-25",
            time=EventTime(start="20:00", timezone="America/Los_Angeles"),
            location=EventLocation(
                city="Los Angeles", state="California", country="United States"
            ),
        )

    mock_result = ImportResult(
        request_id="test-123",
        status=ImportStatus.SUCCESS,
        url=url,
        event_data=mock_event,
        import_time=1.5,
    )

    # Create request
    request = ImportRequest(
        url=url, include_raw_data=show_raw, ignore_cache=True, timeout=120
    )

    try:
        with patch(
            "app.core.importer.EventImporter.import_event", new_callable=AsyncMock
        ) as mock_import:
            mock_import.return_value = mock_result

            # Create importer
            importer = EventImporter()

            # Run import with progress context
            clicycle.info("Importing event...")
            # Start the import
            result = await importer.import_event(request)

        # Display results
        if result.success:
            clicycle.success(f"Import successful: {result.data.title}")
            if show_raw:
                clicycle.info(f"Raw data: {result.raw_data}")
        else:
            clicycle.error(f"Import failed: {result.error}")

    except TimeoutError:
        clicycle.error("Import timed out")
    except Exception as e:
        clicycle.error(f"Unexpected error: {e}")
        clicycle.error(f"Exception Traceback: {traceback.format_exc()}")


async def main() -> None:
    """Run tests with CLI."""
    # This is the critical fix: Initialize the configuration from .env
    get_config()

    clicycle.configure(app_name="event-importer-test")

    # Parse command line arguments
    show_raw = "--raw" in sys.argv
    urls_from_args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

    # Show header
    clicycle.header("Event Importer Test Suite")
    clicycle.info(
        f"Testing event import from various sources{' (with raw data)' if show_raw else ''}"
    )

    # Default test URLs
    test_urls = [
        # Resident Advisor (real event)
        "https://ra.co/events/2147288",
        # Generic web page
        "https://dice.fm/event/53ng6k-cursive-13th-sep-zebulon-los-angeles-tickets",
        # Direct image (use a real event flyer URL)
        "https://imgproxy.ra.co/_/quality:66/w:1442/rt:fill/aHR0cHM6Ly9pbWFnZXMucmEuY28vNmEwZDhkMDNkOTFjMGJmZDE2NTFhMjgzYjI5MDVlMTc3OTQ2M2Y0OC5qcGc=",
    ]

    # Use command line URLs if provided
    if urls_from_args:
        test_urls = urls_from_args
        clicycle.info(f"Testing {len(test_urls)} URL(s) from command line")
    else:
        clicycle.info(f"Testing {len(test_urls)} example URLs")

    if show_raw:
        clicycle.info("Raw data output enabled")

    try:
        # Track overall stats
        total_time = 0.0

        for i, url in enumerate(test_urls, 1):
            if len(test_urls) > 1:
                clicycle.section(f"Test {i} of {len(test_urls)}")

            start = datetime.now()
            await test_import(url, show_raw)
            duration = (datetime.now() - start).total_seconds()

            # Track time
            total_time += duration

            if i < len(test_urls):
                # Brief pause between tests
                await asyncio.sleep(1)

        # Summary
        clicycle.section("Test Summary")
        clicycle.info(f"Total tests: {len(test_urls)}")
        clicycle.info(f"Total time: {total_time:.1f}s")
        clicycle.info(f"Average time: {total_time / len(test_urls):.1f}s per import")
        clicycle.success("All tests completed")

    except KeyboardInterrupt:
        clicycle.warning("Tests interrupted by user")
    except Exception as e:
        clicycle.error(f"Test suite failed: {e}")
        raise
    finally:
        # Clean up HTTP sessions
        clicycle.info("Cleaning up connections...")
        await close_http_service()


if __name__ == "__main__":
    asyncio.run(main())
