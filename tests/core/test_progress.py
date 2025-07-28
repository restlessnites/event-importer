"""Tests for progress tracking."""

from unittest.mock import AsyncMock

import pytest

from app.core.progress import ProgressTracker
from app.schemas import ImportProgress, ImportStatus


@pytest.fixture
def progress_tracker():
    """Create a progress tracker instance."""
    return ProgressTracker()


@pytest.mark.asyncio
async def test_send_progress_with_listener(progress_tracker):
    """Test sending progress with a listener."""
    callback = AsyncMock()
    request_id = "test-123"

    # Add listener
    progress_tracker.add_listener(request_id, callback)

    # Send progress
    progress = ImportProgress(
        request_id=request_id,
        status=ImportStatus.RUNNING,
        message="Processing...",
        progress=0.5,
    )
    await progress_tracker.send_progress(progress)

    # Verify callback was called
    callback.assert_called_once_with(progress)


@pytest.mark.asyncio
async def test_send_progress_without_listener(progress_tracker):
    """Test sending progress without a listener."""
    # Should not raise an error
    progress = ImportProgress(
        request_id="test-123",
        status=ImportStatus.SUCCESS,
        message="Complete",
        progress=1.0,
    )
    await progress_tracker.send_progress(progress)


@pytest.mark.asyncio
async def test_remove_listener(progress_tracker):
    """Test removing a listener."""
    callback = AsyncMock()
    request_id = "test-456"

    # Add and then remove listener
    progress_tracker.add_listener(request_id, callback)
    progress_tracker.remove_listener(request_id, callback)

    # Send progress - callback should not be called
    progress = ImportProgress(
        request_id=request_id,
        status=ImportStatus.RUNNING,
        message="Processing...",
        progress=0.5,
    )
    await progress_tracker.send_progress(progress)

    callback.assert_not_called()


@pytest.mark.asyncio
async def test_multiple_listeners(progress_tracker):
    """Test multiple listeners for same request."""
    callback1 = AsyncMock()
    callback2 = AsyncMock()
    request_id = "test-789"

    # Add multiple listeners
    progress_tracker.add_listener(request_id, callback1)
    progress_tracker.add_listener(request_id, callback2)

    # Send progress
    progress = ImportProgress(
        request_id=request_id,
        status=ImportStatus.RUNNING,
        message="Processing...",
        progress=0.5,
    )
    await progress_tracker.send_progress(progress)

    # Both should be called
    callback1.assert_called_once_with(progress)
    callback2.assert_called_once_with(progress)


def test_get_history(progress_tracker):
    """Test getting progress history."""
    request_id = "test-history"

    # Initially empty
    history = progress_tracker.get_history(request_id)
    assert history == []

    # After sending progress, history is updated
    # (Note: this would normally be done via send_progress)


def test_clear_history(progress_tracker):
    """Test clearing progress history."""
    request_id = "test-clear"

    # Clear should work even on empty history
    progress_tracker.clear_history(request_id)

    history = progress_tracker.get_history(request_id)
    assert history == []


@pytest.mark.asyncio
async def test_listener_exception_handling(progress_tracker):
    """Test that exceptions in listeners don't break progress tracking."""
    good_callback = AsyncMock()
    bad_callback = AsyncMock(side_effect=ValueError("Callback error"))
    request_id = "test-exception"

    # Add both callbacks
    progress_tracker.add_listener(request_id, bad_callback)
    progress_tracker.add_listener(request_id, good_callback)

    # Send progress
    progress = ImportProgress(
        request_id=request_id,
        status=ImportStatus.RUNNING,
        message="Processing...",
        progress=0.5,
    )
    await progress_tracker.send_progress(progress)

    # Good callback should still be called despite bad one failing
    good_callback.assert_called_once_with(progress)
    bad_callback.assert_called_once_with(progress)
