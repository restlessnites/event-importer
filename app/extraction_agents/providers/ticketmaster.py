"""Ticketmaster Discovery API agent."""

from __future__ import annotations

import datetime
import logging
import re
from typing import Any
from urllib.parse import urlparse

from app.core.schemas import (
    Coordinates,
    EventData,
    EventLocation,
    ImportMethod,
    ImportStatus,
)
from app.extraction_agents.base import BaseExtractionAgent

logger = logging.getLogger(__name__)


class Ticketmaster(BaseExtractionAgent):
    """Agent for importing events from Ticketmaster."""

    @property
    def name(self) -> str:
        """Agent name."""
        return "ticketmaster"

    @property
    def import_method(self) -> ImportMethod:
        """Import method."""
        return ImportMethod.API

    async def _perform_extraction(self, url: str, request_id: str) -> EventData | None:
        """Provider-specific logic for Ticketmaster."""
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
                "Could not extract Ticketmaster event ID.", extra={"url": url}
            )
            return None

        api_event_data = await self._try_direct_event_lookup(event_id, api_key)

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
            search_result = await self._search_for_event(url, api_key)
            if search_result:
                api_event_data = search_result

        if not api_event_data:
            logger.error(
                "Could not find event via direct lookup or search",
                extra={"url": url},
            )
            return None

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Processing event data",
            0.7,
        )
        event_data = self._transform_event_data(api_event_data, url)
        if not event_data:
            raise Exception("Failed to transform Ticketmaster API data")

        return event_data

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
            try:
                return await http_service.get_json(
                    api_url, service="Ticketmaster", params=params
                )
            except Exception as e:
                if "404" in str(e):
                    logger.info(
                        f"Event not found with ID {event_id}, will try search",
                        extra={"error": str(e)},
                    )
                else:
                    logger.error(
                        f"Ticketmaster API error: {e}",
                        extra={"error": str(e)},
                    )
                return None
        except Exception:
            logger.exception("Direct event lookup failed")
            return None

    async def _search_for_event(self, url: str, api_key: str) -> dict | None:
        """Search for event using keywords from URL."""
        try:
            search_info = self._extract_search_info_from_url(url)
            if not search_info.get("keyword"):
                logger.warning("Could not extract search keywords from URL")
                return None

            params = self._build_search_params(search_info, api_key)
            http_service = self.get_service("http")
            search_url = "https://app.ticketmaster.com/discovery/v2/events.json"

            try:
                data = await http_service.get_json(
                    search_url, service="Ticketmaster", params=params
                )
            except Exception as e:
                logger.error(f"Ticketmaster search request failed: {e}")
                raise

            events = data.get("_embedded", {}).get("events", [])
            if not events:
                logger.warning(
                    f"No events found for search: {search_info}",
                    extra={
                        "total_elements": data.get("page", {}).get("totalElements", 0)
                    },
                )
                return None

            return self._find_best_match(events, search_info["keyword"])

        except Exception:
            logger.exception("Event search failed")
            return None

    def _build_search_params(self, search_info: dict, api_key: str) -> dict:
        """Build search parameters for Ticketmaster API."""
        params = {
            "apikey": api_key,
            "keyword": search_info["keyword"],
            "size": 50,
            "sort": "date,asc",
        }
        if state_code := search_info.get("stateCode"):
            params["stateCode"] = state_code
        if search_date := search_info.get("date"):
            date_parts = search_date.split("-")
            if len(date_parts) == 3:
                target_date = datetime.date(
                    int(date_parts[2]), int(date_parts[0]), int(date_parts[1])
                )
                start_date = target_date - datetime.timedelta(days=3)
                end_date = target_date + datetime.timedelta(days=3)
                params["localStartDateTime"] = (
                    f"{start_date.isoformat()}T00:00:00,{end_date.isoformat()}T23:59:59"
                )
        return params

    def _find_best_match(self, events: list, search_keyword: str) -> dict | None:
        """Find the best matching event from search results."""
        best_match = None
        search_keywords = search_keyword.lower().split()
        for event in events:
            event_name = event.get("name", "").lower()
            if all(keyword in event_name for keyword in search_keywords):
                logger.info(
                    "Found matching event via search: %s (ID: %s)",
                    event.get("name"),
                    event.get("id"),
                )
                return event
            if not best_match:
                best_match = event
        if best_match:
            logger.info(
                "Using closest match: %s (ID: %s)",
                best_match.get("name"),
                best_match.get("id"),
            )
        return best_match

    def _extract_search_info_from_url(self, url: str) -> dict:
        """Extract searchable information from URL."""
        path = urlparse(url).path
        parts = path.strip("/").split("/")
        if not parts or parts[0] == "event":
            return {}

        slug = parts[0]
        words = slug.split("-")

        city_parts, state = self._extract_location_from_words(words)
        date = self._extract_date_from_slug(slug)
        keyword = self._build_keyword(words, city_parts, state)

        search_info = {}
        if keyword:
            search_info["keyword"] = keyword
        if city_parts:
            search_info["city"] = " ".join(city_parts).title()
        if state:
            search_info["stateCode"] = self.state_mapping[state]
        if date:
            search_info["date"] = date
        logger.info(f"Extracted search info: {search_info}")
        return search_info

    def _extract_location_from_words(
        self, words: list[str]
    ) -> tuple[list[str], str | None]:
        """Extract city and state from a list of words."""
        for i, word in enumerate(words):
            if word.lower() in self.state_mapping:
                state = word.lower()
                city_parts = self._find_city_parts(words, i)
                return city_parts, state
        return [], None

    def _find_city_parts(self, words: list[str], state_index: int) -> list[str]:
        """Find city parts from words based on state index."""
        if state_index == 0:
            return []

        skip_words = [
            "tour",
            "world",
            "concert",
            "show",
            "live",
            "presents",
            "vs",
            "versus",
            "at",
            "the",
        ]
        for j in range(state_index - 1, -1, -1):
            word = words[j].lower()
            if word not in skip_words and not word.isdigit() and len(word) > 2:
                if j > 0 and words[j - 1].lower() in [
                    "los",
                    "san",
                    "new",
                    "las",
                    "el",
                    "la",
                ]:
                    return [words[j - 1], words[j]]
                return [words[j]]
        return []

    def _extract_date_from_slug(self, slug: str) -> str | None:
        """Extract date from URL slug."""
        if date_match := re.search(r"(\d{1,2}-\d{1,2}-\d{4})", slug):
            return date_match.group(1)
        return None

    def _build_keyword(
        self, words: list[str], city_parts: list[str], state: str | None
    ) -> str:
        """Build a search keyword from filtered words."""
        keyword_parts = self._filter_keyword_words(words, city_parts, state)
        if not keyword_parts:
            return ""

        keyword = []
        i = 0
        while i < len(keyword_parts) and len(keyword) < 4:
            if keyword_parts[i].lower() == "the" and i + 1 < len(keyword_parts):
                keyword.extend([keyword_parts[i], keyword_parts[i + 1]])
                i += 2
            else:
                keyword.append(keyword_parts[i])
                i += 1
        return " ".join(keyword[:4])

    def _filter_keyword_words(
        self, words: list[str], city_parts: list[str], state: str | None
    ) -> list[str]:
        """Filter words to build keyword, excluding location and dates."""
        return [
            word
            for word in words
            if word not in city_parts
            and word != state
            and not re.match(r"\d{1,2}-\d{1,2}-\d{4}", word)
            and not re.match(r"\d{4}", word)
            and len(word) > 2
        ]

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
        local_date, local_time = (
            start_date.get("localDate"),
            start_date.get("localTime"),
        )
        end_date_data = event_data.get("dates", {}).get("end", {})
        end_date, end_time = (
            end_date_data.get("localDate"),
            end_date_data.get("localTime"),
        )
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
