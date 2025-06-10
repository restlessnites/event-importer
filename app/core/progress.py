"""Simple progress tracking for event imports."""

import asyncio
import logging
from typing import Dict, List, Callable, Awaitable, Optional
from collections import defaultdict

from app.schemas import ImportProgress, ImportStatus


logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks and distributes progress updates for import requests."""

    def __init__(self):
        """Initialize the progress tracker."""
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._history: Dict[str, List[ImportProgress]] = defaultdict(list)
        self._max_history = 100

    def add_listener(
        self, request_id: str, callback: Callable[[ImportProgress], Awaitable[None]]
    ) -> None:
        """Add a progress listener for a request."""
        self._listeners[request_id].append(callback)

    def remove_listener(
        self, request_id: str, callback: Callable[[ImportProgress], Awaitable[None]]
    ) -> None:
        """Remove a progress listener."""
        if request_id in self._listeners:
            try:
                self._listeners[request_id].remove(callback)
                if not self._listeners[request_id]:
                    del self._listeners[request_id]
            except ValueError:
                pass

    async def send_progress(self, progress: ImportProgress) -> None:
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
        self,
        callback: Callable[[ImportProgress], Awaitable[None]],
        progress: ImportProgress,
    ) -> None:
        """Safely send progress to a callback."""
        try:
            await callback(progress)
        except Exception as e:
            logger.error(f"Error sending progress: {e}")

    def get_history(self, request_id: str) -> List[ImportProgress]:
        """Get progress history for a request."""
        return list(self._history.get(request_id, []))

    def clear_history(self, request_id: str) -> None:
        """Clear history for a request."""
        self._history.pop(request_id, None)

    def get_latest_status(self, request_id: str) -> Optional[ImportStatus]:
        """Get the latest status for a request."""
        history = self._history.get(request_id)
        if history:
            return history[-1].status
        return None
