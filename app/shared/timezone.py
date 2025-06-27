"""Timezone utilities for event location detection."""

from __future__ import annotations

from typing import Any

from app.schemas import EventLocation


def get_timezone_from_location(location: EventLocation | dict[str, Any] | None) -> str:
    """Determine timezone from location data for major cities worldwide.

    Args:
        location: EventLocation object or dictionary with city, state, country

    Returns:
        Timezone string in IANA format
    """
    if not location:
        return "UTC"

    # Handle both EventLocation objects and dicts
    if hasattr(location, 'city'):
        city = getattr(location, 'city', None) or ""
        country = getattr(location, 'country', None) or ""
    else:
        city = (location.get("city") or "").lower() if isinstance(location, dict) else ""
        country = (location.get("country") or "").lower() if isinstance(location, dict) else ""

    city = city.lower()
    country = country.lower()

    # US timezone mapping
    if "united states" in country or "usa" in country or country == "us":
        pacific_cities = [
            "los angeles", "san francisco", "seattle", "las vegas", "portland", "san diego"
        ]
        central_cities = ["chicago", "houston", "dallas", "austin", "new orleans"]
        eastern_cities = [
            "new york", "miami", "atlanta", "boston", "washington", "philadelphia"
        ]
        mountain_cities = ["denver", "salt lake city"]

        if city in pacific_cities:
            return "America/Los_Angeles"
        if city in central_cities:
            return "America/Chicago"
        if city in eastern_cities:
            return "America/New_York"
        if city in mountain_cities:
            return "America/Denver"
        if city == "phoenix":
            return "America/Phoenix"  # Special case - no DST
        return "America/New_York"  # Default to Eastern

    # Canada
    if "canada" in country:
        if city == "vancouver":
            return "America/Vancouver"
        if city == "calgary":
            return "America/Edmonton"
        if city == "montreal":
            return "America/Montreal"
        return "America/Toronto"  # Default

    # UK
    if "united kingdom" in country or "uk" in country:
        return "Europe/London"

    # Europe
    european_cities = {
        "berlin": "Europe/Berlin",
        "paris": "Europe/Paris",
        "amsterdam": "Europe/Amsterdam",
        "barcelona": "Europe/Madrid",
        "madrid": "Europe/Madrid",
        "rome": "Europe/Rome",
        "vienna": "Europe/Vienna",
        "zurich": "Europe/Zurich",
        "brussels": "Europe/Brussels",
    }
    if city in european_cities:
        return european_cities[city]

    # Major international cities
    if city == "tokyo":
        return "Asia/Tokyo"
    if city == "sydney":
        return "Australia/Sydney"
    if city == "melbourne":
        return "Australia/Melbourne"

    return "UTC"