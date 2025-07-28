"""Timezone utilities for event location detection."""

from __future__ import annotations

from typing import Any

from app.schemas import EventLocation

TIMEZONE_MAPPINGS = {
    "country_defaults": {
        "united states": "America/New_York",
        "usa": "America/New_York",
        "us": "America/New_York",
        "canada": "America/Toronto",
        "united kingdom": "Europe/London",
        "uk": "Europe/London",
    },
    "city_timezones": {
        # US Cities
        "los angeles": "America/Los_Angeles",
        "san francisco": "America/Los_Angeles",
        "seattle": "America/Los_Angeles",
        "las vegas": "America/Los_Angeles",
        "portland": "America/Los_Angeles",
        "san diego": "America/Los_Angeles",
        "chicago": "America/Chicago",
        "houston": "America/Chicago",
        "dallas": "America/Chicago",
        "austin": "America/Chicago",
        "new orleans": "America/Chicago",
        "new york": "America/New_York",
        "miami": "America/New_York",
        "atlanta": "America/New_York",
        "boston": "America/New_York",
        "washington": "America/New_York",
        "philadelphia": "America/New_York",
        "denver": "America/Denver",
        "salt lake city": "America/Denver",
        "phoenix": "America/Phoenix",
        # Canadian Cities
        "vancouver": "America/Vancouver",
        "calgary": "America/Edmonton",
        "montreal": "America/Montreal",
        # European Cities
        "berlin": "Europe/Berlin",
        "paris": "Europe/Paris",
        "amsterdam": "Europe/Amsterdam",
        "barcelona": "Europe/Madrid",
        "madrid": "Europe/Madrid",
        "rome": "Europe/Rome",
        "vienna": "Europe/Vienna",
        "zurich": "Europe/Zurich",
        "brussels": "Europe/Brussels",
        # Other Major Cities
        "tokyo": "Asia/Tokyo",
        "sydney": "Australia/Sydney",
        "melbourne": "Australia/Melbourne",
    },
}


def get_timezone_from_location(location: EventLocation | dict[str, Any] | None) -> str:
    """Determine timezone from location data for major cities worldwide.

    Args:
        location: EventLocation object or dictionary with city, state, country

    Returns:
        Timezone string in IANA format
    """
    if not location:
        return "UTC"

    if isinstance(location, EventLocation):
        city = (location.city or "").lower()
        country = (location.country or "").lower()
    else:
        city = (location.get("city") or "").lower()
        country = (location.get("country") or "").lower()

    if city in TIMEZONE_MAPPINGS["city_timezones"]:
        return TIMEZONE_MAPPINGS["city_timezones"][city]

    for country_key, timezone in TIMEZONE_MAPPINGS["country_defaults"].items():
        if country_key in country:
            return timezone

    return "UTC"
