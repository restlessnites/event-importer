"""Genre enhancement service using web search and Claude."""

import logging
import json
import re
from typing import List, Optional, Dict, Any

from app.config import Config
from app.http import HTTPService
from app.services.claude import ClaudeService
from app.data.genres import MusicGenres
from app.prompts import GenrePrompts
from app.schemas import EventData
from app.errors import retry_on_error


logger = logging.getLogger(__name__)


class GenreService:
    """Service for enhancing events with missing genre information."""

    def __init__(
        self, config: Config, http_service: HTTPService, claude_service: ClaudeService
    ):
        """Initialize genre service."""
        self.config = config
        self.http = http_service
        self.claude = claude_service
        self.google_enabled = bool(
            config.api.google_api_key and config.api.google_cse_id
        )

        if not self.google_enabled:
            logger.debug(
                "Genre enhancement disabled - Google Search API not configured"
            )

    async def enhance_genres(self, event_data: EventData) -> EventData:
        """
        Enhance event with missing genre information.

        Only searches if:
        1. No genres are present
        2. We have artists to search for
        3. Google search is enabled
        """
        # Check if we need to search
        if event_data.genres or not event_data.lineup or not self.google_enabled:
            return event_data

        logger.info(f"Searching for genres for event: {event_data.title}")

        # Try to find genres for the main artist
        primary_artist = event_data.lineup[0]

        try:
            found_genres = await self._search_artist_genres(
                primary_artist, self._build_event_context(event_data)
            )

            if found_genres:
                # Validate and normalize genres
                validated = MusicGenres.validate_genres(found_genres)
                if validated:
                    event_data.genres = validated[:4]  # Limit to 4 genres
                    logger.info(f"Enhanced event with genres: {event_data.genres}")

        except Exception as e:
            logger.warning(f"Genre enhancement failed for {primary_artist}: {e}")

        return event_data

    def _build_event_context(self, event_data: EventData) -> Dict[str, Any]:
        """Build context dict for genre search."""
        context = {
            "title": event_data.title,
            "lineup": event_data.lineup,
        }

        if event_data.venue:
            context["venue"] = event_data.venue
        if event_data.date:
            context["date"] = event_data.date

        return context

    @retry_on_error(max_attempts=2)
    async def _search_artist_genres(
        self, artist_name: str, event_context: Dict[str, Any]
    ) -> List[str]:
        """Search for an artist's genres using Google and Claude."""

        # Build search query
        query = f'"{artist_name}" music genre artist'
        logger.debug(f"Searching for artist genres: {query}")

        try:
            # Search Google
            search_results = await self._google_search(query)
            if not search_results:
                return []

            # Extract text from results
            search_text = self._extract_search_text(search_results)

            # Use Claude to analyze and extract genres
            genres = await self._extract_genres_with_claude(
                artist_name, search_text, event_context
            )

            return genres

        except Exception as e:
            logger.error(f"Failed to search genres for {artist_name}: {e}")
            return []

    async def _google_search(self, query: str) -> List[Dict[str, Any]]:
        """Execute Google search for artist information."""
        params = {
            "key": self.config.api.google_api_key,
            "cx": self.config.api.google_cse_id,
            "q": query,
            "num": 5,  # Just need a few good results
        }

        response = await self.http.get_json(
            "https://www.googleapis.com/customsearch/v1",
            service="Google",
            params=params,
            timeout=10,
        )

        return response.get("items", [])

    def _extract_search_text(self, results: List[Dict[str, Any]]) -> str:
        """Extract relevant text from search results."""
        texts = []

        for item in results[:3]:  # Top 3 results
            parts = []

            if item.get("title"):
                parts.append(f"Title: {item['title']}")

            if item.get("snippet"):
                parts.append(f"Description: {item['snippet']}")

            if item.get("displayLink"):
                parts.append(f"Source: {item['displayLink']}")

            if parts:
                texts.append("\n".join(parts))

        return "\n\n---\n\n".join(texts)

    async def _extract_genres_with_claude(
        self, artist_name: str, search_text: str, event_context: Dict[str, Any]
    ) -> List[str]:
        """Use Claude to verify artist and extract genres."""

        # Build prompt using centralized prompt builder
        prompt = GenrePrompts.build_artist_verification_prompt(
            artist_name, search_text, event_context
        )

        try:
            # Use Claude's analyze method
            response = await self.claude.analyze_text(prompt)

            if response:
                # Extract JSON array from response
                genres = self._parse_genre_response(response)
                return genres

            return []

        except Exception as e:
            logger.error(f"Claude genre extraction failed for {artist_name}: {e}")
            return []

    def _parse_genre_response(self, response: str) -> List[str]:
        """Parse Claude's response to extract genre list."""
        try:
            # Look for JSON array in response
            match = re.search(r"\[.*?\]", response, re.DOTALL)
            if match:
                genres = json.loads(match.group())
                # Validate they're strings
                return [g for g in genres if isinstance(g, str) and g.strip()]

            return []

        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"Failed to parse genre response: {e}")
            return []
