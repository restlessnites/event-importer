#!/usr/bin/env -S uv run python
"""Test script for the event importer with CLI output."""

import asyncio
import sys
import traceback
from datetime import datetime

import pytest

from app.config import get_config
from app.core.importer import EventImporter
from app.interfaces.cli.core import CLI
from app.interfaces.cli.runner import get_cli
from app.schemas import ImportProgress, ImportRequest
from app.shared.http import close_http_service


@pytest.mark.parametrize(
    "url",
    [
        "https://ra.co/events/1908868",
        "https://dice.fm/event/l86kmr-framework-presents-paradise-los-angeles-25th-oct-the-dock-at-the-historic-sears-building-los-angeles-tickets",
    ],
)
@pytest.mark.asyncio
async def test_import(url: str, cli: CLI, show_raw: bool = False) -> None:
    """Test importing an event with progress display."""
    # Clear any previous errors
    cli.clear_errors()

    # Start capturing errors during the import
    cli.error_capture.start()

    cli.section("Import Request")
    cli.info(f"URL: {url}")
    cli.info(f"Started: {datetime.now().strftime('%H:%M:%S')}")

    # Create importer
    importer = EventImporter()

    # Create request
    request = ImportRequest(
        url=url, include_raw_data=show_raw, ignore_cache=True, timeout=120
    )

    # Store progress updates for display
    progress_history = []

    # Track progress with our CLI
    async def handle_progress(progress: ImportProgress) -> None:
        update = progress.model_dump()
        progress_history.append(update)
        cli.progress_update(update)

    importer.add_progress_listener(request.request_id, handle_progress)

    try:
        # Run import with progress context
        with cli.progress("Importing event") as progress_cli:
            # Start the import
            import_task = asyncio.create_task(importer.import_event(request))

            # Update progress bar while import runs
            while not import_task.done():
                # Get latest progress
                history = importer.get_progress_history(request.request_id)
                if history:
                    latest = history[-1]
                    progress_cli.update_progress(latest.progress * 100, latest.message)
                await asyncio.sleep(0.1)

            # Get the result
            result = await import_task

        # Display results using CLI helper
        cli.import_result(result, show_raw)

    except TimeoutError:
        cli.error("Import timed out")
    except Exception as e:
        cli.error(f"Unexpected error: {e}")
        cli.code(traceback.format_exc(), "python", "Exception Traceback")
    finally:
        # Stop capturing errors
        cli.error_capture.stop()

        # Show any captured errors at the end
        if cli.error_capture.has_errors() or cli.error_capture.has_warnings():
            cli.show_captured_errors("Issues During Import")


async def main() -> None:
    """Run tests with CLI."""
    # This is the critical fix: Initialize the configuration from .env
    get_config()

    cli = get_cli()

    # Parse command line arguments
    show_raw = "--raw" in sys.argv
    urls_from_args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

    # Show header
    cli.header(
        "Event Importer Test Suite",
        f"Testing event import from various sources{' (with raw data)' if show_raw else ''}",
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
        cli.info(f"Testing {len(test_urls)} URL(s) from command line")
    else:
        cli.info(f"Testing {len(test_urls)} example URLs")

    if show_raw:
        cli.info("Raw data output enabled")

    try:
        # Track overall stats
        total_time = 0.0

        for i, url in enumerate(test_urls, 1):
            if len(test_urls) > 1:
                cli.rule(f"Test {i} of {len(test_urls)}")

            start = datetime.now()
            await test_import(url, cli, show_raw)
            duration = (datetime.now() - start).total_seconds()

            # Track time
            total_time += duration

            if i < len(test_urls):
                # Brief pause between tests
                await asyncio.sleep(1)

        # Summary
        cli.rule("Test Summary")
        cli.info(f"Total tests: {len(test_urls)}")
        cli.info(f"Total time: {total_time:.1f}s")
        cli.info(f"Average time: {total_time / len(test_urls):.1f}s per import")
        cli.success("All tests completed")

    except KeyboardInterrupt:
        cli.warning("\nTests interrupted by user")
    except Exception as e:
        cli.error(f"Test suite failed: {e}")
        raise
    finally:
        # Clean up HTTP sessions
        with cli.spinner("Cleaning up connections"):
            await close_http_service()


if __name__ == "__main__":
    asyncio.run(main())
