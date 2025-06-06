"""URL analysis for event imports."""

import re
from typing import Dict, Any
from urllib.parse import urlparse, parse_qs
from enum import Enum


class URLType(str, Enum):
    """Supported URL types."""

    RESIDENT_ADVISOR = "resident_advisor"
    TICKETMASTER = "ticketmaster"
    UNKNOWN = "unknown"  # Everything else


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

        # Check for Ticketmaster family
        if any(
            domain.endswith(d)
            for d in [
                "ticketmaster.com",
                "ticketmaster.ca",
                "ticketmaster.co.uk",
                "livenation.com",
                "ticketweb.com",
            ]
        ):
            # Try to extract event ID from path first
            path_match = re.search(r"/event/([0-9A-Fa-f]{16})", url)
            if path_match:
                return {"type": URLType.TICKETMASTER, "event_id": path_match.group(1)}

            # Also check query parameters
            query_params = parse_qs(parsed.query)
            if "id" in query_params and query_params["id"]:
                event_id = query_params["id"][0]
                # Validate it looks like a TM event ID
                if re.match(r"^[0-9A-Fa-f]{16}$", event_id):
                    return {"type": URLType.TICKETMASTER, "event_id": event_id}

        # Everything else is unknown (will be determined by content-type)
        return {"type": URLType.UNKNOWN}
