"""TicketFairy transformer."""

from __future__ import annotations

import logging
from typing import Any

from app.shared.timezone import get_timezone_from_location

logger = logging.getLogger(__name__)


def _get_meaningful_url(url_value: str | None) -> str | None:
    """Check if a URL value is meaningful (not empty, None, or just whitespace)"""
    if not url_value:
        return None

    url_str = str(url_value).strip()
    if not url_str or url_str.lower() in ["n/a", "na", "none", "null", ""]:
        return None

    return url_str


def _format_list_or_string(data: list[str] | str | None) -> str:
    """Helper to format data that could be a list or a string."""
    if isinstance(data, list):
        return ", ".join(map(str, data))
    return str(data) if data is not None else ""


class TicketFairyTransformer:
    """Transforms a normalized event data dictionary into the format required
    by the TicketFairy API.
    """

    def _get_address(self: TicketFairyTransformer, location: dict[str, Any]) -> str:
        """Constructs a formatted address string from location data."""
        if not isinstance(location, dict):
            return "N/A"

        address_parts = [
            location.get("address"),
            location.get("city"),
            location.get("state"),
            location.get("country"),
        ]
        return ", ".join(part for part in address_parts if part) or "N/A"

    def _get_image_url(self: TicketFairyTransformer, images: dict[str, Any]) -> str:
        """Extracts the best available image URL."""
        if not isinstance(images, dict):
            return "N/A"
        return images.get("full") or images.get("thumbnail") or "N/A"

    def _get_ticket_url(
        self: TicketFairyTransformer,
        event_data: dict[str, Any],
    ) -> str:
        """Determines the most appropriate ticket URL."""
        ticket_url_raw = event_data.get("ticket_url")
        source_url_raw = event_data.get("source_url")

        return (
            _get_meaningful_url(ticket_url_raw)
            or _get_meaningful_url(source_url_raw)
            or "N/A"
        )

    def _get_datetimes(
        self: TicketFairyTransformer,
        event_data: dict[str, Any],
    ) -> tuple[str, str]:
        """Formats start and end datetimes for the API payload."""
        date_str = event_data.get("date", "")
        if not date_str:
            return "", ""

        end_date_str = event_data.get("end_date", date_str)
        time_obj = event_data.get("time", {})

        start_time = "00:00:00"
        end_time = "23:59:59"

        if isinstance(time_obj, dict):
            start_time = (
                f"{time_obj['start']}:00" if time_obj.get("start") else start_time
            )
            end_time = f"{time_obj['end']}:00" if time_obj.get("end") else end_time

        start_date = f"{date_str} {start_time}"
        end_date = f"{end_date_str} {end_time}"
        return start_date, end_date

    def _construct_details(
        self: TicketFairyTransformer,
        event_data: dict[str, Any],
    ) -> str:
        """Constructs the HTML 'details' field from various event data parts."""
        parts = []
        # Descriptions
        short_desc = event_data.get("short_description", "")
        long_desc = event_data.get("long_description", "")
        if short_desc:
            parts.append(short_desc)
        if long_desc and long_desc != short_desc:
            parts.append(long_desc)
        if not parts and event_data.get("content"):
            parts.append(event_data["content"])

        # Other fields
        if cost := event_data.get("cost"):
            parts.append(f"Cost: {cost}")
        list_fields = ["lineup", "promoters", "genres"]
        for field in list_fields:
            value = _format_list_or_string(event_data.get(field, []))
            if value:
                parts.append(f"{field.title()}: {value}")

        html_parts = [f"<p>{part}</p>" for part in parts if part]
        return "".join(html_parts) or "<p>N/A</p>"

    def transform(
        self: TicketFairyTransformer,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Transforms the scraped event data into the format expected by the
        TicketFairy /api/draft-events endpoint.
        """
        location = event_data.get("location", {})
        start_date, end_date = self._get_datetimes(event_data)

        return {
            "data": {
                "attributes": {
                    "title": event_data.get("title", "N/A"),
                    "url": self._get_ticket_url(event_data),
                    "image": self._get_image_url(event_data.get("images", {})),
                    "hostedBy": True,
                    "startDate": start_date,
                    "endDate": end_date,
                    "timezone": get_timezone_from_location(location),
                    "isOnline": 0,
                    "status": "Public",
                    "address": self._get_address(location),
                    "venue": event_data.get("venue", "N/A"),
                    "details": self._construct_details(event_data),
                },
            },
        }
