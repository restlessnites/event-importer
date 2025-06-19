"""URL analysis for event imports."""

import re
from typing import Dict, Any
from urllib.parse import urlparse, parse_qs
from enum import Enum


class URLType(str, Enum):
    """Supported URL types."""

    RESIDENT_ADVISOR = "resident_advisor"
    TICKETMASTER = "ticketmaster"
    DICE = "dice"
    UNKNOWN = "unknown" 


class URLAnalyzer:
    """Simple URL analyzer for routing."""

    def analyze(self, url: str) -> Dict[str, Any]:
        """
        Analyze a URL and return routing information.

        Returns:
            Dict with 'type' and any extracted metadata
        """
        # Ensure URL has a scheme
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urlparse(url.lower())
        domain = parsed.netloc.replace("www.", "")
        path = parsed.path

        # Check for Resident Advisor
        if domain in ["ra.co", "residentadvisor.net"]:
            # Extract event ID if present
            match = re.search(r"/events/(\d+)", path)
            if match:
                return {"type": URLType.RESIDENT_ADVISOR, "event_id": match.group(1)}

        # Ticketmaster and affiliates
        ticketmaster_domains = [
            "ticketmaster.com",
            "livenation.com",
            "frontgatetickets.com",
            "ticketweb.com",
        ]
        if any(domain in domain for domain in ticketmaster_domains):
            # Regex to find TM/LiveNation event IDs (alphanumeric with dashes)
            # Example: /event/G5vYZ9v1AUf-G
            match = re.search(r"/event/([a-zA-Z0-9-]{16,})", path)
            if match:
                return {"type": URLType.TICKETMASTER, "event_id": match.group(1)}

            # If no ID is found in the URL, that's okay. The agent can use search.
            return {"type": URLType.TICKETMASTER}

        # Check for Dice.fm
        if domain in ["dice.fm"]:
            # Dice URLs typically look like:
            # https://dice.fm/event/{id}-{slug}
            # or https://dice.fm/event/{slug}
            match = re.search(r"/event/([^/?]+)", path)
            if match:
                event_slug = match.group(1)
                
                # Try to extract ID if it's at the beginning of the slug
                # Format: {ID}-{slug} where ID is typically alphanumeric
                id_match = re.match(r"^([a-zA-Z0-9]{6,})-", event_slug)
                if id_match:
                    return {"type": URLType.DICE, "event_id": id_match.group(1), "slug": event_slug}
                else:
                    # Return as dice type but without extracted ID
                    # The agent will use the slug to search for the event ID via API
                    return {"type": URLType.DICE, "slug": event_slug}

        # Everything else is unknown (will be determined by content-type)
        return {"type": URLType.UNKNOWN}