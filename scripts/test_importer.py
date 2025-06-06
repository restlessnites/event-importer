#!/usr/bin/env -S uv run python
"""Test script for the event importer."""

import asyncio
import logging
from pprint import pprint

from app import EventImporter
from app.schemas import ImportRequest
from app.http import close_http_service


logging.basicConfig(level=logging.INFO)


async def test_import(url: str):
    """Test importing an event."""
    print(f"\n🔍 Testing import for: {url}")
    print("-" * 80)

    # Create importer
    importer = EventImporter()

    # Create request
    request = ImportRequest(url=url)

    # Track progress
    async def print_progress(progress):
        print(f"📊 [{progress.progress:.0%}] {progress.message}")

    importer.add_progress_listener(request.request_id, print_progress)

    try:
        # Run import
        result = await importer.import_event(request)

        if result.status == "success":
            print("\n✅ SUCCESS!")
            print(f"Method: {result.method_used}")
            print(f"Time: {result.import_time:.2f}s")
            print("\n📋 Event Data:")
            pprint(result.event_data.model_dump())
        else:
            print(f"\n❌ FAILED: {result.error}")

    except Exception as e:
        print(f"\n💥 Error: {e}")


async def main():
    """Run tests."""
    test_urls = [
        # Resident Advisor (real event)
        "https://ra.co/events/2147288",
        # Generic web page
        "https://dice.fm/event/53ng6k-cursive-13th-sep-zebulon-los-angeles-tickets",
        # Direct image (use a real event flyer URL)
        "https://imgproxy.ra.co/_/quality:66/w:1442/rt:fill/aHR0cHM6Ly9pbWFnZXMucmEuY28vNmEwZDhkMDNkOTFjMGJmZDE2NTFhMjgzYjI5MDVlMTc3OTQ2M2Y0OC5qcGc=",
    ]

    import sys

    if len(sys.argv) > 1:
        test_urls = [sys.argv[1]]

    try:
        for url in test_urls:
            await test_import(url)
            print("\n" + "=" * 80 + "\n")
    finally:
        # Clean up HTTP sessions
        await close_http_service()


if __name__ == "__main__":
    asyncio.run(main())
