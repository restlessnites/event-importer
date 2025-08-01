"""Resident Advisor GraphQL API agent."""

from __future__ import annotations

import logging
from typing import Any

from dateutil import parser as date_parser

from app.core.schemas import EventData, EventLocation, ImportMethod, ImportStatus
from app.extraction_agents.base import BaseExtractionAgent
from app.shared.http import HTTPService
from app.shared.url_analyzer import URLAnalyzer

logger = logging.getLogger(__name__)


class ResidentAdvisor(BaseExtractionAgent):
    """Agent for importing events from Resident Advisor."""

    GRAPHQL_URL = "https://ra.co/graphql"
    http: HTTPService

    def __init__(self, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> None:
        super().__init__(*args, **kwargs)
        self.url_analyzer = URLAnalyzer()
        self.http = self.get_service("http")  # type: ignore[assignment]

    @property
    def name(self: ResidentAdvisor) -> str:
        return "ResidentAdvisor"

    @property
    def import_method(self: ResidentAdvisor) -> ImportMethod:
        return ImportMethod.API

    async def _perform_extraction(
        self: ResidentAdvisor,
        url: str,
        request_id: str,
    ) -> EventData | None:
        """Provider-specific logic for Resident Advisor."""
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

        event_json = await self._fetch_event(event_id)
        if not event_json:
            raise Exception("No event data returned from RA API")

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Parsing event data",
            0.7,
        )

        return self._parse_event(event_json, url)

    async def _fetch_event(self: ResidentAdvisor, event_id: str) -> dict | None:
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

    def _parse_images(self: ResidentAdvisor, event: dict) -> dict[str, str] | None:
        """Parse images from RA event data, returning the first valid image."""
        if (images_list := event.get("images")) and isinstance(images_list, list):
            for img in images_list:
                if filename := img.get("filename"):
                    return {"full": filename, "thumbnail": filename}
        return None

    def _parse_event(self: ResidentAdvisor, event: dict, url: str) -> EventData:
        """Parse RA event data to our schema."""
        location = None
        if (venue_data := event.get("venue")) and (area_data := venue_data.get("area")):
            location = EventLocation(
                city=area_data.get("name"),
                country=area_data.get("country", {}).get("name"),
            )
        time = self.create_event_time(
            start=event.get("startTime"),
            end=event.get("endTime"),
            location=location,
        )
        lineup = [a["name"] for a in event.get("artists") or []]
        promoters = [p["name"] for p in event.get("promoters") or []]
        genres = [g["name"] for g in event.get("genres") or []]
        images = self._parse_images(event)
        ticket_url = (
            f"https://ra.co{event['contentUrl']}" if event.get("contentUrl") else None
        )
        end_date_str = None
        if end_time_str := event.get("endTime"):
            try:
                end_date_obj = date_parser.parse(end_time_str)
                end_date_str = end_date_obj.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass
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
            short_description=None,
            location=location,
            images=images,
            cost=event.get("cost"),
            ticket_url=ticket_url,
            source_url=url,
        )
