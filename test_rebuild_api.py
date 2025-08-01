#!/usr/bin/env python3
"""Manual test script for the rebuild descriptions API."""

import asyncio

import aiohttp

# Base URL for the API
BASE_URL = "http://localhost:8000/api/v1"


async def test_import_event():
    """Import an event first to have something to rebuild."""
    async with aiohttp.ClientSession() as session:
        # Import an event
        response = await session.post(
            f"{BASE_URL}/events/import",
            json={
                "url": "https://www.residentadvisor.net/events/2024/1234567",
                "timeout": 30,
            },
        )

        if response.status == 200:
            data = await response.json()
            print("✓ Event imported successfully")
            print(f"  Event ID: {data.get('event_id', 'N/A')}")
            print(f"  Title: {data['data']['title']}")
            print(f"  Short desc: {data['data'].get('short_description', 'None')}")
            print(
                f"  Long desc: {data['data'].get('long_description', 'None')[:100]}..."
            )
            return data.get("event_id")
        print(f"✗ Import failed: {response.status}")
        print(f"  {await response.text()}")
        return None


async def test_rebuild_without_context(event_id: int):
    """Test rebuilding descriptions without supplementary context."""
    async with aiohttp.ClientSession() as session:
        print(f"\nTesting rebuild without context for event {event_id}...")

        response = await session.post(
            f"{BASE_URL}/events/{event_id}/rebuild-descriptions"
        )

        if response.status == 200:
            data = await response.json()
            print("✓ Rebuild successful")
            print(f"  Short desc: {data['data'].get('short_description', 'None')}")
            print(
                f"  Long desc: {data['data'].get('long_description', 'None')[:100]}..."
            )
        else:
            print(f"✗ Rebuild failed: {response.status}")
            print(f"  {await response.text()}")


async def test_rebuild_with_context(event_id: int):
    """Test rebuilding descriptions with supplementary context."""
    async with aiohttp.ClientSession() as session:
        print(f"\nTesting rebuild with context for event {event_id}...")

        context = "This is a special holiday edition event with surprise guest DJs and extended sets until 6am."

        response = await session.post(
            f"{BASE_URL}/events/{event_id}/rebuild-descriptions",
            json={"supplementary_context": context},
        )

        if response.status == 200:
            data = await response.json()
            print("✓ Rebuild with context successful")
            print(f"  Context: {context}")
            print(f"  Short desc: {data['data'].get('short_description', 'None')}")
            print(
                f"  Long desc: {data['data'].get('long_description', 'None')[:200]}..."
            )
        else:
            print(f"✗ Rebuild failed: {response.status}")
            print(f"  {await response.text()}")


async def test_rebuild_not_found():
    """Test rebuilding a non-existent event."""
    async with aiohttp.ClientSession() as session:
        print("\nTesting rebuild for non-existent event...")

        response = await session.post(f"{BASE_URL}/events/999999/rebuild-descriptions")

        if response.status == 404:
            print("✓ Correctly returned 404 for non-existent event")
        else:
            print(f"✗ Unexpected status: {response.status}")
            print(f"  {await response.text()}")


async def main():
    """Run all tests."""
    print("=== Event Rebuild API Test ===")

    # First import an event
    event_id = await test_import_event()

    if event_id:
        # Test rebuilding without context
        await test_rebuild_without_context(event_id)

        # Test rebuilding with context
        await test_rebuild_with_context(event_id)

    # Test not found case
    await test_rebuild_not_found()

    print("\n=== Tests complete ===")


if __name__ == "__main__":
    asyncio.run(main())
