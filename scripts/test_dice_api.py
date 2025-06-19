#!/usr/bin/env -S uv run python
"""Clean test of Dice unified search API."""

import asyncio
import logging
from app.shared.http import get_http_service, close_http_service

async def test_dice_search_clean():
    """Test just the Dice search API cleanly."""
    
    url = "https://dice.fm/event/l86kmr-framework-presents-paradise-los-angeles-25th-oct-the-dock-at-the-historic-sears-building-los-angeles-tickets"
    
    print("🔍 Testing Dice unified search API")
    print(f"URL: {url}")
    print()
    
    http = get_http_service()
    
    try:
        # Extract search query
        slug = url.split('/event/')[-1]
        words = slug.split('-')[1:]  # Skip first word (l86kmr)
        query = ' '.join(words[:4])  # First 4 words only
        
        print(f"Search query: '{query}'")
        
        # Call search API
        search_url = "https://api.dice.fm/unified_search"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Origin': 'https://dice.fm',
            'Referer': 'https://dice.fm/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        }
        
        response = await http.post_json(
            search_url,
            service="Dice Search",
            headers=headers,
            json={"q": query}
        )
        
        # Find matching event
        for section in response.get("sections", []):
            for item in section.get("items", []):
                if "event" in item:
                    event = item["event"]
                    perm_name = event.get("perm_name", "")
                    if "l86kmr" in perm_name:  # Our event
                        event_id = event.get("id")
                        print(f"✅ Found event: {event.get('name')}")
                        print(f"🆔 Event ID: {event_id}")
                        
                        # Test API call
                        api_url = f"https://api.dice.fm/events/{event_id}/ticket_types"
                        api_response = await http.get_json(api_url, service="Dice API")
                        print(f"🎯 API successful: {api_response.get('name')}")
                        return
        
        print("❌ Event not found")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
    finally:
        await close_http_service()

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(test_dice_search_clean())