"""Resident Advisor GraphQL API agent."""

import logging
from typing import Optional

from app.shared.agent import Agent
from app.schemas import EventData, ImportMethod, ImportStatus, EventTime, EventLocation
from app.shared.url_analyzer import URLAnalyzer


logger = logging.getLogger(__name__)


class ResidentAdvisorAgent(Agent):
    """Agent for importing events from Resident Advisor."""

    GRAPHQL_URL = "https://ra.co/graphql"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url_analyzer = URLAnalyzer()
        # Use shared services
        self.http = self.services["http"]
        self.claude = self.services["claude"]

    @property
    def name(self) -> str:
        return "ResidentAdvisor"

    @property
    def import_method(self) -> ImportMethod:
        return ImportMethod.API
  
    async def import_event(self, url: str, request_id: str) -> Optional[EventData]:
        """Import event from RA GraphQL API."""
        self.start_timer()

        # Extract event ID
        analysis = self.url_analyzer.analyze(url)
        event_id = analysis.get("event_id")
        if not event_id:
            return None

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            f"Fetching event {event_id} from RA API",
            0.3,
        )

        try:
            # Fetch event data
            event_json = await self._fetch_event(event_id)
            if not event_json:
                raise Exception("No event data returned")

            await self.send_progress(
                request_id, ImportStatus.RUNNING, "Parsing event data", 0.7
            )

            # Parse to our format
            event_data = self._parse_event(event_json, url)

            if not event_data.genres and self.services.get("genre"):
                await self.send_progress(
                    request_id, ImportStatus.RUNNING, "Searching for genres", 0.8
                )
                try:
                    event_data = await self.services["genre"].enhance_genres(event_data)
                except Exception as e:
                    logger.debug(f"Genre search failed: {e}")
                    # Continue without genres

            # Generate descriptions if missing using Claude
            if not event_data.long_description or not event_data.short_description:
                await self.send_progress(
                    request_id, ImportStatus.RUNNING, "Generating descriptions", 0.85
                )
                event_data = await self.claude.generate_descriptions(event_data)

            await self.send_progress(
                request_id,
                ImportStatus.SUCCESS,
                "Successfully imported event",
                1.0,
                data=event_data,
            )

            return event_data

        except Exception as e:
            logger.error(f"RA import failed: {e}")
            await self.send_progress(
                request_id,
                ImportStatus.FAILED,
                f"Import failed: {str(e)}",
                1.0,
                error=str(e),
            )
            return None

    async def _fetch_event(self, event_id: str) -> Optional[dict]:
        """Fetch event from GraphQL API."""
        query = """
        query GET_EVENT($id: ID!) {
          event(id: $id) {
            id
            title
            content
            date
            startTime
            endTime
            cost
            flyerFront
            images {
              id
              filename
              alt
              type
              crop
            }
            venue {
              name
              area {
                name
                country {
                  name
                }
              }
            }
            artists {
              name
            }
            promoters {
              name
            }
            genres {
              name
            }
          }
        }
        """

        headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "https://ra.co",
            "ra-content-language": "en",
        }

        data = await self.http.post_json(
            self.GRAPHQL_URL,
            service="RA",
            headers=headers,
            json={
                "operationName": "GET_EVENT",
                "variables": {"id": event_id},
                "query": query,
            },
        )

        return data.get("data", {}).get("event")

    def _parse_event(self, event: dict, url: str) -> EventData:
        """Parse RA event data to our schema."""
        # Build location
        location = None
        if event.get("venue"):
            venue = event["venue"]
            if venue.get("area"):
                location = EventLocation(
                    city=venue["area"].get("name"),
                    country=venue["area"].get("country", {}).get("name"),
                )

        # Build time
        time = None
        if event.get("startTime") or event.get("endTime"):
            time = EventTime(
                start=event.get("startTime"),
                end=event.get("endTime"),
            )

        # Extract lineup
        lineup = []
        if event.get("artists"):
            lineup = [a["name"] for a in event["artists"]]

        # Extract promoters
        promoters = []
        if event.get("promoters"):
            promoters = [p["name"] for p in event["promoters"]]

        # Extract genres
        genres = []
        if event.get("genres"):
            genres = [g["name"] for g in event["genres"]]

        # Build images from the images array
        images = None
        if event.get("images") and isinstance(event["images"], list):
            for img in event["images"]:
                if img.get("filename"):
                    images = {
                        "full": img["filename"],
                        "thumbnail": img["filename"],
                    }
                    break  # Use the first image with a filename

        return EventData(
            title=event["title"],
            venue=event.get("venue", {}).get("name"),
            date=event.get("date"),
            time=time,
            lineup=lineup,
            promoters=promoters,
            genres=genres,
            long_description=event.get("content"),
            short_description=None,  # Will be generated by Claude if needed
            location=location,
            images=images,
            cost=event.get("cost"),
            source_url=url,
        )
