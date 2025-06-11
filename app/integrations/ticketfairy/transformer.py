from typing import Dict, Any, List
import logging

from ..base import BaseTransformer

logger = logging.getLogger(__name__)

def _get_meaningful_url(url_value):
    """Check if a URL value is meaningful (not empty, None, or just whitespace)"""
    if not url_value:
        return None
    
    url_str = str(url_value).strip()
    if not url_str or url_str.lower() in ['n/a', 'na', 'none', 'null', '']:
        return None

def _format_list_or_string(data: Any) -> str:
    """Helper to format data that could be a list or a string."""
    if isinstance(data, list):
        return ", ".join(map(str, data))
    return str(data) if data is not None else ""

def _get_timezone_from_location(location: Dict[str, Any]) -> str:
    """
    Determine timezone from location data for major cities in US, Canada, and UK.
    
    Args:
        location: Location dictionary with city, state, country
        
    Returns:
        Timezone string for TicketFairy
    """
    if not isinstance(location, dict):
        return "UTC"
    
    city = (location.get("city") or "").lower()
    country = (location.get("country") or "").lower()
    
    # US timezone mapping
    if "united states" in country:
        pacific_cities = ["los angeles", "san francisco", "seattle", "las vegas", "portland", "san diego"]
        central_cities = ["chicago", "houston", "dallas", "austin", "new orleans"]
        eastern_cities = ["new york", "miami", "atlanta", "boston", "washington", "philadelphia"]
        mountain_cities = ["denver", "salt lake city"]
        
        if city in pacific_cities:
            return "America/Los_Angeles"
        elif city in central_cities:
            return "America/Chicago" 
        elif city in eastern_cities:
            return "America/New_York"
        elif city in mountain_cities:
            return "America/Denver"
        elif city == "phoenix":
            return "America/Phoenix"  # Special case - no DST
        else:
            return "America/New_York"  # Default to Eastern
    
    # Canada
    elif "canada" in country:
        if city == "vancouver":
            return "America/Vancouver"
        elif city == "calgary":
            return "America/Edmonton" 
        elif city == "montreal":
            return "America/Montreal"
        else:
            return "America/Toronto"  # Default
    
    # UK
    elif "united kingdom" in country:
        return "Europe/London"
    
    return "UTC"

class TicketFairyTransformer(BaseTransformer):
    """
    Transforms a normalized event data dictionary into the format required
    by the TicketFairy API.
    """

    def transform(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms the scraped event data into the format expected by the
        TicketFairy /api/draft-events endpoint.
        
        Actual canonical event data fields used in this system:
        - title (required)
        - venue
        - long_description
        - short_description  
        - location: {address, city, state, country}
        - images: {full, thumbnail}
        - ticket_url
        - date (ISO date)
        - time: {start, end} (HH:MM format)
        - lineup (list)
        - promoters (list)
        - genres (list)
        """
        
        # --- Extract data using correct canonical keys ---
        title = event_data.get("title", "N/A")
        
        # Handle venue
        venue = event_data.get("venue", "N/A")
        
        # Handle location/address - build from available location data
        location = event_data.get("location", {})
        address = "N/A"
        if isinstance(location, dict):
            address_parts = []
            if location.get("address"):
                address_parts.append(location["address"])
            if location.get("city"):
                address_parts.append(location["city"])
            if location.get("state"):
                address_parts.append(location["state"])
            if location.get("country"):
                address_parts.append(location["country"])
            
            if address_parts:
                address = ", ".join(address_parts)
            else:
                address = "N/A"
            
        # Handle images
        image_url = "N/A"
        images = event_data.get("images", {})
        if isinstance(images, dict):
            image_url = images.get("full") or images.get("thumbnail") or "N/A"
        
        # Handle ticket URL with proper fallback
        ticket_url_raw = event_data.get("ticket_url")
        source_url_raw = event_data.get("source_url") 

        ticket_url = (_get_meaningful_url(ticket_url_raw) or 
                      _get_meaningful_url(source_url_raw) or 
                      "N/A")
        
        # Handle datetime - combine date and time into TicketFairy format
        # Determine timezone from location
        timezone = _get_timezone_from_location(location)
        
        start_date = ""
        end_date = ""
        
        date_str = event_data.get("date", "")  # ISO format YYYY-MM-DD
        time_obj = event_data.get("time", {})
        
        if date_str:
            start_time = "00:00:00"  # Default time
            end_time = "23:59:59"    # Default end time
            
            if isinstance(time_obj, dict):
                if time_obj.get("start"):
                    start_time = f"{time_obj['start']}:00"  # Convert HH:MM to HH:MM:SS
                if time_obj.get("end"):
                    end_time = f"{time_obj['end']}:00"    # Convert HH:MM to HH:MM:SS
            
            start_date = f"{date_str} {start_time}"
            end_date = f"{date_str} {end_time}"

        # Handle lists - using actual canonical field names
        lineup = _format_list_or_string(event_data.get("lineup", []))
        promoters = _format_list_or_string(event_data.get("promoters", []))
        genres = _format_list_or_string(event_data.get("genres", []))

        # --- Combine details into a single field ---
        details_parts = []
        
        # Add short description first if available
        short_desc = event_data.get("short_description", "")
        if short_desc:
            details_parts.append(short_desc)
        
        # Add long description if available and different from short
        long_desc = event_data.get("long_description", "")
        if long_desc:
            if not short_desc or long_desc != short_desc:
                details_parts.append(long_desc)
        
        # If we have no descriptions at all, try alternative field names  
        if not details_parts:
            content = event_data.get("content", "")
            if content:
                details_parts.append(content)

        # Add cost if available
        cost = event_data.get("cost", "")
        if cost:
            details_parts.append(f"Cost: {cost}")
            
        # Add additional info
        if lineup:
            details_parts.append(f"Lineup: {lineup}")
        if promoters:
            details_parts.append(f"Promoters: {promoters}")
        if genres:
            details_parts.append(f"Genres: {genres}")
        
        # Join with HTML paragraph tags for TinyMCE
        details_parts_html = [f"<p>{part}</p>" for part in filter(None, details_parts)]
        details = "".join(details_parts_html) or "<p>N/A</p>"

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
                    "timezone": timezone,
                    "isOnline": 0,
                    "status": "Public",
                    "address": address,
                    "venue": venue,
                    "details": details,
                }
            }
        }