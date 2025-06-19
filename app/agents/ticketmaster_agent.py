"""Ticketmaster Discovery API agent."""

import logging
from typing import Optional

from app.shared.agent import Agent
from app.schemas import EventData, ImportMethod, ImportStatus, EventTime, EventLocation
from app.shared.url_analyzer import URLAnalyzer


logger = logging.getLogger(__name__)


class TicketmasterAgent(Agent):
    """Agent for importing events from Ticketmaster."""

    API_BASE = "https://app.ticketmaster.com/discovery/v2"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url_analyzer = URLAnalyzer()
        # Use shared services
        self.http = self.services["http"]
        self.api_key = self.config.api.ticketmaster_key

    @property
    def name(self) -> str:
        return "Ticketmaster"

    @property
    def import_method(self) -> ImportMethod:
        return ImportMethod.API

    async def import_event(self, url: str, request_id: str) -> Optional[EventData]:
        """Import event from Ticketmaster API using search as the default method."""
        self.start_timer()

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            f"Extracting search info from URL for Ticketmaster Discovery API",
            0.2,
        )

        try:
            # Always extract search info from URL
            search_info = self._extract_search_info_from_url(url)
            event_json = None
            event_id = None

            if search_info:
                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    f"Searching Ticketmaster Discovery API for event...",
                    0.3,
                )
                event_json = await self._search_for_event(search_info)
                if event_json and event_json.get("id"):
                    event_id = event_json["id"]

            # If search failed, try extracting event ID from URL and fetch directly
            if not event_json:
                analysis = self.url_analyzer.analyze(url)
                event_id = analysis.get("event_id")
                if event_id:
                    await self.send_progress(
                        request_id,
                        ImportStatus.RUNNING,
                        f"Searching failed, trying direct fetch by event ID {event_id}",
                        0.5,
                    )
                    event_json = await self._fetch_event(event_id)

            if not event_json:
                raise Exception("Event not found in Ticketmaster Discovery API (search and direct fetch failed)")

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

            # Generate descriptions if missing using LLMService fallback
            if not event_data.long_description or not event_data.short_description:
                await self.send_progress(
                    request_id, ImportStatus.RUNNING, "Generating descriptions", 0.85
                )
                event_data = await self.services["llm"].generate_descriptions(event_data)

            await self.send_progress(
                request_id,
                ImportStatus.SUCCESS,
                "Successfully imported event",
                1.0,
                data=event_data,
            )

            return event_data

        except Exception as e:
            logger.error(f"Ticketmaster import failed: {e}")
            await self.send_progress(
                request_id,
                ImportStatus.FAILED,
                f"Import failed: {str(e)}",
                1.0,
                error=str(e),
            )
            return None

    async def _fetch_event(self, event_id: str) -> Optional[dict]:
        """Fetch event from Discovery API."""
        try:
            data = await self.http.get_json(
                f"{self.API_BASE}/events/{event_id}.json",
                service="Ticketmaster",
                params={"apikey": self.api_key},
            )
            return data
        except Exception as e:
            # Try searching if direct fetch fails
            logger.info(f"Direct fetch failed, trying search")
            return None

    def _parse_event(self, event: dict, url: str) -> EventData:
        """Parse Ticketmaster event data to our schema, with robust description extraction."""
        # Extract date and time
        date = None
        time = None
        if event.get("dates", {}).get("start"):
            start = event["dates"]["start"]
            if start.get("localDate"):
                date = start["localDate"]
            if start.get("localTime"):
                time = EventTime(start=start["localTime"])

        # Extract venue and location
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
                event["images"], key=lambda x: int(x.get("width", 0)), reverse=True
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

    def _extract_search_info_from_url(self, url: str) -> dict:
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
        keyword_str = re.sub(r'\b[a-zA-Z0-9]{16,}\b', '', keyword_str)
        
        # 3. Remove any standalone numbers (likely affiliate event IDs)
        keyword_str = re.sub(r'\b\d+\b', '', keyword_str)
        
        # 4. Remove common unhelpful terms
        common_terms = ["tickets", "event", "detail", "purchase"]
        for term in common_terms:
            keyword_str = re.sub(rf'\b{term}\b', '', keyword_str, flags=re.IGNORECASE)
            
        # 5. Clean up whitespace and take the first 6 words for a concise keyword
        cleaned_words = keyword_str.split()
        if cleaned_words:
            search_info["keyword"] = " ".join(cleaned_words[:6])

        logger.info(f"Extracted search info from URL: {search_info}")
        return search_info

    async def _search_for_event(self, search_info: dict) -> Optional[dict]:
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
                f"Using first search result: {event.get('name')} (ID: {event.get('id')})"
            )
            return event
        except Exception as e:
            logger.error(f"Error searching Discovery API: {e}")
            return None
