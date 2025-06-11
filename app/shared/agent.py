"""Base agent class for event import agents."""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable, Dict, Any
import logging
from datetime import datetime

from app.schemas import EventData, ImportProgress, ImportStatus, ImportMethod
from app.config import Config


logger = logging.getLogger(__name__)


class Agent(ABC):
    """Base class for all import agents."""

    def __init__(
        self,
        config: Config,
        progress_callback: Optional[Callable[[ImportProgress], Awaitable[None]]] = None,
        services: Dict[str, Any] = None,
    ):
        """
        Initialize agent.

        Args:
            config: Application configuration
            progress_callback: Optional callback for progress updates
            services: Required shared services dict
        """
        self.config = config
        self.progress_callback = progress_callback
        self.services = services
        self._start_time = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name for logging."""
        pass

    @property
    @abstractmethod
    def import_method(self) -> ImportMethod:
        """The import method this agent uses."""
        pass

    # REMOVED: can_handle() method - no longer needed with content-type routing

    @abstractmethod
    async def import_event(self, url: str, request_id: str) -> Optional[EventData]:
        """
        Import event data from the URL.

        Args:
            url: URL to import from
            request_id: Request ID for progress tracking

        Returns:
            Event data if successful, None otherwise
        """
        pass

    async def send_progress(
        self,
        request_id: str,
        status: ImportStatus,
        message: str,
        progress: float,
        data: Optional[EventData] = None,
        error: Optional[str] = None,
    ) -> None:
        """Send progress update if callback is available."""
        if self.progress_callback:
            update = ImportProgress(
                request_id=request_id,
                status=status,
                message=message,
                progress=progress,
                data=data,
                error=error,
            )
            try:
                await self.progress_callback(update)
            except Exception as e:
                logger.error(f"Failed to send progress update: {e}")

    def start_timer(self) -> None:
        """Start timing the import."""
        self._start_time = datetime.utcnow()

    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if self._start_time:
            return (datetime.utcnow() - self._start_time).total_seconds()
        return 0.0