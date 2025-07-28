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

    async def import_event(self, url: str, _request_id: str) -> EventData | None:
        """Import an event from a Ticketmaster URL.

        Args:
            url: The URL of the event to import.
            _request_id: The ID of the import request (unused).

        Returns:
            The imported event data, or None if the import fails.
        """
        api_key = self.config.api.ticketmaster_key
        if not api_key:
            raise ValueError("Ticketmaster API key not configured")

        event_id = self._extract_event_id(url)
        if not event_id:
            logger.warning(
                "Could not extract Ticketmaster event ID", extra={"url": url}
            )
            return None

        api_url = f"https://app.ticketmaster.com/discovery/v2/events/{event_id}.json"
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
            return None

        event_data = await response.json()
        return self._transform_event_data(event_data, url)

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

        location = self._create_location(venue_data)
        time = (
            self.create_event_time(start=local_time, location=location)
            if local_time
            else None
        )

        return EventData(
            title=event_data.get("name"),
            venue=venue_data.get("name"),
            date=local_date,
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


def get_ticketmaster_id_from_url(url: str) -> str | None:
    """Extract Ticketmaster event ID from a URL."""
    # Regex to find event IDs, which are typically alphanumeric
    match = re.search(r"event/([a-zA-Z0-9]+)", url)
    return match.group(1) if match else None
