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

    # Track progress with our CLI
    async def handle_progress(progress):
        update = progress.model_dump()
        progress_history.append(update)
        cli.progress_update(update)

    importer.add_progress_listener(request.request_id, handle_progress)

    try:
        # Run import with progress context
        with cli.progress(f"Importing event") as progress_cli:
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

        # Display results
        cli.section("Import Summary")

        if result.status == ImportStatus.SUCCESS:
            cli.success(f"Status: SUCCESS")
            cli.info(f"Method: {result.method_used.value}")
            cli.info(f"Duration: {result.import_time:.2f}s")
            cli.info(f"Request ID: {result.request_id}")

            if result.event_data:
                # Show the full event data
                cli.section("Event Data")
                cli.event_card(result.event_data.model_dump())

                # Show image search results if available (for web imports)
                if result.event_data.image_search:
                    cli.section("Image Enhancement Results")
                    cli.image_search_results(
                        result.event_data.image_search.model_dump()
                    )

                # Data completeness check
                cli.section("Data Quality")
                event = result.event_data
                checks = []

                # Required fields
                checks.append(
                    {
                        "Field": "Title",
                        "Status": "✓" if event.title else "✗",
                        "Value": event.title or "Missing",
                    }
                )
                checks.append(
                    {
                        "Field": "Venue",
                        "Status": "✓" if event.venue else "✗",
                        "Value": event.venue or "Missing",
                    }
                )
                checks.append(
                    {
                        "Field": "Date",
                        "Status": "✓" if event.date else "✗",
                        "Value": event.date or "Missing",
                    }
                )

                # Optional but important fields
                time_val = (
                    f"{event.time.start} - {event.time.end}"
                    if event.time and event.time.start
                    else "Missing"
                )
                checks.append(
                    {
                        "Field": "Time",
                        "Status": "✓" if event.time else "✗",
                        "Value": time_val,
                    }
                )

                lineup_val = (
                    f"{len(event.lineup)} artists" if event.lineup else "Missing"
                )
                checks.append(
                    {
                        "Field": "Lineup",
                        "Status": "✓" if event.lineup else "✗",
                        "Value": lineup_val,
                    }
                )

                desc_val = "Present" if event.long_description else "Missing"
                checks.append(
                    {
                        "Field": "Description",
                        "Status": "✓" if event.long_description else "✗",
                        "Value": desc_val,
                    }
                )

                img_val = "Present" if event.images else "Missing"
                checks.append(
                    {
                        "Field": "Images",
                        "Status": "✓" if event.images else "✗",
                        "Value": img_val,
                    }
                )

                cli.table(checks, title="Field Completeness")

                # Show raw data if requested
                if show_raw and result.raw_data:
                    cli.section("Raw Extracted Data")
                    cli.raw_data(result.raw_data)

        else:
            cli.error(f"Status: FAILED")
            cli.error(f"Error: {result.error}")
            if result.method_used:
                cli.info(f"Method attempted: {result.method_used.value}")

        # Show progress timeline
        if len(progress_history) > 1:
            cli.section("Progress Timeline")
            for update in progress_history:
                timestamp = datetime.fromisoformat(update["timestamp"]).strftime(
                    "%H:%M:%S"
                )
                cli.info(f"{timestamp} - {update['message']}")

    except asyncio.TimeoutError:
        cli.error("Import timed out")
    except Exception as e:
        cli.error(f"Unexpected error: {e}")
        import traceback

        cli.code(traceback.format_exc(), "python", "Exception Traceback")


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
                cli.rule(f"Test {i} of {len(test_urls)}")

            start = datetime.now()
            await test_import(url, cli, show_raw)
            duration = (datetime.now() - start).total_seconds()

            # Check if successful
            total_time += duration
            # Note: We'd need to modify test_import to return success status
            # For now, we'll just track time

            if i < len(test_urls):
                # Brief pause between tests
                await asyncio.sleep(1)

        # Summary
        cli.rule("Test Summary")
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
