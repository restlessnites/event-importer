"""Main event import engine."""

import asyncio
import logging
from typing import List, Optional
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


logger = logging.getLogger(__name__)


class EventImportEngine:
    """Coordinates event imports across different agents."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize the import engine."""
        self.config = config or Config.from_env()
        self.progress_tracker = ProgressTracker()

        # Initialize agents with progress callback
        self.agents: List[Agent] = self._create_agents()

    def _create_agents(self) -> List[Agent]:
        """Create all available agents."""
        agents = []

        # Always available
        agents.extend(
            [
                ResidentAdvisorAgent(self.config, self.progress_tracker.send_progress),
                WebAgent(self.config, self.progress_tracker.send_progress),
                ImageAgent(self.config, self.progress_tracker.send_progress),
            ]
        )

        # Conditionally available
        if self.config.api.ticketmaster_key:
            agents.append(
                TicketmasterAgent(self.config, self.progress_tracker.send_progress)
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
            agent = self._find_agent(url, request.force_method)
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

    def _find_agent(
        self, url: str, force_method: Optional[str] = None
    ) -> Optional[Agent]:
        """Find an agent that can handle the URL."""
        # If method is forced, try to find matching agent
        if force_method:
            for agent in self.agents:
                if agent.import_method == force_method and agent.can_handle(url):
                    return agent

        # Otherwise find first capable agent
        for agent in self.agents:
            if agent.can_handle(url):
                return agent

        return None

    def add_progress_listener(self, request_id: str, callback) -> None:
        """Add a progress listener for a request."""
        self.progress_tracker.add_listener(request_id, callback)

    def get_progress_history(self, request_id: str) -> List[ImportProgress]:
        """Get progress history for a request."""
        return self.progress_tracker.get_history(request_id)
