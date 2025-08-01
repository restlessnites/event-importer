"""Dice.fm agent using search API to find event ID and fetch data."""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.error_messages import AgentMessages
from app.core.schemas import (
    EventData,
    EventLocation,
    ImportMethod,
    ImportProgress,
    ImportStatus,
)
from app.extraction_agents.base import BaseExtractionAgent
from app.shared.http import HTTPService
from config import Config

logger = logging.getLogger(__name__)


class Dice(BaseExtractionAgent):
    """
    Agent for importing events from Dice.fm.
    """

    http: HTTPService

    def __init__(
        self,
        config: Config,
        progress_callback: Callable[[ImportProgress], Awaitable[None]] | None = None,
        services: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(config, progress_callback, services)
        self.http = self.get_service("http")  # type: ignore[assignment]

    @property
    def name(self) -> str:
        return "Dice"

    @property
    def import_method(self) -> ImportMethod:
        return ImportMethod.API

    async def _perform_extraction(self, url: str, request_id: str) -> EventData | None:
        """Provider-specific logic for Dice.fm."""
        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Searching for event via Dice API",
            0.2,
        )

        search_query = self._extract_search_query_from_url(url)
        logger.info(f"Generated search query: {search_query}")

        event_id = await self._search_for_event_id(search_query, url, request_id)
        if not event_id:
            raise Exception(AgentMessages.DICE_EVENT_NOT_FOUND)

        logger.info(f"Found Dice event ID: {event_id}")

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Fetching event data from Dice API",
            0.6,
        )

        api_data = await self._fetch_api_data(event_id, request_id)
        if not api_data:
            raise Exception(AgentMessages.DICE_DATA_FETCH_FAILED)

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Processing event data",
            0.8,
        )

        event_data = self._transform_api_data(api_data, url)
        if not event_data:
            raise Exception(AgentMessages.DICE_DATA_TRANSFORM_FAILED)

        return event_data

    def _extract_search_query_from_url(self, url: str) -> str:
        """
        Extract a search query from a Dice URL.
        """
        try:
            slug = url.split("/event/")[-1]
            words = slug.split("-")
            words = words[1:]
            if words and words[-1] == "tickets":
                words.pop()
            months = [
                "jan",
                "feb",
                "mar",
                "apr",
                "may",
                "jun",
                "jul",
                "aug",
                "sep",
                "oct",
                "nov",
                "dec",
            ]
            non_date_words = [
                word
                for word in words
                if word.lower() not in months
                and not re.match(r"^\d{1,2}(st|nd|rd|th)?$", word.lower())
            ]
            return " ".join(non_date_words)
        except IndexError:
            return url

    async def _search_for_event_id(
        self,
        search_query: str,
        original_url: str,
        request_id: str,
    ) -> str | None:
        """
        Search for an event ID using the Dice unified search API.
        """
        try:
            search_url = "https://api.dice.fm/unified_search"
            headers = {
                "Accept": "application/json",
                "Accept-Language": "en-US",
                "Content-Type": "application/json",
                "Origin": "https://dice.fm",
                "Referer": "https://dice.fm/",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "X-Api-Timestamp": "2024-03-25",
                "X-Client-Timezone": "America/Los_Angeles",
            }
            payload = {"q": search_query}
            response = await self.http.post_json(
                search_url,
                service="Dice Search",
                headers=headers,
                json=payload,
                timeout=self.config.http.short_timeout,
            )
            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                "Search response received",
                0.22,
            )
            original_slug = original_url.split("/event/")[-1]
            if "sections" in response:
                for section in response["sections"]:
                    if "items" in section:
                        for item in section["items"]:
                            if "event" in item:
                                event = item["event"]
                                if event.get("perm_name") == original_slug:
                                    return event.get("id")
            return None
        except (ValueError, TypeError, KeyError):
            logger.exception(AgentMessages.DICE_SEARCH_FAILED)
            return None

    async def _fetch_api_data(
        self,
        event_id: str,
        request_id: str,
    ) -> dict[str, Any] | None:
        """
        Fetch detailed event data from the Dice API.
        """
        try:
            api_url = f"https://api.dice.fm/events/{event_id}/ticket_types"
            headers = {
                "Accept": "application/json",
                "Accept-Language": "en-US",
                "Cache-Control": "no-cache",
                "Origin": "https://dice.fm",
                "Referer": "https://dice.fm/",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "X-Api-Timestamp": "2024-04-15",
                "X-Client-Timezone": "America/Los_Angeles",
            }
            response = await self.http.get_json(
                api_url,
                service="Dice API",
                headers=headers,
                timeout=self.config.http.timeout,
            )
            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                "Event API response received",
                0.61,
            )
            return response
        except (ValueError, TypeError, KeyError):
            logger.exception(AgentMessages.DICE_API_ERROR)
            return None

    def _transform_api_data(
        self,
        api_data: dict[str, Any],
        source_url: str,
    ) -> EventData | None:
        """Transform Dice API response to EventData format."""
        try:
            location, venue_name = self._extract_location(api_data)
            event_time, date_str, end_date_str = self._extract_time(api_data, location)
            ticket_url, price_info = self._extract_ticket_info(api_data, source_url)
            lineup = self._extract_lineup(api_data)
            promoters = self._extract_promoters(api_data)
            return EventData(
                title=api_data.get("name", ""),
                long_description=api_data.get("about", {}).get("description"),
                lineup=lineup or None,
                time=event_time,
                location=location,
                venue=venue_name,
                date=date_str,
                end_date=end_date_str,
                ticket_url=ticket_url,
                source_url=source_url,
                images=self._extract_images(api_data),
                promoters=promoters or None,
                price=price_info,
                genres=None,
            )
        except (ValueError, TypeError, KeyError):
            logger.exception(AgentMessages.DICE_TRANSFORM_ERROR)
            return None

    def _extract_location(
        self,
        api_data: dict[str, Any],
    ) -> tuple[EventLocation | None, str | None]:
        """Extract location and venue name from API data."""
        venues = api_data.get("venues", [])
        if not venues:
            return None, None
        venue = venues[0]
        venue_name = venue.get("name")
        city_info = venue.get("city", {})
        return EventLocation(
            venue=venue_name,
            address=venue.get("address"),
            city=city_info.get("name"),
            state=None,
            country=city_info.get("country_name"),
            coordinates=venue.get("location", {}),
        ), venue_name

    def _extract_time(
        self,
        api_data: dict[str, Any],
        location: EventLocation | None,
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        """Extract event time and date string from API data."""
        dates = api_data.get("dates", {})
        event_start = dates.get("event_start_date")
        if not event_start:
            return None, None, None
        event_end = dates.get("event_end_date")
        api_timezone = dates.get("timezone")
        event_time = self.create_event_time(
            start=event_start,
            end=event_end,
            location=location,
            timezone=api_timezone,
        )
        start_date_str = event_start.split("T")[0]
        end_date_str = event_end.split("T")[0] if event_end else None
        return event_time, start_date_str, end_date_str

    def _extract_lineup(self, api_data: dict[str, Any]) -> list[str]:
        """Extract lineup from API data."""
        lineup = []
        if summary_lineup := api_data.get("summary_lineup"):
            for artist in summary_lineup.get("top_artists", []):
                if artist_name := artist.get("name"):
                    lineup.append(artist_name)
        return lineup

    def _extract_images(self, api_data: dict[str, Any]) -> dict[str, str] | None:
        """Extract images from API data."""
        if images := api_data.get("images"):
            return {
                "full": images.get("landscape") or images.get("square"),
                "thumbnail": images.get("square") or images.get("portrait"),
            }
        return None

    def _extract_ticket_info(
        self,
        api_data: dict[str, Any],
        source_url: str,
    ) -> tuple[str, dict[str, Any] | None]:
        """Extract ticket URL and price info from API data."""
        ticket_types = api_data.get("ticket_types", [])
        ticket_url = source_url
        price_info = None
        if not ticket_types:
            return ticket_url, price_info
        prices = []
        for ticket in ticket_types:
            if ticket.get("status") == "on-sale" and (
                amount := ticket.get("price", {}).get("amount")
            ):
                prices.append(amount / 100)
        if prices:
            min_price = min(prices)
            price_info = {
                "amount": min_price,
                "currency": ticket_types[0].get("price", {}).get("currency", "USD"),
            }
        return ticket_url, price_info

    def _extract_promoters(self, api_data: dict[str, Any]) -> list[str]:
        """Extract promoters from API data."""
        promoters = []
        if (billing_promoter := api_data.get("billing_promoter")) and (
            promoter_name := billing_promoter.get("name")
        ):
            promoters.append(promoter_name)
        return promoters
