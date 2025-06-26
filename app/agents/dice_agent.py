"""Dice.fm agent using search API to find event ID and fetch data."""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from app.config import Config
from app.error_messages import AgentMessages
from app.schemas import (
    EventData,
    EventLocation,
    EventTime,
    ImportMethod,
    ImportProgress,
    ImportStatus,
)
from app.shared.agent import Agent
from app.shared.http import HTTPService

logger = logging.getLogger(__name__)




class DiceAgent(Agent):
    """Agent for importing events from Dice.fm using search API."""

    http: HTTPService

    def __init__(
        self,
        config: Config,
        progress_callback: Callable[[ImportProgress], Awaitable[None]] | None = None,
        services: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(config, progress_callback, services)
        # Use shared services with proper error handling
        self.http = self.get_service("http")

    @property
    def name(self) -> str:
        return "Dice"

    @property
    def import_method(self) -> ImportMethod:
        return ImportMethod.API

    async def import_event(self, url: str, request_id: str) -> EventData | None:
        """Import event from Dice using search API to find event ID."""
        self.start_timer()

        try:
            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                "Searching for event via Dice API",
                0.2,
            )

            # Extract search query from URL
            search_query = self._extract_search_query_from_url(url)
            logger.info(f"Generated search query: {search_query}")

            # Use unified search API to find the event
            event_id = await self._search_for_event_id(search_query, url, request_id)
            if not event_id:
                error_msg = AgentMessages.DICE_EVENT_NOT_FOUND
                raise Exception(error_msg)

            logger.info(f"Found Dice event ID: {event_id}")

            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                "Fetching event data from Dice API",
                0.6,
            )

            # Step 2: Fetch event data from API using the extracted ID
            api_data = await self._fetch_api_data(event_id, request_id)
            if not api_data:
                error_msg = AgentMessages.DICE_DATA_FETCH_FAILED
                raise Exception(error_msg)

            await self.send_progress(
                request_id, ImportStatus.RUNNING, "Processing event data", 0.8,
            )

            # Step 3: Transform API data to EventData
            event_data = self._transform_api_data(api_data, url)
            if not event_data:
                error_msg = AgentMessages.DICE_DATA_TRANSFORM_FAILED
                raise Exception(error_msg)

            # Generate descriptions if missing - use safe service access
            if not event_data.long_description or not event_data.short_description:
                await self.send_progress(
                    request_id, ImportStatus.RUNNING, "Generating descriptions", 0.85,
                )
                try:
                    llm_service = self.get_service("llm")
                    event_data = await llm_service.generate_descriptions(event_data)
                except Exception:
                    logger.exception("Failed to generate descriptions")
                    # Continue without descriptions rather than failing completely

            await self.send_progress(
                request_id,
                ImportStatus.SUCCESS,
                "Successfully imported from Dice API",
                1.0,
                data=event_data,
            )

            return event_data

        except Exception as e:
            logger.exception("Dice import failed")
            await self.send_progress(
                request_id,
                ImportStatus.FAILED,
                f"Import failed: {e!s}",
                1.0,
                error=str(e),
            )
            return None

    def _extract_search_query_from_url(self, url: str) -> str:
        """Extract search query from Dice URL, removing date components and 'tickets'."""
        try:
            slug = url.split("/event/")[-1]
            words = slug.split("-")

            # Remove event ID
            words = words[1:]

            # Remove 'tickets' from the end
            if words and words[-1] == "tickets":
                words.pop()

            # Filter out date-related words
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
            return url  # Fallback

    async def _search_for_event_id(
        self, search_query: str, original_url: str, request_id: str,
    ) -> str | None:
        """Search for event using Dice unified search API and match against the perm_name."""
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
                timeout=10,
            )

            # Log the search response for debugging
            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                "Search response received",
                0.22,
            )

            # Extract event ID from search results by matching the slug
            original_slug = original_url.split("/event/")[-1]

            if "sections" in response:
                for section in response["sections"]:
                    if "items" in section:
                        for item in section["items"]:
                            if "event" in item:
                                event = item["event"]
                                # Verify that the event perm_name matches the original URL's slug
                                if event.get("perm_name") == original_slug:
                                    return event.get("id")

            return None

        except (ValueError, TypeError, KeyError):
            logger.exception(AgentMessages.DICE_SEARCH_FAILED)
            return None

    async def _fetch_api_data(
        self, event_id: str, request_id: str,
    ) -> dict[str, Any] | None:
        """Fetch event data from Dice API."""
        try:
            # Use the ticket_types endpoint
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
                api_url, service="Dice API", headers=headers, timeout=30.0,
            )

            # Log the event data response for debugging
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
        self, api_data: dict[str, Any], source_url: str,
    ) -> EventData | None:
        """Transform Dice API response to EventData format."""
        try:
            # Fix: Remove the incorrect event extraction - data is at root level
            title = api_data.get("name", "")

            # Fix: Access dates directly from api_data, not from non-existent event object
            dates = api_data.get("dates", {})
            event_start = dates.get("event_start_date")
            event_end = dates.get("event_end_date")

            event_time = None
            if event_start:
                event_time = EventTime(
                    start=event_start,
                    end=event_end,
                    timezone=dates.get("timezone", "UTC"),
                )

            # Venues are at root level
            venues = api_data.get("venues", [])
            location = None
            venue_name = None
            if venues:
                venue = venues[0]
                venue_name = venue.get("name")
                city_info = venue.get("city", {})
                location = EventLocation(
                    venue=venue_name,
                    address=venue.get("address"),
                    city=city_info.get("name"),
                    state=None,
                    country=city_info.get("country_name"),
                    coordinates=venue.get("location", {}),
                )

            # Lineup from summary_lineup
            lineup = []
            summary_lineup = api_data.get("summary_lineup", {})
            if summary_lineup and "top_artists" in summary_lineup:
                for artist in summary_lineup["top_artists"]:
                    lineup.append(artist.get("name", ""))

            # Images are at root level
            images = api_data.get("images", {})
            image_dict = None
            if images:
                image_dict = {
                    "full": images.get("landscape") or images.get("square"),
                    "thumbnail": images.get("square") or images.get("portrait"),
                }

            # Ticket info
            ticket_types = api_data.get("ticket_types", [])
            ticket_url = source_url
            price_info = None
            if ticket_types:
                prices = []
                for ticket in ticket_types:
                    if ticket.get("status") == "on-sale":
                        price = ticket.get("price", {})
                        amount = price.get("amount")
                        if amount:
                            prices.append(amount / 100)
                if prices:
                    min_price = min(prices)
                    price_info = {
                        "amount": min_price,
                        "currency": ticket_types[0]
                        .get("price", {})
                        .get("currency", "USD"),
                    }

            # Description from about section - FIX THE BUG HERE
            about = api_data.get("about", {})
            description = about.get("description")

            # Promoters
            promoters = []
            billing_promoter = api_data.get("billing_promoter", {})
            if billing_promoter and billing_promoter.get("name"):
                promoters.append(billing_promoter["name"])

            # Extract date string from event_start_date
            date_str = None
            if event_start:
                date_str = event_start.split("T")[0]

            event_data = EventData(
                title=title,
                long_description=description,
                lineup=lineup if lineup else None,
                time=event_time,
                location=location,
                venue=venue_name,
                date=date_str,
                ticket_url=ticket_url,
                source_url=source_url,
                images=image_dict,
                promoters=promoters if promoters else None,
                price=price_info,
                genres=None,
            )
            return event_data
        except (ValueError, TypeError, KeyError):
            logger.exception(AgentMessages.DICE_TRANSFORM_ERROR)
            return None
