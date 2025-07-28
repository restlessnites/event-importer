#!/usr/bin/env -S uv run python
"""Test the error capture system."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.shared.http import HTTPService

if TYPE_CHECKING:
    from app.interfaces.cli.core import CLI


@pytest.mark.asyncio
async def test_error_capture(
    capsys,
    cli: CLI,
    http_service: HTTPService,  # noqa: ARG001
) -> None:
    """Test error capture functionality."""
    cli.header("Error Capture Test", "Testing clean error display")
    cli.error_capture.clear()

    # Capture some errors
    async with cli.error_capture.capture():
        cli.error("This is a test error")
        cli.warning("This is a test warning")

    # Display errors
    cli.show_captured_errors("Captured Issues")

    # Check that the summary is in the output
    captured = capsys.readouterr()
    assert "This is a test error" in captured.out
    assert "This is a test warning" in captured.out
