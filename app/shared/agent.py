"""Base agent class for event import agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from app.config import Config
from app.schemas import EventData, ImportMethod, ImportProgress, ImportStatus

logger = logging.getLogger(__name__)


class Agent(ABC):
    """Base class for all import agents."""

    def __init__(
        self: Agent,
        config: Config,
        progress_callback: Callable[[ImportProgress], Awaitable[None]] | None = None,
        services: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize agent.

        Args:
            config: Application configuration
            progress_callback: Optional callback for progress updates
            services: Required shared services dict
        """
        self.config = config
        self.progress_callback = progress_callback
        
        # Validate services
        if services is None:
            raise ValueError("services dictionary is required but was None")
        
        # Validate required services exist
        required_services = ["http", "llm"]
        missing_services = [svc for svc in required_services if svc not in services]
        if missing_services:
            raise ValueError(f"Missing required services: {missing_services}")
        
        # Validate services are not None
        none_services = [svc for svc in required_services if services[svc] is None]
        if none_services:
            raise ValueError(f"Required services are None: {none_services}")
        
        self.services = services
        self._start_time = None

    def get_service(self: Agent, service_name: str) -> Any:
        """
        Safely get a service with proper error handling.
        
        Args:
            service_name: Name of the service to retrieve
            
        Returns:
            The service instance
            
        Raises:
            ValueError: If service is not available or is None
        """
        if not self.services:
            raise ValueError("Services dictionary is not initialized")
        
        service = self.services.get(service_name)
        if service is None:
            raise ValueError(f"Service '{service_name}' is not available or is None")
        
        return service

    @property
    @abstractmethod
    def name(self: Agent) -> str:
        """Agent name for logging."""
        pass

    @property
    @abstractmethod
    def import_method(self: Agent) -> ImportMethod:
        """The import method this agent uses."""
        pass

    @abstractmethod
    async def import_event(self: Agent, url: str, request_id: str) -> EventData | None:
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
            except Exception as e:
                logger.error(f"Failed to send progress update: {e}")

    def start_timer(self: Agent) -> None:
        """Start timing the import."""
        self._start_time = datetime.utcnow()

    def get_elapsed_time(self: Agent) -> float:
        """Get elapsed time in seconds."""
        if self._start_time:
            return (datetime.utcnow() - self._start_time).total_seconds()
        return 0.0
