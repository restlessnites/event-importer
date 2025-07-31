#!/usr/bin/env -S uv run python
"""Simple test to verify Google Custom Search API is working with CLI."""

import clicycle
import pytest
from dotenv import load_dotenv

from app.config import get_config

# Load environment variables
load_dotenv()


@pytest.mark.asyncio
async def test_google_api(http_service) -> None:
    """Test Google Custom Search API directly."""
    clicycle.configure(app_name="event-importer-test")
    clicycle.header("Google Custom Search API Test")
    clicycle.info("Testing direct API access")

    # Get config which loads .env automatically
    config = get_config()

    api_key = config.api.google_api_key
    cse_id = config.api.google_cse_id

    clicycle.section("Checking credentials")

    if not api_key or not cse_id:
        pytest.skip(
            "Google Search API not configured! Set GOOGLE_API_KEY and GOOGLE_CSE_ID."
        )

    clicycle.success("Google API credentials found")
    credentials = {
        "API Key": f"{api_key[:10]}..." if api_key else "None",
        "CSE ID": f"{cse_id[:10]}..." if cse_id else "None",
    }
    clicycle.table([credentials], title="Credentials (masked)")

    # Test query
    query = "Bonobo live set"

    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "searchType": "image",
        "num": 5,
        "imgSize": "large",
        "imgType": "photo",
    }

    clicycle.section("Testing search")
    clicycle.info(f"Query: {query}")
    clicycle.info("API endpoint: https://www.googleapis.com/customsearch/v1")

    clicycle.info(f"Searching for '{query}'...")
    response = await http_service.get_json(
        "https://www.googleapis.com/customsearch/v1",
        params=params,
        service="GoogleSearch",
    )

    # Assert that the API call was successful and returned results
    assert "error" not in response, f"API Error: {response.get('error')}"
    assert "items" in response and response["items"], "No 'items' found in response"

    clicycle.success(f"Found {len(response['items'])} results")

    # Display results in a table
    clicycle.section("Search Results")

    results = []
    for i, item in enumerate(response["items"], 1):
        result = {
            "#": str(i),
            "Title": item.get("title", "No title")[:40],
            "Size": "Unknown",
            "URL": item.get("link", "No URL"),
        }

        if "image" in item and item["image"].get("width"):
            result["Size"] = (
                f"{item['image']['width']}x{item['image'].get('height', '?')}"
            )

        results.append(result)

    clicycle.table(results, title="Image Search Results")

    # Show API usage info if available
    if "searchInformation" in response:
        info = response["searchInformation"]
        clicycle.section("Search Information")
        clicycle.info(f"Total results: {info.get('totalResults', 'Unknown')}")
        clicycle.info(f"Search time: {info.get('searchTime', 'Unknown')}s")

    clicycle.success("Google API test completed")


if __name__ == "__main__":
    try:
        # This would need proper fixtures when run standalone
        print("Run with pytest for proper fixture support")
    except KeyboardInterrupt:
        clicycle.warning("Test interrupted by user")
