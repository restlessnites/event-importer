"""Resident Advisor GraphQL API agent."""

from __future__ import annotations

import logging
from typing import Any

from dateutil import parser as date_parser

from app.error_messages import AgentMessages, ServiceMessages
from app.schemas import EventData, EventLocation, ImportMethod, ImportStatus
from app.shared.agent import Agent
from app.shared.http import HTTPService
from app.shared.url_analyzer import URLAnalyzer

logger = logging.getLogger(__name__)


class ResidentAdvisorAgent(Agent):
    """Agent for importing events from Resident Advisor."""

    GRAPHQL_URL = "https://ra.co/graphql"
    http: HTTPService

    def __init__(self, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> None:
        super().__init__(*args, **kwargs)
        self.url_analyzer = URLAnalyzer()
        # Use shared services with proper error handling
        self.http = self.get_service("http")

    @property
    def name(self: ResidentAdvisorAgent) -> str:
        return "ResidentAdvisor"

    @property
    def import_method(self: ResidentAdvisorAgent) -> ImportMethod:
        return ImportMethod.API

    async def import_event(
        self: ResidentAdvisorAgent,
        url: str,
        request_id: str,
    ) -> EventData | None:
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
                error_msg = "No event data returned"
                raise Exception(error_msg)

            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                "Parsing event data",
                0.7,
            )

            # Parse to our format
            event_data = self._parse_event(event_json, url)

            if not event_data.genres and self.services.get("genre"):
                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    "Searching for genres",
                    0.8,
                )
                try:
                    genre_service = self.get_service("genre")
                    event_data = await genre_service.enhance_genres(event_data)
                except (ValueError, TypeError, KeyError) as e:
                    logger.debug(f"{ServiceMessages.GENRE_SEARCH_FAILED}: {e}")
                    # Continue without genres

            # Enhance descriptions
            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                "Enhancing descriptions",
                0.85,
            )
            try:
                llm_service = self.get_service("llm")
                event_data = await llm_service.generate_descriptions(event_data)
            except (ValueError, TypeError, KeyError):
                logger.exception(AgentMessages.DESCRIPTION_GENERATION_FAILED)
                # Continue without descriptions rather than failing completely

            await self.send_progress(
                request_id,
                ImportStatus.SUCCESS,
                "Successfully imported event",
                1.0,
                data=event_data,
            )

            return event_data

        except (ValueError, TypeError, KeyError) as e:
            logger.exception(AgentMessages.RA_IMPORT_FAILED)
            await self.send_progress(
                request_id,
                ImportStatus.FAILED,
                f"Import failed: {e!s}",
                1.0,
                error=str(e),
            )
            return None

    async def _fetch_event(self: ResidentAdvisorAgent, event_id: str) -> dict | None:
        """Fetch event from GraphQL API."""
        query = """
        query GET_EVENT($id: ID!) {
          event(id: $id) {
            id
            title
            content
            contentUrl
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

    def _parse_images(self: ResidentAdvisorAgent, event: dict) -> dict[str, str] | None:
        """Parse images from RA event data, returning the first valid image."""
        if (images_list := event.get("images")) and isinstance(images_list, list):
            for img in images_list:
                if filename := img.get("filename"):
                    return {"full": filename, "thumbnail": filename}
        return None

    def _parse_event(self: ResidentAdvisorAgent, event: dict, url: str) -> EventData:
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
            time = self.create_event_time(
                start=event.get("startTime"),
                end=event.get("endTime"),
                location=location,
            )

        # Extract lineup
        lineup = [a["name"] for a in event.get("artists") or []]

        # Extract promoters
        promoters = [p["name"] for p in event.get("promoters") or []]

        # Extract genres
        genres = [g["name"] for g in event.get("genres") or []]

        # Build images from the images array
        images = self._parse_images(event)

        # Generate ticket URL from contentUrl
        ticket_url = None
        if content_url := event.get("contentUrl"):
            ticket_url = f"https://ra.co{content_url}"

        # Extract end_date from endTime
        end_date_str = None
        if end_time_str := event.get("endTime"):
            try:
                end_date_obj = date_parser.parse(end_time_str)
                end_date_str = end_date_obj.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass  # Ignore if parsing fails

        return EventData(
            title=event["title"],
            venue=event.get("venue", {}).get("name"),
            date=event.get("date"),
            end_date=end_date_str,
            time=time,
            lineup=lineup,
            promoters=promoters,
            genres=genres,
            long_description=event.get("content"),
            short_description=None,  # Will be generated by Claude if needed
            location=location,
            images=images,
            cost=event.get("cost"),
            ticket_url=ticket_url,
            source_url=url,
        )
