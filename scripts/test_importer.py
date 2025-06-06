#!/usr/bin/env -S uv run python
"""Test script for the event importer with CLI output."""

import asyncio
import sys
from datetime import datetime

from app import EventImporter
from app.schemas import ImportRequest, ImportStatus
from app.http import close_http_service
from app.cli import get_cli


async def test_import(url: str, cli, show_raw: bool = False):
    """Test importing an event with progress display."""

    cli.section(f"Import Request")
    cli.info(f"URL: {url}")
    cli.info(f"Started: {datetime.now().strftime('%H:%M:%S')}")

    # Create importer
    importer = EventImporter()

    # Create request
    request = ImportRequest(url=url, include_raw_data=show_raw)

    # Store progress updates for display
    progress_history = []

    # Track progress
    async def handle_progress(progress):
        update = progress.model_dump()
        progress_history.append(update)
        cli.progress_update(update)

    importer.add_progress_listener(request.request_id, handle_progress)

    try:
        # Run import with progress
        with cli.progress(f"Importing event") as progress_cli:
            import_task = asyncio.create_task(importer.import_event(request))

            # Update progress bar while import runs
            while not import_task.done():
                history = importer.get_progress_history(request.request_id)
                if history:
                    latest = history[-1]
                    progress_cli.update_progress(latest.progress * 100, latest.message)
                await asyncio.sleep(0.1)

            result = await import_task

        # Display results
        cli.import_summary(result.model_dump())

        if result.status == ImportStatus.SUCCESS and result.event_data:
            # Show ALL event data
            cli.event_data(result.event_data.model_dump())

            # Show raw data if requested
            if show_raw and result.raw_data:
                cli.json(result.raw_data, title="Raw Extracted Data")

        # Show progress timeline
        if len(progress_history) > 1:
            cli.section("Progress Timeline")
            for update in progress_history:
                cli.progress_update(update)

    except asyncio.TimeoutError:
        cli.error("Import timed out")
    except Exception as e:
        cli.error(f"Unexpected error: {e}")
        import traceback

        cli.error(traceback.format_exc())


async def main():
    """Run tests with CLI."""
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
        total_success = 0
        total_time = 0.0

        for i, url in enumerate(test_urls, 1):
            if len(test_urls) > 1:
                cli.header(f"Test {i} of {len(test_urls)}")

            start = datetime.now()
            await test_import(url, cli, show_raw)
            duration = (datetime.now() - start).total_seconds()

            # Check if successful
            total_time += duration

            if i < len(test_urls):
                # Brief pause between tests
                await asyncio.sleep(1)

        # Summary
        cli.header("Test Summary")
        cli.info(f"Total tests: {len(test_urls)}")
        cli.info(f"Total time: {total_time:.1f}s")
        cli.info(f"Average time: {total_time/len(test_urls):.1f}s per import")
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
