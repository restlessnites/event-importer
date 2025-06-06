"""URL analysis for event imports."""

import re
from typing import Dict, Any
from urllib.parse import urlparse
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
        parsed = urlparse(url.lower())
        domain = parsed.netloc.replace("www.", "")
        path = parsed.path

        # Check for Resident Advisor
        if domain == "ra.co":
            # Extract event ID if present
            match = re.search(r"/events/(\d+)", path)
            if match:
                return {"type": URLType.RESIDENT_ADVISOR, "event_id": match.group(1)}

        # Check for Ticketmaster family
        if any(
            domain.endswith(d)
            for d in ["ticketmaster.com", "livenation.com", "ticketweb.com"]
        ):
            # Extract event ID (16 hex chars)
            match = re.search(r"/event/([0-9A-Fa-f]{16})", url)
            if match:
                return {"type": URLType.TICKETMASTER, "event_id": match.group(1)}

        # Everything else is unknown (will be determined by content-type)
        return {"type": URLType.UNKNOWN}
