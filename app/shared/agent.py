"""Base agent class for event import agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from app.config import Config
from app.schemas import EventData, EventLocation, EventTime, ImportMethod, ImportProgress, ImportStatus
from app.shared.timezone import get_timezone_from_location

logger = logging.getLogger(__name__)

# Error message constants
SERVICES_DICT_REQUIRED = "services dictionary is required but was None"
SERVICES_DICT_NOT_INITIALIZED = "Services dictionary is not initialized"


class Agent(ABC):
    """Base class for all import agents."""

    def __init__(
        self: Agent,
        config: Config,
        progress_callback: Callable[[ImportProgress], Awaitable[None]] | None = None,
        services: dict[str, Any] | None = None,
    ) -> None:
        """Initialize agent.

        Args:
            config: Application configuration
            progress_callback: Optional callback for progress updates
            services: Required shared services dict

        """
        self.config = config
        self.progress_callback = progress_callback

        # Validate services
        if services is None:
            raise ValueError(SERVICES_DICT_REQUIRED)

        # Validate required services exist
        required_services = ["http", "llm"]
        missing_services = [svc for svc in required_services if svc not in services]
        if missing_services:
            error_msg = f"Missing required services: {missing_services}"
            raise ValueError(error_msg)

        # Validate services are not None
        none_services = [svc for svc in required_services if services[svc] is None]
        if none_services:
            error_msg = f"Required services are None: {none_services}"
            raise ValueError(error_msg)

        self.services = services
        self._start_time = None

    def get_service(self: Agent, service_name: str) -> object:
        """Safely get a service with proper error handling.

        Args:
            service_name: Name of the service to retrieve

        Returns:
            The service instance

        Raises:
            ValueError: If service is not available or is None

        """
        if not self.services:
            raise ValueError(SERVICES_DICT_NOT_INITIALIZED)

        service = self.services.get(service_name)
        if service is None:
            error_msg = f"Service '{service_name}' is not available or is None"
            raise ValueError(error_msg)

        return service

    @property
    @abstractmethod
    def name(self: Agent) -> str:
        """Agent name for logging."""

    @property
    @abstractmethod
    def import_method(self: Agent) -> ImportMethod:
        """The import method this agent uses."""

    @abstractmethod
    async def import_event(self: Agent, url: str, request_id: str) -> EventData | None:
        """Import event data from the URL.

        Args:
            url: URL to import from
            request_id: Request ID for progress tracking

        Returns:
            Event data if successful, None otherwise

        """

    async def send_progress(
        self: Agent,
        request_id: str,
        status: ImportStatus,
        message: str,
        progress: float,
        data: EventData | None = None,
        error: str | None = None,
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
            except Exception:
                logger.exception("Failed to send progress update")

    def start_timer(self: Agent) -> None:
        """Start timing the import."""
        self._start_time = datetime.utcnow()

    def get_elapsed_time(self: Agent) -> float:
        """Get elapsed time in seconds."""
        if self._start_time:
            return (datetime.utcnow() - self._start_time).total_seconds()
        return 0.0

    def create_event_time(
        self: Agent,
        start: str | None = None,
        end: str | None = None,
        location: EventLocation | None = None,
        timezone: str | None = None,
    ) -> EventTime:
        """Create EventTime with automatic timezone detection from location.
        
        Args:
            start: Start time in HH:MM format
            end: End time in HH:MM format  
            location: Event location for timezone detection
            timezone: Explicit timezone (overrides location detection)
            
        Returns:
            EventTime with timezone populated
        """
        if timezone is None:
            timezone = get_timezone_from_location(location)
            
        return EventTime(
            start=start,
            end=end,
            timezone=timezone,
        )
