"""Importer for events."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.agents import (
    DiceAgent,
    ImageAgent,
    ResidentAdvisorAgent,
    TicketmasterAgent,
    WebAgent,
)
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
from app.shared.database import cache_event, get_cached_event
from app.shared.http import get_http_service

logger = logging.getLogger(__name__)





class EventImporter:
    """Coordinates event imports across different agents."""

    def __init__(self: "EventImporter", config: Config | None = None) -> None:
        """Initialize the importer."""
        self.config = config or Config.from_env()
        self.progress_tracker = ProgressTracker()
        self.http = get_http_service()

        # Create shared services once
        self._services = self._create_shared_services()

        # Initialize agents with shared services
        self.agents: list[Agent] = self._create_agents()

    def _create_shared_services(self: "EventImporter") -> dict[str, Any]:
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

    @handle_errors_async(reraise=True)
    async def import_event(
        self: "EventImporter", request: ImportRequest,
    ) -> ImportResult:
        """Import an event from a URL.

        Args:
            request: Import request with URL and options

        Returns:
            Import result with event data or error

        """
        start_time = datetime.now(timezone.utc)
        url = str(request.url)

        # Initialize agent to avoid UnboundLocalError in exception handling
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

            # Check cache first (ONLY if not ignoring cache)
            if not request.ignore_cache:
                cached_data = get_cached_event(str(url))
                if cached_data:
                    logger.info(f"Found cached event for {url}")

                    try:
                        # Convert cached data to EventData
                        event_data = EventData(**cached_data)
                    except ValidationError as e:
                        # If cached data fails validation (e.g., description too long), fix it
                        logger.info(
                            f"Cached data failed validation: {e}. Attempting to fix descriptions.",
                        )

                        # Create a temporary EventData object without validation to fix descriptions
                        temp_event_data = EventData.model_construct(**cached_data)

                        # Use LLM service to regenerate descriptions if they're too long
                        if (
                            temp_event_data.short_description
                            and len(temp_event_data.short_description) > 100
                        ) or (
                            temp_event_data.long_description
                            and len(temp_event_data.long_description) > 500
                        ):
                            logger.info("Regenerating descriptions for cached data")
                            fixed_event_data = await self._services[
                                "llm"
                            ].generate_descriptions(temp_event_data)

                            # Try again with fixed data
                            event_data = EventData(**fixed_event_data.model_dump())

                            # Update cache with fixed data
                            cache_event(str(url), event_data.model_dump(mode="json"))
                            logger.info("Updated cache with fixed descriptions")
                        else:
                            # Re-raise if it's not a description length issue
                            raise e

                    return ImportResult(
                        request_id=request.request_id,
                        status=ImportStatus.SUCCESS,
                        url=request.url,
                        method_used=ImportMethod.CACHE,
                        event_data=event_data,
                        import_time=(
                            datetime.now(timezone.utc) - start_time
                        ).total_seconds(),
                    )
            else:
                logger.info(f"Ignoring cache for {url} due to ignore_cache=True")

            # Find capable agent
            agent = await self._determine_agent(url, request.force_method)
            if not agent:
                raise UnsupportedURLError(url)

            logger.info(f"Using {agent.name} for {url}")

            # Run import with timeout
            event_data = await asyncio.wait_for(
                agent.import_event(url, request.request_id), timeout=request.timeout,
            )

            # --- Fallback to WebAgent if TicketmasterAgent fails ---
            if (
                not event_data
                and agent.name == "Ticketmaster"
                and self._get_agent_by_name("WebScraper") is not None
            ):
                logger.info(
                    f"TicketmasterAgent failed, falling back to WebAgent for {url}",
                )
                web_agent = self._get_agent_by_name("WebScraper")
                event_data = await asyncio.wait_for(
                    web_agent.import_event(url, request.request_id),
                    timeout=request.timeout,
                )
                if event_data:
                    logger.info(
                        f"WebAgent succeeded for {url} after TicketmasterAgent failure",
                    )

            if event_data and not event_data.genres:
                await self.progress_tracker.send_progress(
                    ImportProgress(
                        request_id=request.request_id,
                        status=ImportStatus.RUNNING,
                        message="Searching for artist genres",
                        progress=0.95,
                    ),
                )

                try:
                    event_data = await self._services["genre"].enhance_genres(
                        event_data,
                    )
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"{ServiceMessages.GENRE_ENHANCEMENT_FAILED}: {e}")
                    # Continue without genres rather than failing

            # Create result
            if event_data:
                # Cache the successful result (always cache new imports)
                cache_event(str(url), event_data.model_dump(mode="json"))

                await self.progress_tracker.send_progress(
                    ImportProgress(
                        request_id=request.request_id,
                        status=ImportStatus.SUCCESS,
                        message="Import completed successfully",
                        progress=1.0,
                        data=event_data,
                    ),
                )

                return ImportResult(
                    request_id=request.request_id,
                    status=ImportStatus.SUCCESS,
                    url=request.url,
                    method_used=agent.import_method,
                    event_data=event_data,
                    import_time=(
                        datetime.now(timezone.utc) - start_time
                    ).total_seconds(),
                )
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
                import_time=(
                    datetime.now(timezone.utc) - start_time
                ).total_seconds(),
            )

        except asyncio.TimeoutError:
            error = f"Import timed out after {request.timeout}s"
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
                import_time=(datetime.now(timezone.utc) - start_time).total_seconds(),
            )

        except (ValueError, TypeError, KeyError) as e:
            error = str(e)
            logger.exception(CommonMessages.IMPORT_FAILED)
            await self.progress_tracker.send_progress(
                ImportProgress(
                    request_id=request.request_id,
                    status=ImportStatus.FAILED,
                    message=f"Import failed: {error}",
                    progress=1.0,
                    error=error,
                ),
            )
            return ImportResult(
                request_id=request.request_id,
                status=ImportStatus.FAILED,
                url=request.url,
                method_used=getattr(agent, "import_method", None),
                error=error,
                import_time=(datetime.now(timezone.utc) - start_time).total_seconds(),
            )

    def _create_agents(self: "EventImporter") -> list[Agent]:
        """Create all available agents with shared services."""
        agents = []

        # Common callback
        progress_callback = self.progress_tracker.send_progress

        # Always available agents
        agents.extend(
            [
                ResidentAdvisorAgent(
                    self.config, progress_callback, services=self._services,
                ),
                DiceAgent(  # Add this block
                    self.config, progress_callback, services=self._services,
                ),
                WebAgent(self.config, progress_callback, services=self._services),
                ImageAgent(self.config, progress_callback, services=self._services),
            ],
        )

        # Conditionally available - check if API key is configured
        if self.config.api.ticketmaster_key:
            agents.append(
                TicketmasterAgent(
                    self.config, progress_callback, services=self._services,
                ),
            )

        return agents

    async def _determine_agent(
        self: "EventImporter", url: str, force_method: str | None = None,
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
        from app.shared.url_analyzer import URLAnalyzer

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

    def _get_agent_by_name(self: "EventImporter", name: str) -> Agent | None:
        """Get agent by name."""
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None

    def add_progress_listener(
        self: "EventImporter",
        request_id: str,
        callback: Callable[[ImportProgress], None],
    ) -> None:
        """Add a progress listener for a specific request."""
        self.progress_tracker.add_listener(request_id, callback)

    def remove_progress_listener(
        self: "EventImporter",
        request_id: str,
        callback: Callable[[ImportProgress], None],
    ) -> None:
        """Remove a progress listener for a specific request."""
        self.progress_tracker.remove_listener(request_id, callback)

    def get_progress_history(
        self: "EventImporter", request_id: str,
    ) -> list[ImportProgress]:
        """Get the progress history for a request."""
        return self.progress_tracker.get_history(request_id)

    async def extract_event_data(
        self: "EventImporter",
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
                prompt=prompt, image_b64=None, mime_type=None,
            )
        except (ValueError, TypeError, KeyError):
            logger.exception(AgentMessages.EVENT_DATA_EXTRACTION_FAILED)
            return None

    async def enhance_genres(self: "EventImporter", event_data: EventData) -> EventData:
        try:
            return await self._services["genre"].enhance_genres(event_data)
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"{ServiceMessages.GENRE_ENHANCEMENT_FAILED}: {e}")
            return event_data
