from typing import Dict, Any, List

from ..base import BaseTransformer

def _format_list_or_string(data: Any) -> str:
    """Helper to format data that could be a list or a string."""
    if isinstance(data, list):
        return ", ".join(map(str, data))
    return str(data) if data is not None else ""

class TicketFairyTransformer(BaseTransformer):
    """
    Transforms a normalized event data dictionary into the format required
    by the TicketFairy API.
    """

    def transform(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms the scraped event data into the format expected by the
        TicketFairy /api/draft-events endpoint.
        """
        
        # --- Extract data using canonical keys ---
        title = event_data.get("title", "N/A")
        description = event_data.get("description", "")
        venue = event_data.get("venue", "N/A")
        address = event_data.get("address", "N/A")
        image_url = event_data.get("image_url", "N/A")
        ticket_url = event_data.get("url", "N/A")
        
        start_date = event_data.get("datetime_utc", "")
        end_date = event_data.get("end_datetime_utc", start_date)

        lineup = _format_list_or_string(event_data.get("lineup", []))
        promoters = _format_list_or_string(event_data.get("promoters", []))
        genres = _format_list_or_string(event_data.get("genres", []))

        # --- Combine details into a single field ---
        details_parts = [description]
        if lineup:
            details_parts.append(f"Lineup: {lineup}")
        if promoters:
            details_parts.append(f"Promoters: {promoters}")
        if genres:
            details_parts.append(f"Genres: {genres}")
        
        details = "\n\n".join(filter(None, details_parts)) or "N/A"

        # --- Construct the final payload ---
        return {
            "data": {
                "attributes": {
                    "title": title,
                    "url": ticket_url,
                    "image": image_url,
                    "hostedBy": True,
                    "startDate": start_date,
                    "endDate": end_date,
                    "timezone": "UTC",
                    "isOnline": 0,
                    "status": "Public",
                    "address": address,
                    "venue": venue,
                    "details": details,
                }
            }
        } 