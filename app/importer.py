"""Main event import module with shared services."""

import asyncio
import logging
from typing import List, Optional, Dict
from datetime import datetime

from app.config import Config
from app.schemas import (
    ImportRequest,
    ImportResult,
    ImportStatus,
    ImportProgress,
)
from app.agent import Agent
from app.agents import (
    ResidentAdvisorAgent,
    TicketmasterAgent,
    WebAgent,
    ImageAgent,
)
from app.progress import ProgressTracker
from app.errors import UnsupportedURLError, handle_errors_async
from app.http import get_http_service
from app.services.claude import ClaudeService
from app.services.image import ImageService
from app.services.zyte import ZyteService


logger = logging.getLogger(__name__)


class EventImporter:
    """Coordinates event imports across different agents."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize the importer."""
        self.config = config or Config.from_env()
        self.progress_tracker = ProgressTracker()
        self.http = get_http_service()

        # Create shared services once
        self._services = self._create_shared_services()

        # Initialize agents with shared services
        self.agents: List[Agent] = self._create_agents()

    def _create_shared_services(self) -> Dict:
        """Create services that will be shared across agents."""
        return {
            "http": self.http,
            "claude": ClaudeService(self.config),
            "image": ImageService(self.config, self.http),
            "zyte": ZyteService(self.config, self.http),
        }

    def _create_agents(self) -> List[Agent]:
        """Create all available agents with shared services."""
        agents = []

        # Common callback
        progress_callback = self.progress_tracker.send_progress

        # Always available agents
        agents.extend(
            [
                ResidentAdvisorAgent(
                    self.config, progress_callback, services=self._services
                ),
                WebAgent(self.config, progress_callback, services=self._services),
                ImageAgent(self.config, progress_callback, services=self._services),
            ]
        )

        # Conditionally available
        if self.config.api.ticketmaster_key:
            agents.append(
                TicketmasterAgent(
                    self.config, progress_callback, services=self._services
                )
            )

        return agents

    @handle_errors_async(reraise=True)
    async def import_event(self, request: ImportRequest) -> ImportResult:
        """
        Import an event from a URL.

        Args:
            request: Import request with URL and options

        Returns:
            Import result with event data or error
        """
        start_time = datetime.utcnow()
        url = str(request.url)

        # Send initial progress
        await self.progress_tracker.send_progress(
            ImportProgress(
                request_id=request.request_id,
                status=ImportStatus.RUNNING,
                message="Starting import",
                progress=0.0,
            )
        )

        try:
            # Find capable agent
            agent = await self._determine_agent(url, request.force_method)
            if not agent:
                raise UnsupportedURLError(url)

            logger.info(f"Using {agent.name} for {url}")

            # Run import with timeout
            event_data = await asyncio.wait_for(
                agent.import_event(url, request.request_id), timeout=request.timeout
            )

            # Create result
            if event_data:
                return ImportResult(
                    request_id=request.request_id,
                    status=ImportStatus.SUCCESS,
                    url=request.url,
                    method_used=agent.import_method,
                    event_data=event_data,
                    import_time=(datetime.utcnow() - start_time).total_seconds(),
                )
            else:
                return ImportResult(
                    request_id=request.request_id,
                    status=ImportStatus.FAILED,
                    url=request.url,
                    method_used=agent.import_method,
                    error="No event data extracted",
                    import_time=(datetime.utcnow() - start_time).total_seconds(),
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
                )
            )
            return ImportResult(
                request_id=request.request_id,
                status=ImportStatus.FAILED,
                url=request.url,
                error=error,
                import_time=(datetime.utcnow() - start_time).total_seconds(),
            )

        except Exception as e:
            error = str(e)
            logger.error(f"Import failed: {error}")
            await self.progress_tracker.send_progress(
                ImportProgress(
                    request_id=request.request_id,
                    status=ImportStatus.FAILED,
                    message=f"Import failed: {error}",
                    progress=1.0,
                    error=error,
                )
            )
            return ImportResult(
                request_id=request.request_id,
                status=ImportStatus.FAILED,
                url=request.url,
                error=error,
                import_time=(datetime.utcnow() - start_time).total_seconds(),
            )

    async def _determine_agent(
        self, url: str, force_method: Optional[str] = None
    ) -> Optional[Agent]:
        """Determine which agent should handle the URL."""
        # If method is forced, try to find matching agent
        if force_method:
            for agent in self.agents:
                if agent.import_method == force_method:
                    return agent

        # Check for known API sources first
        for agent in self.agents:
            if isinstance(agent, (ResidentAdvisorAgent, TicketmasterAgent)):
                if agent.can_handle(url):
                    return agent

        # For unknown URLs, fetch and check what it is
        try:
            # Try HEAD request first (faster)
            response = await self.http.head(url, timeout=10)
            content_type = response.headers.get("content-type", "").lower()

            # If HEAD doesn't give us content-type, try GET with small range
            if not content_type:
                response = await self.http.get(
                    url, headers={"Range": "bytes=0-1024"}, timeout=10
                )
                content_type = response.headers.get("content-type", "").lower()

        except Exception as e:
            logger.debug(f"Could not determine content type for {url}: {e}")
            # Default to web agent if we can't determine
            content_type = "text/html"

        # Route based on content type
        if content_type.startswith("image/"):
            for agent in self.agents:
                if isinstance(agent, ImageAgent):
                    return agent

        # Default to web agent for HTML or unknown
        for agent in self.agents:
            if isinstance(agent, WebAgent):
                return agent

        return None

    def add_progress_listener(self, request_id: str, callback) -> None:
        """Add a progress listener for a request."""
        self.progress_tracker.add_listener(request_id, callback)

    def get_progress_history(self, request_id: str) -> List[ImportProgress]:
        """Get progress history for a request."""
        return self.progress_tracker.get_history(request_id)
