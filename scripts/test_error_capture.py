#!/usr/bin/env -S uv run python
"""Test the error capture system."""

import asyncio
import logging
import pytest

from app.interfaces.cli import get_cli
from app.shared.http import close_http_service, get_http_service
from app.interfaces.cli.error_capture import ErrorCapture
from app.shared.http import HTTPService


@pytest.mark.asyncio
async def test_error_capture(capsys, cli: "CLI", http_service: HTTPService) -> None:
    """Test error capture functionality."""
    cli.header("Error Capture Test", "Testing clean error display")

    # Test 1: Generate some errors while capturing
    cli.section("Test 1: Capturing Errors")

    # Start capturing
    cli.error_capture.start(logging.WARNING)

    # Generate some log messages
    logger = logging.getLogger("app.test")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    try:
        # This should fail with 403
        await http_service.get("https://dice.fm/test", service="TestService")
    except Exception as e:
        logger.error(f"Failed to fetch URL: {e}")

    # Stop capturing
    cli.error_capture.stop()

    # Show what we captured
    cli.success("Test completed")
    cli.show_captured_errors("Captured During Test")

    # Test 2: Using context manager
    cli.section("Test 2: Context Manager")

    async with cli.error_capture.capture():
        # This should also be captured
        logger.info("This is in a context manager")
        try:
            await http_service.get(
                "https://dice.fm/another-test", service="TestService"
            )
        except Exception as e:
            logger.error(f"Another failed fetch: {e}")

    cli.show_captured_errors("Captured in Context")


if __name__ == "__main__":
    asyncio.run(test_error_capture())
