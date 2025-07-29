"""Ticketmaster Discovery API agent."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.schemas import (
    Coordinates,
    EventData,
    EventLocation,
    ImportMethod,
    ImportStatus,
)
from app.shared.agent import Agent

logger = logging.getLogger(__name__)


class TicketmasterAgent(Agent):
    """Agent for importing events from Ticketmaster."""

    @property
    def name(self) -> str:
        """Agent name."""
        return "ticketmaster"

    @property
    def import_method(self) -> ImportMethod:
        """Import method."""
        return ImportMethod.API

    async def import_event(self, url: str, request_id: str) -> EventData | None:
        """Import an event from a Ticketmaster URL.

        Args:
            url: The URL of the event to import.
            request_id: The ID of the import request.

        Returns:
            The imported event data, or None if the import fails.
        """
        self.start_timer()

        try:
            api_key = self.config.api.ticketmaster_key
            if not api_key:
                raise ValueError("Ticketmaster API key not configured")

            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                "Extracting event ID from URL",
                0.2,
            )
            event_id = self._extract_event_id(url)
            if not event_id:
                logger.warning(
                    "Could not extract Ticketmaster event ID, allowing fallback.",
                    extra={"url": url},
                )
                return None

            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                "Fetching event data from Ticketmaster API",
                0.5,
            )
            api_url = (
                f"https://app.ticketmaster.com/discovery/v2/events/{event_id}.json"
            )
            params = {"apikey": api_key}

            http_service = self.get_service("http")
            response = await http_service.get(api_url, params=params)

            if response.status != 200:
                error_data = await response.json()
                error_message = error_data.get("fault", {}).get(
                    "faultstring", "Unknown API error"
                )
                logger.error(
                    f"Ticketmaster API error: {error_message}",
                    extra={"status_code": response.status, "url": url},
                )
                return None  # Allow fallback to web scraper

            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                "Processing event data",
                0.7,
            )
            api_event_data = await response.json()
            event_data = self._transform_event_data(api_event_data, url)

            if not event_data:
                raise Exception("Failed to transform Ticketmaster API data")

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
            except Exception:
                logger.exception("Failed to enhance descriptions")
                # Continue without descriptions rather than failing completely

            await self.send_progress(
                request_id,
                ImportStatus.SUCCESS,
                "Successfully imported from Ticketmaster",
                1.0,
                data=event_data,
            )

            return event_data

        except Exception as e:
            logger.exception("Ticketmaster import failed")
            await self.send_progress(
                request_id,
                ImportStatus.FAILED,
                f"Import failed: {e!s}",
                1.0,
                error=str(e),
            )
            return None

    def _extract_event_id(self, url: str) -> str | None:
        """Extract event ID from Ticketmaster URL."""
        match = re.search(r"/event/(\w+)", url)
        return match.group(1) if match else None

    def _transform_event_data(
        self, event_data: dict[str, Any], source_url: str
    ) -> EventData | None:
        """Transform Ticketmaster API response into EventData."""
        if not event_data:
            return None

        embedded = event_data.get("_embedded", {})
        venue_data = embedded.get("venues", [{}])[0]
        attractions = embedded.get("attractions", [])

        start_date = event_data.get("dates", {}).get("start", {})
        local_date = start_date.get("localDate")
        local_time = start_date.get("localTime")

        end_date_data = event_data.get("dates", {}).get("end", {})
        end_date = end_date_data.get("localDate")
        end_time = end_date_data.get("localTime")

        location = self._create_location(venue_data)
        time = self.create_event_time(start=local_time, end=end_time, location=location)

        return EventData(
            title=event_data.get("name"),
            venue=venue_data.get("name"),
            date=local_date,
            end_date=end_date,
            time=time,
            lineup=[att.get("name") for att in attractions if att.get("name")],
            genres=[
                c.get("genre", {}).get("name")
                for c in event_data.get("classifications", [])
                if c.get("genre", {}).get("name")
            ],
            location=location,
            source_url=source_url,
        )

    def _create_location(self, venue_data: dict[str, Any]) -> EventLocation | None:
        """Create an EventLocation object from venue data."""
        if not venue_data:
            return None

        coords = venue_data.get("location")
        coordinates = (
            Coordinates(lat=float(coords["latitude"]), lng=float(coords["longitude"]))
            if coords and "latitude" in coords and "longitude" in coords
            else None
        )

        return EventLocation(
            address=venue_data.get("address", {}).get("line1"),
            city=venue_data.get("city", {}).get("name"),
            state=venue_data.get("state", {}).get("stateCode"),
            country=venue_data.get("country", {}).get("countryCode"),
            coordinates=coordinates,
        )
