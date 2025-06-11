#!/usr/bin/env -S uv run python
"""Test the error capture system."""

import asyncio
import logging

from app.shared.http import get_http_service, close_http_service
from app.interfaces.cli import get_cli


async def test_error_capture():
    """Test error capture functionality."""
    cli = get_cli()

    cli.header("Error Capture Test", "Testing clean error display")

    # Test 1: Generate some errors while capturing
    cli.section("Test 1: Capturing Errors")

    # Start capturing
    cli.error_capture.start(logging.WARNING)

    # Generate some log messages
    logger = logging.getLogger("app.test")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    http = get_http_service()

    try:
        # This should fail with 403
        await http.get("https://dice.fm/test", service="TestService")
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
        logger = logging.getLogger("app.another")
        logger.warning("Context manager warning")
        logger.error("Context manager error", exc_info=Exception("Test exception"))

    cli.success("Context test completed")
    cli.show_captured_errors("Captured in Context")

    # Clean up
    await close_http_service()


if __name__ == "__main__":
    asyncio.run(test_error_capture())
