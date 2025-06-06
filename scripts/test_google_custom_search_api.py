#!/usr/bin/env -S uv run python
"""Simple test to verify Google Custom Search API is working."""

import asyncio
import os
from urllib.parse import urlencode
from dotenv import load_dotenv

from app.http import get_http_service, close_http_service

# Load environment variables
load_dotenv()


async def test_google_api():
    """Test Google Custom Search API directly."""
    # Get config which loads .env automatically
    from app.config import get_config

    config = get_config()

    api_key = config.api.google_api_key
    cse_id = config.api.google_cse_id

    if not api_key or not cse_id:
        print("❌ Google API credentials not found!")
        print("Set GOOGLE_API_KEY and GOOGLE_CSE_ID in .env")
        return

    print("✅ Google API credentials found")
    print(f"API Key: {api_key[:10]}..." if api_key else "None")
    print(f"CSE ID: {cse_id[:10]}..." if cse_id else "None")

    http = get_http_service()

    # Test query
    query = '"Cursive" band photo'

    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "searchType": "image",
        "num": 5,
        "imgSize": "large",
        "imgType": "photo",
    }

    print(f"\nTesting search for: {query}")
    print(f"API URL: https://www.googleapis.com/customsearch/v1?{urlencode(params)}")

    try:
        response = await http.get_json(
            "https://www.googleapis.com/customsearch/v1",
            service="Google",
            params=params,
        )

        if "error" in response:
            print(f"\n❌ API Error: {response['error']}")
            return

        if "items" not in response:
            print(f"\n⚠️ No results found")
            print(f"Response: {response}")
            return

        print(f"\n✅ Found {len(response['items'])} results:")
        for i, item in enumerate(response["items"], 1):
            print(f"\n{i}. {item.get('title', 'No title')}")
            print(f"   URL: {item.get('link', 'No URL')}")
            if "image" in item:
                print(
                    f"   Size: {item['image'].get('width')}x{item['image'].get('height')}"
                )

    except Exception as e:
        print(f"\n💥 Request failed: {e}")

    await close_http_service()


if __name__ == "__main__":
    asyncio.run(test_google_api())
