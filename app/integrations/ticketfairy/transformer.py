import json
from typing import Dict, Any
from datetime import datetime

from ..base import BaseTransformer


class TicketFairyTransformer(BaseTransformer):
    """Transform event data to TicketFairy API format"""
    
    def __init__(self):
        # TicketFairy template based on the provided JSON
        self.template = {
            "data": {
                "longDescription": {
                    "en": "{long_description}\n\nPromoters: {promoters}, Genres: {event_genre}\n\nLineup: {lineup}\n\nTicket price: {ticket_price}"
                },
                "shortDescription": {
                    "en": "{short_description}"
                },
                "externalTicketingUrl": "{ticket_url}",
                "minimumAge": "{minimum_age}",
                "displayName": "{title}",
                "imageURLs": {
                    "en": "{event_image_url}"
                },
                "startDate": "{datetime_ISO8601_UTC}",
                "endDate": "{datetime_ISO8601_UTC}",
                "searchValue": "{venue}"
            }
        }
    
    def transform(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform scraped event data to TicketFairy format"""
        
        # Extract values with fallbacks
        title = event_data.get("title", "")
        long_description = event_data.get("description", event_data.get("long_description", ""))
        short_description = event_data.get("short_description", title)
        
        # Handle lineup/artists
        lineup = ""
        if "lineup" in event_data:
            if isinstance(event_data["lineup"], list):
                lineup = ", ".join(event_data["lineup"])
            else:
                lineup = str(event_data["lineup"])
        elif "artists" in event_data:
            if isinstance(event_data["artists"], list):
                lineup = ", ".join(event_data["artists"])
            else:
                lineup = str(event_data["artists"])
        
        # Handle promoters
        promoters = ""
        if "promoters" in event_data:
            if isinstance(event_data["promoters"], list):
                promoters = ", ".join(event_data["promoters"])
            else:
                promoters = str(event_data["promoters"])
        
        # Handle genres
        event_genre = ""
        if "genres" in event_data:
            if isinstance(event_data["genres"], list):
                event_genre = ", ".join(event_data["genres"])
            else:
                event_genre = str(event_data["genres"])
        elif "genre" in event_data:
            event_genre = str(event_data["genre"])
        
        # Handle datetime
        datetime_iso = ""
        if "datetime" in event_data:
            try:
                # Try to parse and format as ISO8601 UTC
                if isinstance(event_data["datetime"], str):
                    # Assume it's already in ISO format or parse it
                    datetime_iso = event_data["datetime"]
                elif isinstance(event_data["datetime"], datetime):
                    datetime_iso = event_data["datetime"].isoformat() + "Z"
            except Exception:
                datetime_iso = ""
        
        # Handle ticket price
        ticket_price = ""
        if "ticket_price" in event_data:
            ticket_price = str(event_data["ticket_price"])
        elif "price" in event_data:
            ticket_price = str(event_data["price"])
        
        # Create the transformed data
        transformed = {
            "data": {
                "longDescription": {
                    "en": f"{long_description}\n\nPromoters: {promoters}, Genres: {event_genre}\n\nLineup: {lineup}\n\nTicket price: {ticket_price}"
                },
                "shortDescription": {
                    "en": short_description
                },
                "externalTicketingUrl": event_data.get("ticket_url", event_data.get("url", "")),
                "minimumAge": str(event_data.get("minimum_age", event_data.get("age_restriction", ""))),
                "displayName": title,
                "imageURLs": {
                    "en": event_data.get("image_url", event_data.get("event_image_url", ""))
                },
                "startDate": datetime_iso,
                "endDate": datetime_iso,  # Same as start date for now
                "searchValue": event_data.get("venue", event_data.get("location", ""))
            }
        }
        
        return transformed 