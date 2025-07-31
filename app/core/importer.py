"""Importer for events."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from app.agents.dice_agent import DiceAgent
from app.agents.image_agent import ImageAgent
from app.agents.ra_agent import ResidentAdvisorAgent
from app.agents.ticketmaster_agent import TicketmasterAgent
from app.agents.web_agent import WebAgent
from app.config import Config, get_config
from app.core.progress import ProgressTracker
from app.error_messages import AgentMessages, CommonMessages, ServiceMessages
from app.errors import APIError, UnsupportedURLError, handle_errors_async
from app.schemas import (
    EventData,
    EventTime,
    ImportMethod,
    ImportProgress,
    ImportRequest,
    ImportResult,
    ImportStatus,
    ServiceFailure,
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


class ServiceFailureCollector:
    """Collects service failures during import."""

    def __init__(self):
        self.failures: list[ServiceFailure] = []

    def add_failure(self, service: str, error: Exception) -> None:
        """Add a service failure."""
        error_msg = str(error)
        detail = None

        # Extract more detail for specific error types
        if hasattr(error, "__class__"):
            detail = f"{error.__class__.__name__}: {error_msg}"

        self.failures.append(
            ServiceFailure(
                service=service,
                error=error_msg[:200],  # Truncate long errors
                detail=detail,
            )
        )


class EventImporter:
    """Coordinates event imports across different agents."""

    def __init__(self: EventImporter, config: Config | None = None) -> None:
        """Initialize the importer."""
        self.config = config or get_config()
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
            and agent.name.lower() == "ticketmaster"
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
        failure_collector: ServiceFailureCollector | None = None,
    ) -> EventData:
        """Enhance event data with genres and images."""
        # Image enhancement
        if self._services["image"].google_enabled:
            await self.progress_tracker.send_progress(
                ImportProgress(
                    request_id=request_id,
                    status=ImportStatus.RUNNING,
                    message="Enhancing images",
                    progress=0.85,
                ),
            )
            try:
                event_data = await self._services["image"].enhance_event_image(
                    event_data, failure_collector=failure_collector
                )
                await self.progress_tracker.send_progress(
                    ImportProgress(
                        request_id=request_id,
                        status=ImportStatus.RUNNING,
                        message="Image enhancement complete",
                        progress=0.90,
                    ),
                )
            except Exception as e:
                logger.warning(f"Image enhancement failed: {e}")
                if failure_collector:
                    failure_collector.add_failure("GoogleImageSearch", e)

        # Genre enhancement
        if not event_data.genres:
            await self.progress_tracker.send_progress(
                ImportProgress(
                    request_id=request_id,
                    status=ImportStatus.RUNNING,
                    message="Searching for artist genres",
                    progress=0.95,
                ),
            )
            try:
                event_data = await self._services["genre"].enhance_genres(event_data)
            except Exception as e:
                logger.warning(f"{ServiceMessages.GENRE_ENHANCEMENT_FAILED}: {e}")
                if failure_collector:
                    if isinstance(e, APIError):
                        failure_collector.add_failure(e.service, e)
                    else:
                        failure_collector.add_failure("GenreService", e)

        return event_data

    async def _finalize_import(
        self: EventImporter,
        request: ImportRequest,
        event_data: EventData | None,
        agent: Agent,
        start_time: datetime,
        failure_collector: ServiceFailureCollector | None = None,
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

        enhanced_data = await self._enhance_event_data(
            request.request_id, event_data, failure_collector
        )
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
            service_failures=failure_collector.failures if failure_collector else [],
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

            # 2. Create failure collector
            failure_collector = ServiceFailureCollector()

            # 3. Run import via agent
            agent, event_data = await self._run_agent_import(request)

            # 4. Finalize and return result
            return await self._finalize_import(
                request, event_data, agent, start_time, failure_collector
            )

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
        if self.config.api.ticketmaster_api_key:
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
            target_agents_lower = [t.lower() for t in target_agents]
            for agent in self.agents:
                if agent.name.lower() in target_agents_lower:
                    return agent

            logger.warning(f"Forced method '{force_method}' not available")

        # URL pattern based routing for specialized agents first
        analyzer = URLAnalyzer()
        analysis = analyzer.analyze(url)

        # Route to specialized agents based on URL analysis
        if analysis.get("type") == "resident_advisor" and "event_id" in analysis:
            return self._get_agent_by_name("ResidentAdvisor")
        if analysis.get("type") == "ticketmaster":
            agent = self._get_agent_by_name("ticketmaster")
            # Only return if API key is configured
            return agent if self.config.api.ticketmaster_api_key else None
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
        """Get agent by name (case-insensitive)."""
        name_lower = name.lower()
        for agent in self.agents:
            if agent.name.lower() == name_lower:
                return agent
        return None

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

    async def rebuild_description(
        self: EventImporter,
        event_id: int,
        description_type: str,
        supplementary_context: str | None = None,
    ) -> EventData | None:
        """Rebuild description for a cached event (preview only - does not save).

        Args:
            event_id: The ID of the event to rebuild description for
            description_type: Which description to rebuild: 'short' or 'long'
            supplementary_context: Optional context to help generate better descriptions
        """
        logger.info(
            f"Rebuilding {description_type} description for event ID: {event_id} (preview only)"
        )
        cached_data = get_cached_event(event_id=event_id)
        if not cached_data:
            logger.error(f"No cached event found for ID: {event_id}")
            return None

        try:
            # Remove the _db_id before creating EventData
            cached_data.pop("_db_id", None)
            event_data = EventData(**cached_data)

            # Copy the event data so we don't modify the original
            updated_event_data = event_data.model_copy(deep=True)

            # Use the LLM service to generate only the requested description
            llm_service = self._services["llm"]

            if description_type == "short":
                # Generate only short description
                new_description = await llm_service.generate_short_description(
                    event_data, supplementary_context
                )
                updated_event_data.short_description = new_description
            else:  # description_type == "long"
                # Generate only long description
                new_description = await llm_service.generate_long_description(
                    event_data, supplementary_context
                )
                updated_event_data.long_description = new_description

            logger.info(
                f"Successfully rebuilt {description_type} description for event ID: {event_id} (preview only)"
            )
            return updated_event_data

        except (ValidationError, Exception) as e:
            logger.exception(
                f"Failed to rebuild descriptions for event {event_id}: {e}"
            )
            return None

    async def rebuild_genres(
        self: EventImporter,
        event_id: int,
        supplementary_context: str | None = None,
    ) -> tuple[EventData | None, list[dict]]:
        """Rebuild genres for a cached event (preview only - does not save).

        Args:
            event_id: The ID of the event to rebuild genres for
            supplementary_context: Optional context to help identify genres

        Returns:
            Tuple of (EventData, service_failures)
        """
        logger.info(f"Rebuilding genres for event ID: {event_id} (preview only)")
        cached_data = get_cached_event(event_id=event_id)
        if not cached_data:
            logger.error(f"No cached event found for ID: {event_id}")
            return None, []

        # Create failure collector
        failure_collector = ServiceFailureCollector()

        try:
            # Remove the _db_id before creating EventData
            cached_data.pop("_db_id", None)
            event_data = EventData(**cached_data)

            # Copy the event data so we don't modify the original
            updated_event_data = event_data.model_copy(deep=True)

            # Use the genre service to enhance genres
            genre_service = self._services["genre"]
            # Force re-search by clearing existing genres
            updated_event_data.genres = []

            try:
                updated_event_data = await genre_service.enhance_genres(
                    updated_event_data, supplementary_context
                )
            except ValueError as e:
                # Specific error for missing lineup
                logger.warning(f"Genre enhancement failed: {e}")
                failure_collector.add_failure("GenreService", e)
            except APIError as e:
                logger.warning(f"Genre enhancement API error: {e}")
                failure_collector.add_failure(e.service, e)
            except Exception as e:
                logger.warning(f"Genre enhancement failed: {e}")
                failure_collector.add_failure("GenreService", e)

            logger.info(
                f"Successfully rebuilt genres for event ID: {event_id} (preview only)"
            )
            return updated_event_data, failure_collector.failures

        except (ValidationError, Exception) as e:
            logger.exception(f"Failed to rebuild genres for event {event_id}: {e}")
            failure_collector.add_failure("GenreRebuild", e)
            return None, failure_collector.failures

    async def rebuild_image(
        self: EventImporter,
        event_id: int,
        supplementary_context: str | None = None,
    ) -> tuple[EventData | None, list[dict]]:
        """Rebuild image for a cached event (preview only - does not save).

        Args:
            event_id: The ID of the event to rebuild image for
            supplementary_context: Optional context to help find better images

        Returns:
            Tuple of (EventData, service_failures)
        """
        logger.info(f"Rebuilding image for event ID: {event_id} (preview only)")
        cached_data = get_cached_event(event_id=event_id)
        if not cached_data:
            logger.error(f"No cached event found for ID: {event_id}")
            return None, []

        # Create failure collector
        failure_collector = ServiceFailureCollector()

        try:
            # Remove the _db_id before creating EventData
            cached_data.pop("_db_id", None)
            event_data = EventData(**cached_data)

            # Copy the event data so we don't modify the original
            updated_event_data = event_data.model_copy(deep=True)

            # Use the image service to enhance image
            image_service = self._services["image"]

            # Create a simple progress callback

            async def progress_callback(message: str, progress: float) -> None:
                logger.info(f"Image search progress: {message} ({progress:.0%})")

            try:
                updated_event_data = await image_service.enhance_event_image(
                    updated_event_data,
                    progress_callback,
                    failure_collector,
                    force_search=True,
                    supplementary_context=supplementary_context,
                )
            except Exception as e:
                logger.warning(f"Image enhancement failed: {e}")
                if isinstance(e, APIError):
                    failure_collector.add_failure(e.service, e)
                else:
                    failure_collector.add_failure("ImageService", e)

            logger.info(
                f"Successfully rebuilt image for event ID: {event_id} (preview only)"
            )
            return updated_event_data, failure_collector.failures

        except (ValidationError, Exception) as e:
            logger.exception(f"Failed to rebuild image for event {event_id}: {e}")
            failure_collector.add_failure("ImageRebuild", e)
            return None, failure_collector.failures

    async def _prepare_updates(self, updates: dict, event_data: EventData) -> dict:
        """Validate and prepare update fields."""
        validated_updates = {}
        for field, value in updates.items():
            if not hasattr(event_data, field):
                logger.warning(f"Field '{field}' does not exist on EventData")
                continue

            if field == "time" and isinstance(value, dict):
                validated_updates[field] = EventTime(**value)
            elif field == "images" and isinstance(value, dict):
                if not all(k in ["full", "thumbnail"] for k in value):
                    logger.warning(
                        "Invalid image keys. Only 'full' and 'thumbnail' are allowed"
                    )
                    continue
                if "full" in value and "thumbnail" not in value:
                    value["thumbnail"] = value["full"]
                elif "thumbnail" in value and "full" not in value:
                    value["full"] = value["thumbnail"]
                validated_updates[field] = value
            else:
                validated_updates[field] = value
        return validated_updates

    async def update_event(self, event_id: int, updates: dict) -> EventData | None:
        """Update specific fields of a cached event.

        Args:
            event_id: The ID of the event to update
            updates: Dictionary of fields to update

        Returns:
            Updated EventData if successful, None otherwise
        """
        try:
            logger.info(
                f"Updating event ID: {event_id} with fields: {list(updates.keys())}"
            )

            event_data_dict = get_cached_event(event_id=event_id)
            if not event_data_dict:
                logger.warning(f"Event not found for ID: {event_id}")
                return None

            event_data_dict.pop("_db_id", None)
            event_data = EventData(**event_data_dict)

            validated_updates = await self._prepare_updates(updates, event_data)
            if not validated_updates:
                logger.warning("No valid updates to apply")
                return event_data

            current_data = event_data.model_dump()
            current_data.update(validated_updates)
            updated_event_data = EventData(**current_data)

            cache_event(
                str(updated_event_data.source_url),
                updated_event_data.model_dump(mode="json"),
            )
            logger.info(f"Successfully updated event ID: {event_id}")
            return updated_event_data

        except (ValidationError, Exception) as e:
            logger.exception(f"Failed to update event {event_id}: {e}")
            return None
