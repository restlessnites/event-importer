#!/usr/bin/env python3
"""Manual test script for the rebuild descriptions API."""

import asyncio

import httpx

# Base URL for the API
BASE_URL = "http://localhost:8000/api/v1"


async def test_import_event():
    """Import an event first to have something to rebuild."""
    async with httpx.AsyncClient() as client:
        # Import an event
        response = await client.post(
            f"{BASE_URL}/events/import",
            json={
                "url": "https://www.residentadvisor.net/events/2024/1234567",
                "timeout": 30
            }
        )

        if response.status_code == 200:
            data = response.json()
            print("✓ Event imported successfully")
            print(f"  Event ID: {data.get('event_id', 'N/A')}")
            print(f"  Title: {data['data']['title']}")
            print(f"  Short desc: {data['data'].get('short_description', 'None')}")
            print(f"  Long desc: {data['data'].get('long_description', 'None')[:100]}...")
            return data.get('event_id')
        print(f"✗ Import failed: {response.status_code}")
        print(f"  {response.text}")
        return None


async def test_rebuild_without_context(event_id: int):
    """Test rebuilding descriptions without supplementary context."""
    async with httpx.AsyncClient() as client:
        print(f"\nTesting rebuild without context for event {event_id}...")

        response = await client.post(
            f"{BASE_URL}/events/{event_id}/rebuild-descriptions"
        )

        if response.status_code == 200:
            data = response.json()
            print("✓ Rebuild successful")
            print(f"  Short desc: {data['data'].get('short_description', 'None')}")
            print(f"  Long desc: {data['data'].get('long_description', 'None')[:100]}...")
        else:
            print(f"✗ Rebuild failed: {response.status_code}")
            print(f"  {response.text}")


async def test_rebuild_with_context(event_id: int):
    """Test rebuilding descriptions with supplementary context."""
    async with httpx.AsyncClient() as client:
        print(f"\nTesting rebuild with context for event {event_id}...")

        context = "This is a special holiday edition event with surprise guest DJs and extended sets until 6am."

        response = await client.post(
            f"{BASE_URL}/events/{event_id}/rebuild-descriptions",
            json={"supplementary_context": context}
        )

        if response.status_code == 200:
            data = response.json()
            print("✓ Rebuild with context successful")
            print(f"  Context: {context}")
            print(f"  Short desc: {data['data'].get('short_description', 'None')}")
            print(f"  Long desc: {data['data'].get('long_description', 'None')[:200]}...")
        else:
            print(f"✗ Rebuild failed: {response.status_code}")
            print(f"  {response.text}")


async def test_rebuild_not_found():
    """Test rebuilding a non-existent event."""
    async with httpx.AsyncClient() as client:
        print("\nTesting rebuild for non-existent event...")

        response = await client.post(
            f"{BASE_URL}/events/999999/rebuild-descriptions"
        )

        if response.status_code == 404:
            print("✓ Correctly returned 404 for non-existent event")
        else:
            print(f"✗ Unexpected status: {response.status_code}")
            print(f"  {response.text}")


async def main():
    """Run all tests."""
    print("Event Description Rebuild API Test")
    print("==================================")

    # First, check if the API is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                print("✗ API is not running. Please start it with: make run-api")
                return
    except httpx.ConnectError:
        print("✗ Cannot connect to API. Please start it with: make run-api")
        return

    print("✓ API is running\n")

    # Import an event first
    event_id = await test_import_event()

    if event_id:
        # Test rebuild without context
        await test_rebuild_without_context(event_id)

        # Wait a bit between requests
        await asyncio.sleep(1)

        # Test rebuild with context
        await test_rebuild_with_context(event_id)

    # Test non-existent event
    await test_rebuild_not_found()

    print("\n✓ All tests completed")


if __name__ == "__main__":
    asyncio.run(main())
