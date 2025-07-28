"""Importer for events."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from app.agents.dice_agent import DiceAgent
from app.agents.image_agent import ImageAgent
from app.agents.ra_agent import ResidentAdvisorAgent
from app.agents.ticketmaster_agent import TicketmasterAgent
from app.agents.web_agent import WebAgent
from app.config import Config
from app.core.progress import ProgressTracker
from app.error_messages import AgentMessages, CommonMessages, ServiceMessages
from app.errors import UnsupportedURLError, handle_errors_async
from app.schemas import (
    EventData,
    ImportMethod,
    ImportProgress,
    ImportRequest,
    ImportResult,
    ImportStatus,
)
from app.services.genre import GenreService
from app.services.image import ImageService
from app.services.llm import LLMService
from app.services.zyte import ZyteService
from app.shared.agent import Agent
from app.shared.database.utils import cache_event, get_cached_event
from app.shared.http import get_http_service
from app.shared.url_analyzer import URLAnalyzer

logger = logging.getLogger(__name__)


class EventImporter:
    """Coordinates event imports across different agents."""

    def __init__(self: EventImporter, config: Config | None = None) -> None:
        """Initialize the importer."""
        self.config = config or Config.from_env()
        self.progress_tracker = ProgressTracker()
        self.http = get_http_service()

        # Create shared services once
        self._services = self._create_shared_services()

        # Initialize agents with shared services
        self.agents: list[Agent] = self._create_agents()

    def _create_shared_services(self: EventImporter) -> dict[str, Any]:
        """Create services that will be shared across agents."""
        llm_service = LLMService(self.config)
        genre_service = GenreService(self.config, self.http, llm_service)

        return {
            "http": self.http,
            "llm": llm_service,
            "image": ImageService(self.config, self.http),
            "zyte": ZyteService(self.config, self.http),
            "genre": genre_service,
        }

    async def _handle_cache(
        self: EventImporter,
        url: str,
        start_time: datetime,
        request: ImportRequest,
    ) -> ImportResult | None:
        """Handle event import from cache."""
        if request.ignore_cache:
            logger.info(f"Ignoring cache for {url} due to ignore_cache=True")
            return None

        cached_data = get_cached_event(url)
        if not cached_data:
            return None

        logger.info(f"Found cached event for {url}")
        try:
            event_data = EventData(**cached_data)
        except ValidationError as e:
            event_data = await self._fix_cached_data(url, cached_data, e)

        return ImportResult(
            request_id=request.request_id,
            status=ImportStatus.SUCCESS,
            url=request.url,
            method_used=ImportMethod.CACHE,
            event_data=event_data,
            import_time=(datetime.now(UTC) - start_time).total_seconds(),
        )

    async def _fix_cached_data(
        self: EventImporter,
        url: str,
        cached_data: dict[str, Any],
        error: ValidationError,
    ) -> EventData:
        """Attempt to fix invalid cached data."""
        logger.info(f"Cached data failed validation: {error}. Attempting to fix.")
        temp_event_data = EventData.model_construct(**cached_data)

        if not (
            (
                temp_event_data.short_description
                and len(temp_event_data.short_description) > 100
            )
            or (
                temp_event_data.long_description
                and len(temp_event_data.long_description) > 500
            )
        ):
            raise error

        logger.info("Regenerating descriptions for cached data")
        fixed_event_data = await self._services["llm"].generate_descriptions(
            temp_event_data
        )
        event_data = EventData(**fixed_event_data.model_dump())
        cache_event(url, event_data.model_dump(mode="json"))
        logger.info("Updated cache with fixed descriptions")
        return event_data

    async def _run_agent_import(
        self: EventImporter,
        request: ImportRequest,
    ) -> tuple[Agent, EventData | None]:
        """Determine and run the correct agent for the URL."""
        agent = await self._determine_agent(str(request.url), request.force_method)
        if not agent:
            raise UnsupportedURLError(str(request.url))

        logger.info(f"Using {agent.name} for {request.url}")
        event_data = await asyncio.wait_for(
            agent.import_event(str(request.url), request.request_id),
            timeout=request.timeout,
        )

        # --- Fallback to WebAgent if TicketmasterAgent fails ---
        if (
            not event_data
            and agent.name == "Ticketmaster"
            and (web_agent := self._get_agent_by_name("WebScraper"))
        ):
            logger.info(
                f"TicketmasterAgent failed, falling back to WebAgent for {request.url}"
            )
            event_data = await asyncio.wait_for(
                web_agent.import_event(str(request.url), request.request_id),
                timeout=request.timeout,
            )
            if event_data:
                logger.info(f"WebAgent succeeded for {request.url} after failure")
        return agent, event_data

    async def _enhance_event_data(
        self: EventImporter,
        request_id: str,
        event_data: EventData,
    ) -> EventData:
        """Enhance event data, e.g., by adding genres."""
        if event_data.genres:
            return event_data

        await self.progress_tracker.send_progress(
            ImportProgress(
                request_id=request_id,
                status=ImportStatus.RUNNING,
                message="Searching for artist genres",
                progress=0.95,
            ),
        )
        try:
            return await self._services["genre"].enhance_genres(event_data)
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"{ServiceMessages.GENRE_ENHANCEMENT_FAILED}: {e}")
            return event_data  # Continue without genres

    async def _finalize_import(
        self: EventImporter,
        request: ImportRequest,
        event_data: EventData | None,
        agent: Agent,
        start_time: datetime,
    ) -> ImportResult:
        """Finalize the import process by enhancing, caching, and creating a result."""
        if not event_data:
            error = "Agent returned no data"
            await self.progress_tracker.send_progress(
                ImportProgress(
                    request_id=request.request_id,
                    status=ImportStatus.FAILED,
                    message=error,
                    progress=1.0,
                    error=error,
                ),
            )
            return ImportResult(
                request_id=request.request_id,
                status=ImportStatus.FAILED,
                url=request.url,
                method_used=agent.import_method,
                error=error,
                import_time=(datetime.now(UTC) - start_time).total_seconds(),
            )

        enhanced_data = await self._enhance_event_data(request.request_id, event_data)
        cache_event(str(request.url), enhanced_data.model_dump(mode="json"))

        await self.progress_tracker.send_progress(
            ImportProgress(
                request_id=request.request_id,
                status=ImportStatus.SUCCESS,
                message="Import completed successfully",
                progress=1.0,
                data=enhanced_data,
            ),
        )
        return ImportResult(
            request_id=request.request_id,
            status=ImportStatus.SUCCESS,
            url=request.url,
            method_used=agent.import_method,
            event_data=enhanced_data,
            import_time=(datetime.now(UTC) - start_time).total_seconds(),
        )

    async def _handle_import_error(
        self: EventImporter,
        request: ImportRequest,
        error: Exception,
        start_time: datetime,
        agent: Agent | None,
        is_timeout: bool = False,
    ) -> ImportResult:
        """Handle exceptions during the import process."""
        if is_timeout:
            error_msg = f"Import timed out after {request.timeout}s"
        else:
            error_msg = str(error)
            logger.error(CommonMessages.IMPORT_FAILED)

        await self.progress_tracker.send_progress(
            ImportProgress(
                request_id=request.request_id,
                status=ImportStatus.FAILED,
                message=f"Import failed: {error_msg}",
                progress=1.0,
                error=error_msg,
            ),
        )
        return ImportResult(
            request_id=request.request_id,
            status=ImportStatus.FAILED,
            url=request.url,
            method_used=getattr(agent, "import_method", None),
            error=error_msg,
            import_time=(datetime.now(UTC) - start_time).total_seconds(),
        )

    @handle_errors_async(reraise=True)
    async def import_event(self: EventImporter, request: ImportRequest) -> ImportResult:
        """Import an event from a URL.

        Args:
            request: Import request with URL and options

        Returns:
            Import result with event data or error

        """
        start_time = datetime.now(UTC)
        agent = None
        try:
            await self.progress_tracker.send_progress(
                ImportProgress(
                    request_id=request.request_id,
                    status=ImportStatus.RUNNING,
                    message="Starting import",
                    progress=0.1,
                ),
            )

            # 1. Check cache
            if cached_result := await self._handle_cache(
                str(request.url), start_time, request
            ):
                return cached_result

            # 2. Run import via agent
            agent, event_data = await self._run_agent_import(request)

            # 3. Finalize and return result
            return await self._finalize_import(request, event_data, agent, start_time)

        except TimeoutError as e:
            return await self._handle_import_error(
                request, e, start_time, agent, is_timeout=True
            )

        except (ValueError, TypeError, KeyError) as e:
            return await self._handle_import_error(request, e, start_time, agent)

    def _create_agents(self: EventImporter) -> list[Agent]:
        """Create all available agents with shared services."""
        agents = []

        # Common callback
        progress_callback = self.progress_tracker.send_progress

        # Always available agents
        agents.extend(
            [
                ResidentAdvisorAgent(
                    self.config,
                    progress_callback,
                    services=self._services,
                ),
                DiceAgent(  # Add this block
                    self.config,
                    progress_callback,
                    services=self._services,
                ),
                WebAgent(self.config, progress_callback, services=self._services),
                ImageAgent(self.config, progress_callback, services=self._services),
            ],
        )

        # Conditionally available - check if API key is configured
        if self.config.api.ticketmaster_key:
            agents.append(
                TicketmasterAgent(
                    self.config,
                    progress_callback,
                    services=self._services,
                ),
            )

        return agents

    async def _determine_agent(
        self: EventImporter,
        url: str,
        force_method: str | None = None,
    ) -> Agent | None:
        """Determine which agent should handle the URL using content-type and URL analysis."""
        if force_method:
            # Find agent by method name mapping
            method_mapping = {
                "api": ["ResidentAdvisor", "Ticketmaster", "Dice"],
                "web": ["WebScraper"],
                "image": ["ImageAgent"],
            }

            target_agents = method_mapping.get(force_method, [])
            for agent in self.agents:
                if agent.name in target_agents:
                    return agent

            logger.warning(f"Forced method '{force_method}' not available")

        # URL pattern based routing for specialized agents first
        analyzer = URLAnalyzer()
        analysis = analyzer.analyze(url)

        # Route to specialized agents based on URL analysis
        if analysis.get("type") == "resident_advisor" and "event_id" in analysis:
            return self._get_agent_by_name("ResidentAdvisor")
        if analysis.get("type") == "ticketmaster":
            agent = self._get_agent_by_name("Ticketmaster")
            # Only return if API key is configured
            return agent if self.config.api.ticketmaster_key else None
        if analysis.get("type") == "dice":
            return self._get_agent_by_name("Dice")

        # Check for image URLs by extension or keywords before falling back to web scraping
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        url_lower = url.lower()
        if (
            any(url_lower.endswith(ext) for ext in image_extensions)
            or "imgproxy" in url_lower
        ):
            return self._get_agent_by_name("ImageAgent")

        # If it's not a special API or image URL, default to WebAgent.
        # It's better to let Zyte handle it than to fail on a HEAD request.
        logger.info(f"Defaulting to WebScraper for URL: {url}")
        return self._get_agent_by_name("WebScraper")

    def _get_agent_by_name(self: EventImporter, name: str) -> Agent | None:
        """Get agent by name."""
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None

    def add_progress_listener(
        self: EventImporter,
        request_id: str,
        callback: Callable[[ImportProgress], None],
    ) -> None:
        """Add a progress listener for a specific request."""
        self.progress_tracker.add_listener(request_id, callback)

    def remove_progress_listener(
        self: EventImporter,
        request_id: str,
        callback: Callable[[ImportProgress], None],
    ) -> None:
        """Remove a progress listener for a specific request."""
        self.progress_tracker.remove_listener(request_id, callback)

    def get_progress_history(
        self: EventImporter,
        request_id: str,
    ) -> list[ImportProgress]:
        """Get the progress history for a request."""
        return self.progress_tracker.get_history(request_id)

    async def extract_event_data(
        self: EventImporter,
        prompt: str,
        image_b64: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Extract event data from prompt or image."""
        try:
            if image_b64 and mime_type:
                return await self._services["llm"].extract_event_data(
                    prompt="",  # Empty prompt for image extraction
                    image_b64=image_b64,
                    mime_type=mime_type,
                )
            return await self._services["llm"].extract_event_data(
                prompt=prompt,
                image_b64=None,
                mime_type=None,
            )
        except (ValueError, TypeError, KeyError):
            logger.exception(AgentMessages.EVENT_DATA_EXTRACTION_FAILED)
            return None

    async def enhance_genres(self: EventImporter, event_data: EventData) -> EventData:
        try:
            return await self._services["genre"].enhance_genres(event_data)
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"{ServiceMessages.GENRE_ENHANCEMENT_FAILED}: {e}")
            return event_data

    async def rebuild_descriptions(
        self: EventImporter, event_id: int
    ) -> EventData | None:
        """Rebuild descriptions for a cached event."""
        logger.info(f"Rebuilding descriptions for event ID: {event_id}")
        cached_data = get_cached_event(event_id=event_id)
        if not cached_data:
            logger.error(f"No cached event found for ID: {event_id}")
            return None

        try:
            event_data = EventData(**cached_data)

            # Use the LLM service to force a rebuild
            llm_service = self._services["llm"]
            updated_event_data = await llm_service.generate_descriptions(
                event_data, force_rebuild=True
            )

            # Cache the updated event data
            cache_event(
                updated_event_data.source_url,
                updated_event_data.model_dump(mode="json"),
            )
            logger.info(f"Successfully rebuilt descriptions for event ID: {event_id}")
            return updated_event_data

        except (ValidationError, Exception) as e:
            logger.exception(
                f"Failed to rebuild descriptions for event {event_id}: {e}"
            )
            return None
