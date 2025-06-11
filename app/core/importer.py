import asyncio
import logging
import aiohttp
from datetime import datetime, timezone
from typing import List, Optional, Dict

from app.config import Config
from app.schemas import (
   ImportRequest,
   ImportResult,
   ImportStatus,
   ImportProgress,
   EventData,
)
from app.shared.agent import Agent
from app.agents import (
   ResidentAdvisorAgent,
   TicketmasterAgent,
   WebAgent,
   ImageAgent,
)
from app.core.progress import ProgressTracker
from app.errors import UnsupportedURLError, handle_errors_async
from app.shared.http import get_http_service
from app.services.claude import ClaudeService
from app.services.image import ImageService
from app.services.zyte import ZyteService
from app.services.genre import GenreService
# Add database imports
from app.shared.database import cache_event, get_cached_event


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
       claude_service = ClaudeService(self.config)

       return {
           "http": self.http,
           "claude": claude_service,
           "image": ImageService(self.config, self.http),
           "zyte": ZyteService(self.config, self.http),
           "genre": GenreService(self.config, self.http, claude_service),
       }

   @handle_errors_async(reraise=True)
   async def import_event(self, request: ImportRequest) -> ImportResult:
       """
       Import an event from a URL.

       Args:
           request: Import request with URL and options

       Returns:
           Import result with event data or error
       """
       start_time = datetime.now(timezone.utc)
       url = str(request.url)

       try:
           await self.progress_tracker.send_progress(
               ImportProgress(
                   request_id=request.request_id,
                   status=ImportStatus.RUNNING,
                   message="Starting import",
                   progress=0.1,
               )
           )

            # Check cache first
           cached_data = get_cached_event(str(url))
           if cached_data:
                logger.info(f"Found cached event for {url}")
                
                # Convert cached data to EventData
                event_data = EventData(**cached_data)
                
                return ImportResult(
                    request_id=request.request_id,
                    status=ImportStatus.SUCCESS,
                    url=request.url,
                    method_used=None,
                    event_data=event_data,
                    import_time=(
                        datetime.now(timezone.utc) - start_time
                    ).total_seconds(),
                )
           # Find capable agent
           agent = await self._determine_agent(url, request.force_method)
           if not agent:
               raise UnsupportedURLError(url)

           logger.info(f"Using {agent.name} for {url}")

           # Run import with timeout
           event_data = await asyncio.wait_for(
               agent.import_event(url, request.request_id), timeout=request.timeout
           )

           if event_data and not event_data.genres:
               await self.progress_tracker.send_progress(
                   ImportProgress(
                       request_id=request.request_id,
                       status=ImportStatus.RUNNING,
                       message="Searching for artist genres",
                       progress=0.95,
                   )
               )

               try:
                   event_data = await self._services["genre"].enhance_genres(
                       event_data
                   )
               except Exception as e:
                   logger.warning(f"Genre enhancement failed: {e}")
                   # Continue without genres rather than failing

           # Create result
           if event_data:
               # Cache the successful result
               cache_event(str(url), event_data.model_dump(mode="json"))

               await self.progress_tracker.send_progress(
                   ImportProgress(
                       request_id=request.request_id,
                       status=ImportStatus.SUCCESS,
                       message="Import completed successfully",
                       progress=1.0,
                       data=event_data,
                   )
               )

               return ImportResult(
                   request_id=request.request_id,
                   status=ImportStatus.SUCCESS,
                   url=request.url,
                   method_used=agent.import_method.value,
                   event_data=event_data,
                   import_time=(
                       datetime.now(timezone.utc) - start_time
                   ).total_seconds(),
               )
           else:
               error = "Agent returned no data"
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
               )
           )
           return ImportResult(
               request_id=request.request_id,
               status=ImportStatus.FAILED,
               url=request.url,
               error=error,
               import_time=(datetime.now(timezone.utc) - start_time).total_seconds(),
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
               import_time=(datetime.now(timezone.utc) - start_time).total_seconds(),
           )

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

       # Conditionally available - check if API key is configured
       if self.config.api.ticketmaster_key:
           agents.append(
               TicketmasterAgent(
                   self.config, progress_callback, services=self._services
               )
           )

       return agents

   async def _determine_agent(
       self, url: str, force_method: Optional[str] = None
   ) -> Optional[Agent]:
       """Determine which agent should handle the URL using content-type and URL analysis."""
       
       if force_method:
           # Find agent by method name mapping
           method_mapping = {
               "api": ["ResidentAdvisorAgent", "TicketmasterAgent"],
               "web": ["WebScraper"], 
               "image": ["ImageAgent"],
           }
           
           target_agents = method_mapping.get(force_method, [])
           for agent in self.agents:
               if agent.name in target_agents:
                   return agent
           
           logger.warning(f"Forced method '{force_method}' not available")

       # Content-type based routing
       try:
          response = await self.http.head(
              url,
              service="ContentTypeCheck",
               timeout=10
          )
          content_type = response.headers.get("Content-Type", "").lower()
          logger.info(f"Content-Type for {url}: {content_type}")

          # Route by content-type
          if content_type.startswith("image/"):
              return self._get_agent_by_name("ImageAgent")
          elif content_type.startswith(("text/html", "application/")):
              return self._get_agent_by_name("WebScraper")
                        
       except Exception as e:
          logger.warning(f"Failed to check content-type for {url}: {e}")

        # URL pattern based routing for specialized agents
       from app.shared.url_analyzer import URLAnalyzer
       analyzer = URLAnalyzer()
       analysis = analyzer.analyze(url)
       
       # Route to specialized agents based on URL analysis
       if analysis.get("type") == "ra" and "event_id" in analysis:
           return self._get_agent_by_name("ResidentAdvisorAgent")
       elif analysis.get("type") == "ticketmaster" and "event_id" in analysis:
           agent = self._get_agent_by_name("TicketmasterAgent") 
           # Only return if API key is configured
           return agent if self.config.api.ticketmaster_key else None

       # Default fallback to WebAgent for any remaining URLs
       return self._get_agent_by_name("WebScraper")

   def _get_agent_by_name(self, name: str) -> Optional[Agent]:
       """Get agent by name."""
       for agent in self.agents:
           if agent.name == name:
               return agent
       return None

   def add_progress_listener(self, request_id: str, callback):
       """Add a progress listener for a specific request."""
       self.progress_tracker.add_listener(request_id, callback)

   def remove_progress_listener(self, request_id: str):
       """Remove progress listener for a request."""
       self.progress_tracker.remove_listener(request_id)

   def get_progress_history(self, request_id: str):
       """Get the progress history for a request."""
       return self.progress_tracker.get_history(request_id)