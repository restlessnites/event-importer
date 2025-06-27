"""Ticketmaster Discovery API agent."""

from __future__ import annotations

import logging
from typing import Any

from app.error_messages import AgentMessages, ServiceMessages
from app.schemas import EventData, EventLocation, EventTime, ImportMethod, ImportStatus
from app.shared.agent import Agent
from app.shared.http import HTTPService
from app.shared.url_analyzer import URLAnalyzer

logger = logging.getLogger(__name__)




class TicketmasterAgent(Agent):
    """Agent for importing events from Ticketmaster."""

    API_BASE = "https://app.ticketmaster.com/discovery/v2"
    http: HTTPService
    api_key: str | None

    def __init__(self, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> None:
        super().__init__(*args, **kwargs)
        self.url_analyzer = URLAnalyzer()
        # Use shared services with proper error handling
        self.http = self.get_service("http")
        self.api_key = self.config.api.ticketmaster_key

    @property
    def name(self: TicketmasterAgent) -> str:
        return "Ticketmaster"

    @property
    def import_method(self: TicketmasterAgent) -> ImportMethod:
        return ImportMethod.API

    async def import_event(
        self: TicketmasterAgent, url: str, request_id: str,
    ) -> EventData | None:
        """Import event from Ticketmaster Discovery API."""
        self.start_timer()

        if not self.api_key:
            logger.error("Ticketmaster API key not configured")
            return None

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Extracting event ID from URL",
            0.1,
        )

        try:
            # Extract event information from URL
            search_info = self.url_analyzer.analyze(url)
            if not search_info:
                error_msg = AgentMessages.TICKETMASTER_URL_EXTRACT_FAILED
                raise Exception(error_msg)

            # Try to find the event using search
            event = await self._search_for_event(search_info)
            if not event:
                error_msg = AgentMessages.TICKETMASTER_EVENT_NOT_FOUND
                raise Exception(error_msg)

            await self.send_progress(
                request_id, ImportStatus.RUNNING, "Parsing event data", 0.6,
            )

            # Parse the event data
            event_data = self._parse_event(event, url)

            await self.send_progress(
                request_id, ImportStatus.RUNNING, "Enhancing event data", 0.75,
            )

            if not event_data.genres and self.services.get("genre"):
                await self.send_progress(
                    request_id, ImportStatus.RUNNING, "Searching for genres", 0.8,
                )
                try:
                    genre_service = self.get_service("genre")
                    event_data = await genre_service.enhance_genres(event_data)
                except (ValueError, TypeError, KeyError) as e:
                    logger.debug(f"{ServiceMessages.GENRE_SEARCH_FAILED}: {e}")
                    # Continue without genres

            # Generate descriptions if missing - use safe service access
            if not event_data.long_description or not event_data.short_description:
                await self.send_progress(
                    request_id, ImportStatus.RUNNING, "Generating descriptions", 0.85,
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
            logger.exception(AgentMessages.TICKETMASTER_IMPORT_FAILED)
            await self.send_progress(
                request_id,
                ImportStatus.FAILED,
                f"Import failed: {e!s}",
                1.0,
                error=str(e),
            )
            return None

    async def _fetch_event(self: TicketmasterAgent, event_id: str) -> dict | None:
        """Fetch event from Discovery API."""
        try:
            data = await self.http.get_json(
                f"{self.API_BASE}/events/{event_id}.json",
                service="Ticketmaster",
                params={"apikey": self.api_key},
            )
            return data
        except (ValueError, TypeError, KeyError):
            # Try searching if direct fetch fails
            logger.info("Direct fetch failed, trying search")
            return None

    def _parse_event(self: TicketmasterAgent, event: dict, url: str) -> EventData:
        """Parse Ticketmaster event data to our schema, with robust description extraction."""
        # Extract venue and location first (needed for timezone)
        venue_name = None
        location = None
        if event.get("_embedded", {}).get("venues"):
            venue = event["_embedded"]["venues"][0]
            venue_name = venue.get("name")

            # Build location
            loc_parts = {}
            if venue.get("address", {}).get("line1"):
                loc_parts["address"] = venue["address"]["line1"]
            if venue.get("city", {}).get("name"):
                loc_parts["city"] = venue["city"]["name"]
            if venue.get("state"):
                loc_parts["state"] = venue["state"].get("stateCode")
            if venue.get("country", {}).get("name"):
                loc_parts["country"] = venue["country"]["name"]

            if loc_parts:
                location = EventLocation(**loc_parts)

        # Extract date and time (with timezone from location)
        date = None
        time = None
        if event.get("dates", {}).get("start"):
            start = event["dates"]["start"]
            if start.get("localDate"):
                date = start["localDate"]
            if start.get("localTime"):
                time = self.create_event_time(
                    start=start["localTime"],
                    location=location,
                )

        # Extract lineup
        lineup = []
        if event.get("_embedded", {}).get("attractions"):
            lineup = [a["name"] for a in event["_embedded"]["attractions"]]

        # Extract genres
        genres = []
        if event.get("classifications"):
            for c in event["classifications"]:
                if c.get("genre", {}).get("name"):
                    genres.append(c["genre"]["name"])

        # Extract cost
        cost = None
        if event.get("priceRanges"):
            pr = event["priceRanges"][0]
            if pr.get("min") and pr.get("max"):
                cost = f"${pr['min']:.2f} - ${pr['max']:.2f}"
            elif pr.get("min"):
                cost = f"${pr['min']:.2f}"

        # Extract images
        images = None
        if event.get("images"):
            # Sort by width to get highest res
            sorted_images = sorted(
                event["images"], key=lambda x: int(x.get("width", 0)), reverse=True,
            )
            if sorted_images:
                images = {
                    "full": sorted_images[0]["url"],
                    "thumbnail": sorted_images[-1]["url"],
                }

        # Robust description extraction
        long_description = (
            event.get("info")
            or event.get("pleaseNote")
            or event.get("description")
            or event.get("additionalInfo")
        )
        # Clean up whitespace if present
        if isinstance(long_description, str):
            long_description = long_description.strip()
        else:
            long_description = None

        # Short description logic
        if long_description:
            if len(long_description) <= 150:
                short_description = long_description
            else:
                short_description = long_description[:147].rstrip() + "..."
        else:
            short_description = None

        return EventData(
            title=event["name"],
            venue=venue_name,
            date=date,
            time=time,
            lineup=lineup,
            genres=genres,
            long_description=long_description,
            short_description=short_description,
            location=location,
            images=images,
            cost=cost,
            ticket_url=event.get("url"),
            source_url=url,
        )

    def _extract_search_info_from_url(self: TicketmasterAgent, url: str) -> dict:
        """Extract searchable information from a Ticketmaster URL using domain/source and path keywords."""
        import re
        from urllib.parse import urlparse

        search_info = {}
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        path = parsed.path.strip("/")

        # Use the 'source' parameter for documented sources
        source_mapping = {
            "universe.com": "universe",
            "frontgatetickets.com": "frontgate",
        }
        source_found = False
        for d, s in source_mapping.items():
            if d in domain:
                search_info["source"] = s
                source_found = True
                break

        # For other affiliates like TicketWeb, use the 'domain' parameter
        if not source_found:
            affiliate_domains = ["ticketweb.com", "livenation.com"]
            for d in affiliate_domains:
                if d in domain:
                    search_info["domain"] = d
                    break

        # Extract a keyword from the URL path, as it's often descriptive
        keyword_str = path

        # Remove '/event/' prefix if present
        if "/event/" in keyword_str:
            keyword_str = keyword_str.split("/event/")[1]

        # Clean up string for use as a keyword:
        # 1. Replace separators with spaces
        keyword_str = keyword_str.replace("-", " ").replace("/", " ")

        # 2. Remove long alphanumeric IDs (like TM event IDs)
        keyword_str = re.sub(r"\b[a-zA-Z0-9]{16,}\b", "", keyword_str)

        # 3. Remove any standalone numbers (likely affiliate event IDs)
        keyword_str = re.sub(r"\b\d+\b", "", keyword_str)

        # 4. Remove common unhelpful terms
        common_terms = ["tickets", "event", "detail", "purchase"]
        for term in common_terms:
            keyword_str = re.sub(rf"\b{term}\b", "", keyword_str, flags=re.IGNORECASE)

        # 5. Clean up whitespace and take the first 6 words for a concise keyword
        cleaned_words = keyword_str.split()
        if cleaned_words:
            search_info["keyword"] = " ".join(cleaned_words[:6])

        logger.info(f"Extracted search info from URL: {search_info}")
        return search_info

    async def _search_for_event(
        self: TicketmasterAgent, search_info: dict,
    ) -> dict | None:
        """Search for an event using the Discovery API search endpoint with domain/source filtering."""
        try:
            params = {
                "apikey": self.api_key,
                "size": 10,
                "sort": "date,asc",
            }
            if "keyword" in search_info:
                params["keyword"] = search_info["keyword"]
            if "domain" in search_info:
                params["domain"] = search_info["domain"]
            if "source" in search_info:
                params["source"] = search_info["source"]

            logger.info(f"Searching Discovery API with params: {params}")
            data = await self.http.get_json(
                f"{self.API_BASE}/events.json",
                service="Ticketmaster",
                params=params,
            )
            events = data.get("_embedded", {}).get("events", [])
            if not events:
                logger.info("No events found in search results")
                return None

            # Return the first result, which is the most likely match
            event = events[0]
            logger.info(
                f"Using first search result: {event.get('name')} (ID: {event.get('id')})",
            )
            return event
        except (ValueError, TypeError, KeyError):
            logger.exception(AgentMessages.DISCOVERY_API_ERROR)
            return None
