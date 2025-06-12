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
        self.claude = self.services["claude"]
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
        """Extract searchable information from a Ticketmaster URL (robust version)."""
        import re
        from urllib.parse import urlparse
        search_info = {}
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # For Ticketmaster URLs, the format is usually:
        # /event-slug/event/EVENT_ID
        if "/event/" in path:
            parts = path.split("/event/")
            if len(parts) >= 2:
                event_slug = parts[0].split("/")[-1]  # Get the last part before /event/
            else:
                event_slug = path
        else:
            path_parts = path.split("/")
            event_slug = path_parts[-1] if path_parts else ""

        # Try to extract date (format: MM-DD-YYYY)
        date_pattern = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
        date_match = date_pattern.search(event_slug)
        if date_match:
            month, day, year = date_match.groups()
            search_info["startDate"] = f"{year}-{month}-{day}"
            # Remove date from slug for keyword extraction
            date_str = date_match.group(0)
            event_slug = event_slug.replace(date_str, " ")

        # State name to code mapping
        STATE_ABBR = {
            "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
            "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
            "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
            "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA",
            "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
            "nebraska": "NE", "nevada": "NV", "new-hampshire": "NH", "new-jersey": "NJ", "new-mexico": "NM",
            "new-york": "NY", "north-carolina": "NC", "north-dakota": "ND", "ohio": "OH", "oklahoma": "OK",
            "oregon": "OR", "pennsylvania": "PA", "rhode-island": "RI", "south-carolina": "SC", "south-dakota": "SD",
            "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
            "west-virginia": "WV", "wisconsin": "WI", "wyoming": "WY", "district-of-columbia": "DC"
        }
        slug_lower = event_slug.lower()
        for state_name, state_code in STATE_ABBR.items():
            if state_name in slug_lower or state_name.replace("-", "") in slug_lower.replace("-", ""):
                search_info["stateCode"] = state_code
                event_slug = (
                    event_slug.lower()
                    .replace(state_name, " ")
                    .replace(state_name.replace("-", ""), " ")
                )
                break

        # Clean up the remaining slug for keyword
        keyword_parts = []
        for part in event_slug.split("-"):
            # Skip common words, cities, and very short parts
            if len(part) > 2 and part.lower() not in {
                "the", "and", "tour", "show", "concert", "event", "good", "vibes", "only",
                "inglewood", "los", "angeles"
            }:
                keyword_parts.append(part)
        if keyword_parts:
            search_info["keyword"] = " ".join(keyword_parts[:3])

        logger.info(f"Extracted search info from URL: {search_info}")
        return search_info if search_info else {}

    async def _search_for_event(self, search_info: dict) -> Optional[dict]:
        """Search for an event using the Discovery API search endpoint (robust version)."""
        try:
            params = {
                "apikey": self.api_key,
                "size": 10,
                "sort": "date,asc",
            }
            if "keyword" in search_info:
                # Use hyphens in keywords for better results
                params["keyword"] = search_info["keyword"].replace(" ", "-")
            if "startDate" in search_info:
                params["startDate"] = search_info["startDate"]
            if "stateCode" in search_info:
                params["stateCode"] = search_info["stateCode"]

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
            # If we have a date, try to find the exact match
            if "startDate" in search_info and len(events) > 1:
                search_date = search_info["startDate"]
                for event in events:
                    if (
                        event.get("dates", {}).get("start", {}).get("localDate")
                        == search_date
                    ):
                        logger.info(
                            f"Found exact date match: {event.get('name')} (ID: {event.get('id')})"
                        )
                        return event
            # Otherwise, return the first result
            event = events[0]
            logger.info(
                f"Using first search result: {event.get('name')} (ID: {event.get('id')})"
            )
            return event
        except Exception as e:
            logger.error(f"Error searching Discovery API: {e}")
            return None
