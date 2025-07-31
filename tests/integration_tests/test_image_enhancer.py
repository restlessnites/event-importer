#!/usr/bin/env -S uv run python
"""Test script to debug image search functionality with CLI."""

import asyncio
import logging

import clicycle
import pytest
from dotenv import load_dotenv

from app.services.image import ImageService

# Load environment variables
load_dotenv()

# Set logging to WARNING to reduce noise (but still capture them)
logging.basicConfig(level=logging.WARNING)


@pytest.mark.asyncio
async def test_rate_image_logic(capsys, image_service: ImageService, monkeypatch):
    """Test the logic of the rate_image method by mocking its dependencies."""
    clicycle.configure(app_name="event-importer-test")
    clicycle.header("Image Rating Logic Test")

    # Mock the internal validate_and_download to control test conditions
    async def mock_validate_and_download(url, max_size=None, http_service=None):
        # Simulate a successful download of a good image
        if "good-image" in url:
            # A valid 1x1 PNG image in bytes
            valid_png_data = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00"
                b"\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDAT"
                b"x\x9cc`\x00\x00\x00\x02\x00\x01\xe2!\xb3`\x82\x00\x00\x00\x00IEND"
                b"\xaeB`\x82"
            )
            return valid_png_data, "image/png"
        # Simulate a failed download or invalid image
        return None

    monkeypatch.setattr(
        image_service, "validate_and_download", mock_validate_and_download
    )

    test_cases = [
        {
            "url": "https://good-image.com/high-quality.jpg",
            "description": "Good quality, standard domain",
            "expected_min_score": 30,  # Base score for size
        },
        {
            "url": "https://some-other-server.com/path/to/low-quality-image.jpg",
            "description": "Invalid or inaccessible image",
            "expected_score": 0,
        },
        {
            "url": "https://spotify.com/good-image.jpg",
            "description": "Good quality, priority domain",
            "expected_min_score": 50,  # Base score + priority domain bonus
        },
        {
            "url": "https://getty.com/bad-image.jpg",
            "description": "Blacklisted domain",
            "expected_score": 0,
        },
    ]

    for case in test_cases:
        clicycle.section(f"Testing Case: {case['description']}")
        url = case["url"]
        clicycle.info(f"URL: {url}")

        result_candidate = await image_service.rate_image(url)
        score = result_candidate.score
        clicycle.info(f"Score: {score}")
        clicycle.info(f"Reason: {result_candidate.reason}")

        if "expected_score" in case:
            assert score == case["expected_score"]
            clicycle.success(f"Passed: Score is exactly {case['expected_score']}")
        if "expected_min_score" in case:
            assert score >= case["expected_min_score"]
            clicycle.success(
                f"Passed: Score {score} is >= {case['expected_min_score']}"
            )

    captured = capsys.readouterr()
    assert "IMAGE RATING LOGIC TEST" in captured.out


async def main() -> None:
    """Run tests based on command line arguments."""
    clicycle.configure(app_name="event-importer-test")

    try:
        clicycle.info("Run with pytest for proper fixture support")
    except KeyboardInterrupt:
        clicycle.warning("Test interrupted by user")
    except Exception as e:
        clicycle.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
