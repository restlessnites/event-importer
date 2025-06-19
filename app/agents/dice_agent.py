"""Dice.fm agent using search API to find event ID and fetch data."""

import logging
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from app.shared.agent import Agent
from app.schemas import EventData, ImportMethod, ImportStatus, EventTime, EventLocation


logger = logging.getLogger(__name__)


class DiceAgent(Agent):
   """Agent for importing events from Dice.fm using search API."""

   def __init__(self, *args, **kwargs):
       super().__init__(*args, **kwargs)
       # Use shared services
       self.http = self.services["http"]

   @property
   def name(self) -> str:
       return "Dice"

   @property
   def import_method(self) -> ImportMethod:
       return ImportMethod.API

   async def import_event(self, url: str, request_id: str) -> Optional[EventData]:
       """Import event from Dice using search API to find event ID."""
       self.start_timer()

       try:
           await self.send_progress(
               request_id, ImportStatus.RUNNING, "Searching for event via Dice API", 0.2
           )
           
           # Extract search query from URL
           search_query = self._extract_search_query_from_url(url)
           logger.info(f"Generated search query: {search_query}")
           
           # Use unified search API to find the event
           event_id = await self._search_for_event_id(search_query)
           if not event_id:
               raise Exception("Could not find event using Dice search API")

           logger.info(f"Found Dice event ID: {event_id}")

           await self.send_progress(
               request_id, ImportStatus.RUNNING, "Fetching event data from Dice API", 0.6
           )

           # Step 2: Fetch event data from API using the extracted ID
           api_data = await self._fetch_api_data(event_id)
           if not api_data:
               raise Exception("Could not fetch event data from Dice API")

           await self.send_progress(
               request_id, ImportStatus.RUNNING, "Processing event data", 0.8
           )

           # Step 3: Transform API data to EventData
           event_data = self._transform_api_data(api_data, url)
           if not event_data:
               raise Exception("Could not transform Dice API data to event format")

           await self.send_progress(
               request_id,
               ImportStatus.SUCCESS,
               "Successfully imported from Dice API",
               1.0,
               data=event_data,
           )

           return event_data

       except Exception as e:
           logger.error(f"Dice import failed: {e}")
           await self.send_progress(
               request_id,
               ImportStatus.FAILED,
               f"Import failed: {str(e)}",
               1.0,
               error=str(e),
           )
           return None

   def _extract_search_query_from_url(self, url: str) -> str:
      """Extract search query from Dice URL."""
      slug = url.split('/event/')[-1] if '/event/' in url else ""
      
      # Remove first word (identifier) and take just the first few meaningful words
      words = slug.split('-')[1:] if '-' in slug else []
      
      # Just take the first 4 words max - this should be the event name
      return ' '.join(words[:4])

   async def _search_for_event_id(self, search_query: str) -> Optional[str]:
       """Search for event using Dice unified search API."""
       try:
           search_url = "https://api.dice.fm/unified_search"
           
           headers = {
               'Accept': 'application/json',
               'Accept-Language': 'en-US',
               'Content-Type': 'application/json',
               'Origin': 'https://dice.fm',
               'Referer': 'https://dice.fm/',
               'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
               'X-Api-Timestamp': '2024-03-25',
               'X-Client-Timezone': 'America/Los_Angeles',
           }
           
           payload = {"q": search_query}
           
           response = await self.http.post_json(
               search_url,
               service="Dice Search",
               headers=headers,
               json=payload,
               timeout=10
           )
           
           # Extract event ID from search results
           if "sections" in response:
               for section in response["sections"]:
                   if "items" in section:
                       for item in section["items"]:
                           if "event" in item:
                               event = item["event"]
                               return event.get("id")
           
           return None
           
       except Exception as e:
           logger.error(f"Dice search failed: {e}")
           return None

   async def _fetch_api_data(self, event_id: str) -> Optional[Dict[str, Any]]:
       """Fetch event data from Dice API."""
       try:
           # Use the ticket_types endpoint
           api_url = f"https://api.dice.fm/events/{event_id}/ticket_types"
           
           headers = {
               "Accept": "application/json",
               "Accept-Language": "en-US",
               "Cache-Control": "no-cache",
               "Origin": "https://dice.fm",
               "Referer": "https://dice.fm/",
               "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
               "X-Api-Timestamp": "2024-04-15",
               "X-Client-Timezone": "America/Los_Angeles",
           }
           
           response = await self.http.get_json(
               api_url,
               service="Dice API",
               headers=headers,
               timeout=30.0
           )
           
           return response
           
       except Exception as e:
           logger.error(f"Error fetching Dice API data: {e}")
           return None

   def _transform_api_data(self, api_data: Dict[str, Any], source_url: str) -> Optional[EventData]:
       """Transform Dice API response to EventData format."""
       try:
           # Extract main event information
           title = api_data.get("name", "")
           
           # Handle dates
           dates = api_data.get("dates", {})
           event_start = dates.get("event_start_date")
           event_end = dates.get("event_end_date")
           
           event_time = None
           if event_start:
               event_time = EventTime(
                   start=event_start,
                   end=event_end,
                   timezone=dates.get("timezone", "UTC")
               )

           # Handle venue information
           venues = api_data.get("venues", [])
           location = None
           venue_name = None
           
           if venues:
               venue = venues[0]  # Take first venue
               venue_name = venue.get("name")
               
               # Extract location details
               address = venue.get("address", "")
               city_info = venue.get("city", {})
               
               location = EventLocation(
                   venue=venue_name,
                   address=address,
                   city=city_info.get("name"),
                   state=None,  # Not provided in this format
                   country=city_info.get("country_name"),
                   coordinates=venue.get("location", {})
               )

           # Handle lineup
           lineup = []
           summary_lineup = api_data.get("summary_lineup", {})
           top_artists = summary_lineup.get("top_artists", [])
           
           for artist in top_artists:
               lineup.append(artist.get("name", ""))

           # Handle images
           images = api_data.get("images", {})
           image_dict = None
           if images:
               image_dict = {
                   "full": images.get("landscape") or images.get("square"),
                   "thumbnail": images.get("square") or images.get("portrait"),
               }

           # Handle ticket information and pricing
           ticket_types = api_data.get("ticket_types", [])
           ticket_url = source_url  # Use the original Dice URL
           
           # Extract price information
           price_info = None
           if ticket_types:
               # Get minimum price from available tickets
               prices = []
               for ticket in ticket_types:
                   if ticket.get("status") == "on-sale":
                       price = ticket.get("price", {})
                       amount = price.get("amount")
                       if amount:
                           prices.append(amount / 100)  # Convert from cents
               
               if prices:
                   min_price = min(prices)
                   price_info = {
                       "amount": min_price,
                       "currency": ticket_types[0].get("price", {}).get("currency", "USD")
                   }

           # Handle description and promoter info
           about = api_data.get("about", {})
           description = about.get("description", "")
           
           # Add presented by info if available
           presented_by = api_data.get("presented_by")
           if presented_by and not description:
               description = presented_by
           elif presented_by:
               description += f"\n\n{presented_by}"

           # Handle promoters
           promoters = []
           billing_promoter = api_data.get("billing_promoter", {})
           if billing_promoter.get("name"):
               promoters.append(billing_promoter["name"])

           # Create EventData
           event_data = EventData(
               title=title,
               description=description or None,
               lineup=lineup if lineup else None,
               time=event_time,
               location=location,
               ticket_url=ticket_url,
               source_url=source_url,
               images=image_dict,
               promoters=promoters if promoters else None,
               price=price_info,
               genres=None,  # Not provided in Dice API, could be enhanced later
           )

           return event_data

       except Exception as e:
           logger.error(f"Error transforming Dice API data: {e}")
           return None