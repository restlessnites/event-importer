"""Ticketmaster Discovery API agent."""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

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
            api_key = self.config.api.ticketmaster_api_key
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

            # Try direct event lookup first
            api_event_data = await self._try_direct_event_lookup(event_id, api_key)

            # If direct lookup fails, try search
            if not api_event_data:
                logger.info(
                    "Direct event lookup failed, trying search",
                    extra={"url": url, "event_id": event_id},
                )
                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    "Searching for event by name",
                    0.4,
                )
                api_event_data = await self._search_for_event(url, api_key)

            if not api_event_data:
                logger.error(
                    "Could not find event via direct lookup or search",
                    extra={"url": url},
                )
                return None  # Allow fallback to web scraper

            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                "Processing event data",
                0.7,
            )
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

    async def _try_direct_event_lookup(
        self, event_id: str, api_key: str
    ) -> dict | None:
        """Try to fetch event directly by ID."""
        try:
            api_url = (
                f"https://app.ticketmaster.com/discovery/v2/events/{event_id}.json"
            )
            params = {"apikey": api_key}

            http_service = self.get_service("http")
            response = await http_service.get(api_url, params=params)

            if response.status == 200:
                return await response.json()

            error_data = await response.json()
            if response.status == 404:
                logger.info(
                    f"Event not found with ID {event_id}, will try search",
                    extra={"error": error_data},
                )
            else:
                logger.error(
                    f"Ticketmaster API error: {error_data}",
                    extra={"status_code": response.status},
                )
            return None
        except Exception:
            logger.exception("Direct event lookup failed")
            return None

    async def _search_for_event(self, url: str, api_key: str) -> dict | None:
        """Search for event using keywords from URL."""
        try:
            # Extract search info from URL
            search_info = self._extract_search_info_from_url(url)
            if not search_info.get("keyword"):
                logger.warning("Could not extract search keywords from URL")
                return None

            # Search parameters
            params = {
                "apikey": api_key,
                "keyword": search_info["keyword"],
                "size": 20,
                "sort": "date,asc",
            }

            # Add state code but not city (city might be too specific)
            if search_info.get("stateCode"):
                params["stateCode"] = search_info["stateCode"]

            # Add date range if we have a date
            if search_info.get("date"):
                # Convert MM-DD-YYYY to YYYY-MM-DD
                date_parts = search_info["date"].split("-")
                if len(date_parts) == 3:
                    formatted_date = f"{date_parts[2]}-{date_parts[0].zfill(2)}-{date_parts[1].zfill(2)}"
                    params["localStartDateTime"] = (
                        f"{formatted_date}T00:00:00,{formatted_date}T23:59:59"
                    )

            http_service = self.get_service("http")
            search_url = "https://app.ticketmaster.com/discovery/v2/events.json"
            response = await http_service.get(search_url, params=params)

            if response.status != 200:
                logger.error(f"Search failed with status {response.status}")
                return None

            data = await response.json()
            events = data.get("_embedded", {}).get("events", [])

            if not events:
                logger.warning(
                    f"No events found for search: {search_info}",
                    extra={
                        "total_elements": data.get("page", {}).get("totalElements", 0)
                    },
                )
                return None

            # Return the first matching event
            event = events[0]
            logger.info(
                f"Found event via search: {event.get('name')} (ID: {event.get('id')})"
            )
            return event

        except Exception:
            logger.exception("Event search failed")
            return None

    def _extract_search_info_from_url(self, url: str) -> dict:
        """Extract searchable information from URL."""
        search_info = {}
        path = urlparse(url).path

        # Extract components from URL path
        # Example: /the-brian-jonestown-massacre-los-angeles-california-11-22-2025/event/...
        parts = path.strip("/").split("/")
        if parts and parts[0] != "event":
            # The slug before /event/ contains event info
            slug = parts[0]
            words = slug.split("-")

            # Try to identify location (usually near the end)
            location_keywords = [
                "california",
                "new-york",
                "texas",
                "florida",
                "illinois",
            ]
            city_parts = []
            state = None

            for i, word in enumerate(words):
                if word.lower() in location_keywords:
                    state = word
                    # City is usually before state
                    if i > 0:
                        city_parts = words[max(0, i - 2) : i]
                    break

            # Extract date if present (format: MM-DD-YYYY)
            date_match = re.search(r"(\d{1,2}-\d{1,2}-\d{4})", slug)
            if date_match:
                search_info["date"] = date_match.group(1)

            # Build keyword from remaining parts (artist/event name)
            keyword_parts = []
            keyword_parts = self._filter_keyword_words(words, city_parts, state)

            if keyword_parts:
                # Take first 5-6 words as keyword
                search_info["keyword"] = " ".join(keyword_parts[:6])

            if city_parts:
                search_info["city"] = " ".join(city_parts).title()
            if state:
                search_info["stateCode"] = state[:2].upper()

        logger.info(f"Extracted search info: {search_info}")
        return search_info

    def _filter_keyword_words(
        self, words: list[str], city_parts: list[str], state: str | None
    ) -> list[str]:
        """Filter words to build keyword, excluding location and dates."""
        keyword_parts = []
        for word in words:
            if (
                word not in city_parts
                and word != state
                and not re.match(r"\d{1,2}-\d{1,2}-\d{4}", word)
                and not re.match(r"\d{4}", word)  # Skip year
                and len(word) > 2
            ):
                keyword_parts.append(word)
        return keyword_parts

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
