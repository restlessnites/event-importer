#!/usr/bin/env -S uv run python
"""Simple test to verify Google Custom Search API is working with CLI."""

import asyncio
import traceback

import pytest
from dotenv import load_dotenv

from app.config import get_config
from app.interfaces.cli.runner import get_cli
from app.shared.http import close_http_service

# Load environment variables
load_dotenv()

# Initialize CLI
cli = get_cli()


@pytest.mark.asyncio
async def test_google_api(cli, http_service) -> None:
    """Test Google Custom Search API directly."""
    cli.header("Google Custom Search API Test", "Testing direct API access")

    # Get config which loads .env automatically
    config = get_config()

    api_key = config.api.google_api_key
    cse_id = config.api.google_cse_id

    cli.section("Checking credentials")

    if not api_key or not cse_id:
        cli.error("Google Search API not configured!")
        cli.info("Set GOOGLE_API_KEY and GOOGLE_CSE_ID in .env file")
        return

    cli.success("Google API credentials found")
    credentials = {
        "API Key": f"{api_key[:10]}..." if api_key else "None",
        "CSE ID": f"{cse_id[:10]}..." if cse_id else "None",
    }
    cli.table([credentials], title="Credentials (masked)")

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

    cli.section("Testing search")
    cli.info(f"Query: {query}")
    cli.info("API endpoint: https://www.googleapis.com/customsearch/v1")
    cli.console.print()

    # Start capturing errors
    async with cli.error_capture.capture():
        try:
            with cli.spinner(f"Searching for '{query}'..."):
                response = await http_service.get_json(
                    "https://www.googleapis.com/customsearch/v1",
                    params=params,
                    service="GoogleSearch",
                )

            if "error" in response:
                cli.error(
                    f"API Error: {response['error'].get('message', 'Unknown error')}"
                )
                if "code" in response["error"]:
                    cli.info(f"Error code: {response['error']['code']}")
                return

            if "items" not in response:
                cli.warning("No results found")
                cli.json(response, title="API Response")
                return

            cli.success(f"Found {len(response['items'])} results")

            # Display results in a table
            cli.section("Search Results")

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

            cli.table(results, title="Image Search Results")

            # Show API usage info if available
            if "searchInformation" in response:
                info = response["searchInformation"]
                cli.section("Search Information")
                cli.info(f"Total results: {info.get('totalResults', 'Unknown')}")
                cli.info(f"Search time: {info.get('searchTime', 'Unknown')}s")

        except Exception as e:
            cli.error(f"Request failed: {e}")
            cli.code(traceback.format_exc(), "python", "Traceback")

    # Show any captured errors
    if cli.error_capture.has_errors() or cli.error_capture.has_warnings():
        cli.show_captured_errors("Issues During Test")

    await close_http_service()
    cli.console.print()
    cli.success("Google API test completed")


if __name__ == "__main__":
    try:
        asyncio.run(test_google_api())
    except KeyboardInterrupt:
        cli = get_cli()
        cli.warning("\nTest interrupted by user")
