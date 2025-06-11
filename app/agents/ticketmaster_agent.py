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
        """Import event from Ticketmaster API."""
        self.start_timer()

        # Extract event ID
        analysis = self.url_analyzer.analyze(url)
        event_id = analysis.get("event_id")
        if not event_id:
            return None

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            f"Fetching event {event_id} from Ticketmaster API",
            0.3,
        )

        try:
            # Fetch event data
            event_json = await self._fetch_event(event_id)
            if not event_json:
                raise Exception("Event not found in API")

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

            # Generate descriptions if missing using Claude
            if not event_data.long_description or not event_data.short_description:
                await self.send_progress(
                    request_id, ImportStatus.RUNNING, "Generating descriptions", 0.85
                )
                event_data = await self.claude.generate_descriptions(event_data)

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
        """Parse Ticketmaster event data to our schema."""
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

        return EventData(
            title=event["name"],
            venue=venue_name,
            date=date,
            time=time,
            lineup=lineup,
            genres=genres,
            long_description=event.get("info"),
            short_description=None,  # Will be generated by Claude if needed
            location=location,
            images=images,
            cost=cost,
            ticket_url=event.get("url"),
            source_url=url,
        )
