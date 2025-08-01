"""The core event import orchestrator."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import HttpUrl

from app.core.errors import AgentNotFoundError, UnsupportedURLError
from app.core.progress import ProgressTracker
from app.core.schemas import (
    DescriptionResult,
    EventData,
    GenreResult,
    ImageResult,
    ImportMethod,
    ImportProgress,
    ImportResult,
    ImportStatus,
    ServiceFailure,
)
from app.extraction_agents.base import BaseExtractionAgent as Agent
from app.extraction_agents.providers.dice import Dice
from app.extraction_agents.providers.image import Image
from app.extraction_agents.providers.ra import ResidentAdvisor
from app.extraction_agents.providers.ticketmaster import Ticketmaster
from app.extraction_agents.providers.web import Web
from app.services.genre import GenreService
from app.services.image import ImageService
from app.services.integration_discovery import get_available_integrations
from app.services.llm.service import LLMService
from app.services.security_detector import SecurityPageDetector
from app.shared.database.utils import get_event, save_event
from app.shared.http import HTTPService
from app.shared.url_analyzer import URLAnalyzer
from config import Config

logger = logging.getLogger(__name__)


class EventImporter:
    """Orchestrates the event import process."""

    def __init__(self, config: Config) -> None:
        """Initialize the event importer."""
        self.config = config
        self.url_analyzer = URLAnalyzer()
        self.progress_tracker = ProgressTracker()

        # Initialize shared services
        http_service = HTTPService(config)
        llm_service = LLMService(config)
        self.services = {
            "http": http_service,
            "image": ImageService(config, http_service=http_service),
            "llm": llm_service,
            "genre": GenreService(
                config, http_service=http_service, llm_service=llm_service
            ),
            "security_detector": SecurityPageDetector(),
        }

        # Dynamically load integrations from the integrations directory
        self.integrations = get_available_integrations()

    def get_service(self, service_name: str) -> Any:  # noqa: ANN401
        """Get a shared service instance."""
        return self.services.get(service_name)

    async def close(self) -> None:
        """Close any resources held by the importer."""
        # Close HTTP service
        http_service = self.services.get("http")
        if http_service and hasattr(http_service, "close"):
            await http_service.close()

    async def _enhance_genres(
        self, event_data: EventData, request_id: str
    ) -> GenreResult:
        """Enhance event genres if needed."""
        # Check if genre enhancement is required (no genres or only broad categories)
        if not event_data.genres or len(event_data.genres) <= 2:
            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                "Enhancing genres",
                0.9,
            )
            try:
                genre_service = self.get_service("genre")
                enhanced_genres = await genre_service.enhance_genres(event_data)
                if enhanced_genres and enhanced_genres != event_data.genres:
                    return GenreResult(
                        original_genres=event_data.genres,
                        enhanced_genres=enhanced_genres,
                    )
            except Exception as e:
                logger.exception("Genre enhancement failed")
                return GenreResult(
                    original_genres=event_data.genres,
                    enhanced_genres=event_data.genres,
                    service_failure=ServiceFailure(
                        service="genre", error=str(e), detail="Failed to enhance genres"
                    ),
                )
        return GenreResult(
            original_genres=event_data.genres, enhanced_genres=event_data.genres
        )

    async def _enhance_image(
        self, event_data: EventData, request_id: str
    ) -> ImageResult:
        """Enhance event image if needed."""
        if not event_data.images or not event_data.images.get("full"):
            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                "Searching for a better image",
                0.95,
            )
            try:
                image_service = self.get_service("image")
                # enhance_event_image returns ImageResult directly
                return await image_service.enhance_event_image(event_data)
            except Exception as e:
                logger.exception("Image enhancement failed")
                return ImageResult(
                    original_image_url=(
                        event_data.images.get("full") if event_data.images else None
                    ),
                    enhanced_image_url=None,
                    service_failure=ServiceFailure(
                        service="image", error=str(e), detail="Failed to enhance image"
                    ),
                )

        return ImageResult(
            original_image_url=(
                event_data.images.get("full") if event_data.images else None
            ),
            enhanced_image_url=(
                event_data.images.get("full") if event_data.images else None
            ),
        )

    async def process_event(
        self,
        event_data: EventData,
        request_id: str,
        enhance_genres: bool = True,
        enhance_image: bool = True,
    ) -> tuple[EventData, list[ServiceFailure]]:
        """Post-process an event after import (genre and image enhancement)."""
        # Run enhancements concurrently
        tasks = []
        if enhance_genres:
            tasks.append(self._enhance_genres(event_data, request_id))
        if enhance_image:
            tasks.append(self._enhance_image(event_data, request_id))

        results = await asyncio.gather(*tasks)

        # Process results and collect failures
        service_failures = []
        for result in results:
            if isinstance(result, GenreResult):
                event_data.genres = result.enhanced_genres
                if result.service_failure:
                    service_failures.append(result.service_failure)
            elif isinstance(result, ImageResult):
                if result.enhanced_image_url:
                    if not event_data.images:
                        event_data.images = {}
                    event_data.images["full"] = result.enhanced_image_url
                    event_data.images["thumbnail"] = result.enhanced_image_url
                if result.service_failure:
                    service_failures.append(result.service_failure)

        return event_data, service_failures

    async def import_event(
        self,
        url: HttpUrl,
        enhance_genres: bool = True,
        enhance_image: bool = True,
        progress_callback: Callable[[ImportProgress], Awaitable[None]] | None = None,
    ) -> ImportResult:
        """Import an event from a URL.

        This is the main entry point for the import process.
        """
        # Ensure URL is a string for internal use
        url_str = str(url)
        request_id = str(uuid.uuid4())
        start_time = asyncio.get_event_loop().time()
        service_failures: list[ServiceFailure] = []
        self.progress_tracker.add_listener(request_id, progress_callback)

        await self.send_progress(
            request_id,
            ImportStatus.PENDING,
            "Starting import...",
            0,
        )

        try:
            # 1. Select agent
            agent = self._select_agent(url_str, request_id)

            # 2. Import event
            event_data = await agent.import_event(url_str, request_id)
            if not event_data:
                raise Exception("The agent failed to import the event.")

            # 3. Post-processing (enhancements)
            event_data, enhancement_failures = await self.process_event(
                event_data, request_id, enhance_genres, enhance_image
            )
            service_failures.extend(enhancement_failures)

            # 4. Save to database
            save_event(str(event_data.source_url), event_data.model_dump(mode="json"))

            await self.send_progress(
                request_id,
                ImportStatus.SUCCESS,
                "Import complete",
                1,
                data=event_data,
            )

            # Calculate import time
            import_time = asyncio.get_event_loop().time() - start_time

            # Build ImportResult
            return ImportResult(
                request_id=request_id,
                status=ImportStatus.SUCCESS,
                url=url,
                method_used=agent.import_method,
                event_data=event_data,
                import_time=import_time,
                service_failures=service_failures,
            )
        except Exception as e:
            logger.exception(f"Import failed for URL: {url}")
            await self.send_progress(
                request_id,
                ImportStatus.FAILED,
                f"Import failed: {e!s}",
                1,
                error=str(e),
            )
            raise
        finally:
            self.progress_tracker.remove_listener(request_id, progress_callback)

    def _get_agent_for_source(self, source: str) -> Agent:
        """Get agent for a specific source."""
        agents: dict[str, type[Agent]] = {
            "dice.fm": Dice,
            "ra.co": ResidentAdvisor,
            "ticketmaster.com": Ticketmaster,
        }
        if agent_class := agents.get(source):
            return agent_class(
                self.config, self.progress_tracker.send_progress, self.services
            )
        raise UnsupportedURLError(f"No agent available for source: {source}")

    def _get_agent_for_method(self, import_method: ImportMethod) -> Agent:
        """Get agent for a specific import method."""
        if import_method == ImportMethod.IMAGE:
            return Image(
                self.config, self.progress_tracker.send_progress, self.services
            )
        if import_method == ImportMethod.WEB:
            return Web(self.config, self.progress_tracker.send_progress, self.services)
        raise AgentNotFoundError(
            f"No agent found for import method: {import_method.value}"
        )

    def _select_agent(self, url: str, request_id: str) -> Agent:  # noqa: ARG002
        """Select the appropriate agent for the given URL."""
        analysis = self.url_analyzer.analyze(url)
        url_type = analysis.get("type")
        import_method = analysis.get("method")

        logger.info(
            f"URL analysis result: type={url_type}, method={import_method}",
            extra={"analysis": analysis},
        )

        agent = None
        if url_type and url_type != "unknown":
            try:
                # Map URLType to domain for agent selection
                source_mapping = {
                    "resident_advisor": "ra.co",
                    "ticketmaster": "ticketmaster.com",
                    "dice": "dice.fm",
                }
                source = source_mapping.get(url_type, url_type)
                agent = self._get_agent_for_source(source)
                logger.info(
                    f"Selected agent '{agent.name}' for source '{source}'",
                    extra={"agent": agent.name, "source": source},
                )
            except UnsupportedURLError:
                logger.warning(
                    f"No specific agent for source '{source}', falling back to web agent."
                )
                agent = self._get_agent_for_method(ImportMethod.WEB)
        elif import_method:
            agent = self._get_agent_for_method(import_method)
            logger.info(
                f"Selected agent '{agent.name}' for import method '{import_method.value}'"
            )

        if not agent:
            raise UnsupportedURLError("Could not determine an agent for the given URL.")

        return agent

    async def send_progress(
        self,
        request_id: str,
        status: ImportStatus,
        message: str,
        percentage: float,
        data: EventData | None = None,
        error: str | None = None,
    ) -> None:
        """Send progress update."""
        progress = ImportProgress(
            request_id=request_id,
            status=status,
            message=message,
            progress=percentage,
            data=data,
            error=error,
        )
        await self.progress_tracker.send_progress(progress)

    async def rebuild_description(
        self,
        event_id: int,
        description_type: str,
        supplementary_context: str | None = None,
    ) -> DescriptionResult | None:
        """Rebuild the description for a cached event."""
        event_data_dict = get_event(event_id=event_id)
        if not event_data_dict:
            return None

        event_data = EventData(**event_data_dict)
        llm_service: LLMService = self.get_service("llm")

        # Determine which description to rebuild
        needs_long = description_type == "long"
        needs_short = description_type == "short"

        # Clear the specific description type being rebuilt
        if needs_short:
            event_data.short_description = None
        elif needs_long:
            event_data.long_description = None

        # Get the provider and generate descriptions
        provider = llm_service.primary_provider or llm_service.fallback_provider
        if not provider:
            raise ValueError("No LLM provider available")

        updated_event = await provider.generate_descriptions(
            event_data,
            needs_long=needs_long,
            needs_short=needs_short,
            supplementary_context=supplementary_context,
        )

        # Return just the descriptions
        return DescriptionResult(
            short_description=updated_event.short_description,
            long_description=updated_event.long_description,
        )

    async def rebuild_genres(
        self,
        event_id: int,
        supplementary_context: str | None = None,
    ) -> tuple[GenreResult | None, list[ServiceFailure]]:
        """Rebuild the genres for a cached event."""
        event_data_dict = get_event(event_id=event_id)
        if not event_data_dict:
            return None, []

        event_data = EventData(**event_data_dict)
        genre_service: GenreService = self.get_service("genre")
        failures = []
        try:
            enhanced_genres = await genre_service.enhance_genres(
                event_data, supplementary_context=supplementary_context
            )
            # Return just the genres
            return GenreResult(
                original_genres=event_data.genres, enhanced_genres=enhanced_genres
            ), failures
        except Exception as e:
            failures.append(ServiceFailure(service="genre", error=str(e)))
            return GenreResult(
                original_genres=event_data.genres, enhanced_genres=event_data.genres
            ), failures

    async def rebuild_image(
        self,
        event_id: int,
        supplementary_context: str | None = None,
    ) -> tuple[ImageResult | None, list[ServiceFailure]]:
        """Rebuild the image for a cached event."""
        event_data_dict = get_event(event_id=event_id)
        if not event_data_dict:
            return None, []

        event_data = EventData(**event_data_dict)
        image_service: ImageService = self.get_service("image")
        failures = []
        try:
            # enhance_event_image now returns ImageResult directly
            image_result = await image_service.enhance_event_image(
                event_data,
                supplementary_context=supplementary_context,
                force_search=True,  # Force search since this is a rebuild
            )
            return image_result, failures
        except Exception as e:
            failures.append(ServiceFailure(service="image", error=str(e)))
            return ImageResult(), failures

    async def update_event(
        self,
        event_id: int,
        updates: dict[str, Any],
    ) -> EventData | None:
        """Update a cached event with new data."""
        event_data_dict = get_event(event_id=event_id)
        if not event_data_dict:
            return None

        # Merge updates with event data
        merged_data = {**event_data_dict, **updates}
        # Create new EventData to ensure validation
        updated_event = EventData(**merged_data)
        save_event(str(updated_event.source_url), updated_event.model_dump(mode="json"))
        return updated_event
