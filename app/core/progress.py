"""Simple progress tracking for event imports."""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from app.schemas import ImportProgress, ImportStatus

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks and distributes progress updates for import requests."""

    def __init__(self: "ProgressTracker") -> None:
        """Initialize the progress tracker."""
        self._listeners: dict[str, list[Callable]] = defaultdict(list)
        self._history: dict[str, list[ImportProgress]] = defaultdict(list)
        self._max_history = 100

    def add_listener(
        self: "ProgressTracker",
        request_id: str,
        callback: Callable[[ImportProgress], Awaitable[None]],
    ) -> None:
        """Add a progress listener for a request."""
        self._listeners[request_id].append(callback)

    def remove_listener(
        self: "ProgressTracker",
        request_id: str,
        callback: Callable[[ImportProgress], Awaitable[None]],
    ) -> None:
        """Remove a progress listener."""
        if request_id in self._listeners:
            try:
                self._listeners[request_id].remove(callback)
                if not self._listeners[request_id]:
                    del self._listeners[request_id]
            except ValueError:
                pass

    async def send_progress(self: "ProgressTracker", progress: ImportProgress) -> None:
        """Send progress update to all listeners."""
        request_id = progress.request_id

        # Store in history
        history = self._history[request_id]
        history.append(progress)
        if len(history) > self._max_history:
            history.pop(0)

        # Send to listeners
        listeners = self._listeners.get(request_id, [])
        if listeners:
            # Send to all listeners concurrently
            tasks = [self._safe_send(listener, progress) for listener in listeners]
            await asyncio.gather(*tasks)

        # Clean up if terminal status
        if progress.status in (
            ImportStatus.SUCCESS,
            ImportStatus.FAILED,
            ImportStatus.CANCELLED,
        ):
            self._listeners.pop(request_id, None)

    async def _safe_send(
        self: "ProgressTracker",
        callback: Callable[[ImportProgress], Awaitable[None]],
        progress: ImportProgress,
    ) -> None:
        """Safely send progress to a callback."""
        try:
            await callback(progress)
        except (ValueError, TypeError, KeyError):
            logger.exception("Error sending progress")

    def get_history(self: "ProgressTracker", request_id: str) -> list[ImportProgress]:
        """Get progress history for a request."""
        return list(self._history.get(request_id, []))
