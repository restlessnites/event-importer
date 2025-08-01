"""Base class for extraction agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from app.core.error_messages import AgentMessages
from app.core.schemas import (
    EventData,
    EventLocation,
    EventTime,
    ImportMethod,
    ImportProgress,
    ImportStatus,
)
from app.services.llm.service import LLMService
from app.shared.constants.error_messages import (
    SERVICES_DICT_NOT_INITIALIZED,
    SERVICES_DICT_REQUIRED,
)
from app.shared.constants.state_mappings import US_STATE_MAPPING
from app.shared.timezone import get_timezone_from_location
from config import Config

logger = logging.getLogger(__name__)


class BaseExtractionAgent(ABC):
    """Abstract base class for agents that extract event data."""

    state_mapping = US_STATE_MAPPING

    def __init__(
        self: BaseExtractionAgent,
        config: Config,
        progress_callback: Callable[[ImportProgress], Awaitable[None]] | None = None,
        services: dict[str, Any] | None = None,
    ) -> None:
        """Initialize agent."""
        self.config = config
        self.progress_callback = progress_callback

        if services is None:
            raise ValueError(SERVICES_DICT_REQUIRED)

        required_services = ["http", "llm"]
        missing_services = [svc for svc in required_services if svc not in services]
        if missing_services:
            raise ValueError(f"Missing required services: {missing_services}")

        none_services = [svc for svc in required_services if services[svc] is None]
        if none_services:
            raise ValueError(f"Required services are None: {none_services}")

        self.services = services
        self._start_time = datetime.now(UTC)

    def get_service(self: BaseExtractionAgent, service_name: str) -> Any:
        """Safely get a service with proper error handling."""
        if not self.services:
            raise ValueError(SERVICES_DICT_NOT_INITIALIZED)

        service = self.services.get(service_name)
        if service is None:
            raise ValueError(f"Service '{service_name}' is not available or is None")

        return service

    @property
    @abstractmethod
    def name(self: BaseExtractionAgent) -> str:
        """Agent name for logging."""

    @property
    @abstractmethod
    def import_method(self: BaseExtractionAgent) -> ImportMethod:
        """The import method this agent uses."""

    @abstractmethod
    async def _perform_extraction(self, url: str, request_id: str) -> EventData | None:
        """Provider-specific logic for extracting event data."""

    async def import_event(self, url: str, request_id: str) -> EventData | None:
        """Template method for importing an event."""
        self.start_timer()
        try:
            event_data = await self._perform_extraction(url, request_id)
            if not event_data:
                raise Exception(f"{self.name} agent failed to extract event data.")

            event_data = await self.enhance_descriptions(event_data, request_id)

            await self.send_progress(
                request_id,
                ImportStatus.SUCCESS,
                f"Successfully imported from {self.name}",
                1.0,
                data=event_data,
            )
            return event_data
        except Exception as e:
            logger.exception(f"{self.name} import failed")
            await self.send_progress(
                request_id,
                ImportStatus.FAILED,
                f"Import failed: {e!s}",
                1.0,
                error=str(e),
            )
            return None

    async def send_progress(
        self: BaseExtractionAgent,
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

    def start_timer(self: BaseExtractionAgent) -> None:
        """Start timing the import."""
        self._start_time = datetime.now(UTC)

    def create_event_time(
        self: BaseExtractionAgent,
        start: str | None = None,
        end: str | None = None,
        location: EventLocation | None = None,
        timezone: str | None = None,
    ) -> EventTime:
        """Create EventTime with automatic timezone detection from location."""
        if timezone is None:
            timezone = get_timezone_from_location(location)

        return EventTime(
            start=start,
            end=end,
            timezone=timezone,
        )

    async def enhance_descriptions(
        self, event_data: EventData, request_id: str
    ) -> EventData:
        """
        Enhance event descriptions using the LLM service if they are missing
        or do not meet quality standards.
        """
        llm_service: LLMService = self.get_service("llm")
        needs_long, needs_short = llm_service.needs_description_generation(event_data)

        if not needs_long and not needs_short:
            return event_data

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Enhancing descriptions with LLM",
            0.85,
        )
        try:
            return await llm_service.generate_descriptions(
                event_data, force_rebuild=False
            )
        except Exception:
            logger.exception(AgentMessages.DESCRIPTION_GENERATION_FAILED)
            return event_data
