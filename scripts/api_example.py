#!/usr/bin/env python3
"""
Example script demonstrating how to use the Event Importer HTTP API.

This script shows how to:
1. Start the API server programmatically
2. Make requests to import events
3. Check the health endpoint
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aiohttp

# Example URLs to test with
EXAMPLE_URLS = [
    "https://ra.co/events/1234567",  # Example RA URL
    "https://www.ticketmaster.com/event/123",  # Example Ticketmaster URL
]


@asynccontextmanager
async def api_client() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Create an HTTP client for API requests."""
    async with aiohttp.ClientSession() as session:
        yield session


async def check_health(base_url: str = "http://localhost:8000") -> bool | None:
    """Check if the API is healthy."""
    async with api_client() as client:
        try:
            async with client.get(f"{base_url}/api/v1/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ API is healthy!")
                    print(f"   Version: {data['version']}")
                    print(f"   Features: {', '.join(data['features'])}")
                    return True
                else:
                    print(f"❌ API health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Failed to connect to API: {e}")
            return False


async def import_event(url: str, base_url: str = "http://localhost:8000") -> None:
    """Import an event via the API."""
    async with api_client() as client:
        try:
            # Prepare request
            request_data = {"url": url, "timeout": 60, "include_raw_data": False}

            print(f"🔄 Importing event from: {url}")

            # Make request
            async with client.post(
                f"{base_url}/api/v1/events/import",
                json=request_data,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("success"):
                        print("✅ Import successful!")
                        print(f"   Method used: {data.get('method_used')}")
                        print(f"   Import time: {data.get('import_time', 0):.2f}s")

                        # Display event data
                        event_data = data.get("data", {})
                        if event_data:
                            print(f"   Title: {event_data.get('title', 'N/A')}")
                            print(f"   Venue: {event_data.get('venue', 'N/A')}")
                            print(f"   Date: {event_data.get('date', 'N/A')}")

                            lineup = event_data.get("lineup", [])
                            if lineup:
                                print(
                                    f"   Artists: {', '.join(lineup[:3])}{'...' if len(lineup) > 3 else ''}"
                                )
                    else:
                        print(f"❌ Import failed: {data.get('error', 'Unknown error')}")

                else:
                    error_data = await response.json()
                    print(f"❌ API request failed: {response.status}")
                    print(f"   Error: {error_data.get('detail', 'Unknown error')}")

        except Exception as e:
            print(f"❌ Failed to import event: {e}")


async def main() -> None:
    """Main example function."""
    print("🚀 Event Importer API Example")
    print("=" * 40)

    # Check if API is running
    print("\n1. Checking API health...")
    if not await check_health():
        print("\n💡 To start the API server, run:")
        print("   event-importer api --port 8000")
        print("   # or")
        print("   event-importer-api --port 8000")
        return

    # Import example events
    print("\n2. Importing example events...")
    for i, url in enumerate(EXAMPLE_URLS, 1):
        print(f"\n   Example {i}:")
        await import_event(url)

        # Add delay between requests
        if i < len(EXAMPLE_URLS):
            await asyncio.sleep(1)

    print("\n✨ Example completed!")
    print("\n💡 You can also test the API manually:")
    print("   curl -X POST http://localhost:8000/api/v1/events/import \\")
    print("        -H 'Content-Type: application/json' \\")
    print('        -d \'{"url": "https://example.com/event"}\'')


if __name__ == "__main__":
    asyncio.run(main())
