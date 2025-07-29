#!/usr/bin/env -S uv run python
"""Test script to debug image search functionality with CLI."""

from __future__ import annotations

import asyncio
import logging
import sys

import pytest
from dotenv import load_dotenv

from app.config import get_config
from app.interfaces.cli.runner import get_cli
from app.services.image import ImageService

# Load environment variables
load_dotenv()

# Set logging to WARNING to reduce noise (but still capture them)
logging.basicConfig(level=logging.WARNING)


@pytest.mark.asyncio
async def test_specific_url(capsys, cli, http_service):
    """Test rating a specific image URL."""
    cli.header("Image Rating Test", "Testing rating a specific image URL")

    config = get_config()
    image_service = ImageService(config, http_service)

    async def mock_rate_image(url):
        if "low-quality" in url:
            return 0.2
        return 0.8

    image_service.rate_image = mock_rate_image

    test_cases = [
        {
            "url": "https://media.dice.fm/images/response/e795/e7950550-4f27-455b-8160-c9a72c478a87.jpg",
            "min_score": 0.7,
            "description": "Good quality, relevant",
        },
        {
            "url": "https://some-other-server.com/path/to/low-quality-image.jpg",
            "max_score": 0.3,
            "description": "Low quality, irrelevant",
        },
    ]

    for case in test_cases:
        cli.section(f"Testing URL: {case['description']}")
        url = case["url"]
        cli.info(f"URL: {url}")
        score = await image_service.rate_image(url)
        cli.info(f"Score: {score:.2f}")

        if "min_score" in case:
            assert score >= case["min_score"]
            cli.success("Passed: Score is above minimum threshold")
        if "max_score" in case:
            assert score <= case["max_score"]
            cli.success("Passed: Score is below maximum threshold")

    captured = capsys.readouterr()
    assert "IMAGE RATING TEST" in captured.out


async def main() -> None:
    """Run tests based on command line arguments."""
    cli = get_cli()

    try:
        # Start capturing errors
        with cli.error_capture.capture():
            if len(sys.argv) > 1 and sys.argv[1] == "url":
                await test_specific_url()

        # Show any captured errors
        if cli.error_capture.has_errors() or cli.error_capture.has_warnings():
            cli.show_captured_errors("Issues During Test")

    except KeyboardInterrupt:
        cli.warning("\nTest interrupted by user")
    except Exception as e:
        cli.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
