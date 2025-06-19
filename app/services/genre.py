"""Genre enhancement service using web search and LLMs."""

import json
import logging
import re
from typing import Any

from app.config import Config
from app.genres import MusicGenres
from app.errors import retry_on_error
from app.prompts import GenrePrompts
from app.schemas import EventData
from app.services.llm import LLMService
from app.shared.http import HTTPService

logger = logging.getLogger(__name__)


class GenreService:
    """Service for enhancing events with missing genre information."""

    def __init__(
        self: "GenreService",
        config: Config,
        http_service: HTTPService,
        llm_service: LLMService,
    ) -> None:
        """Initialize genre service."""
        self.config = config
        self.http = http_service
        self.llm = llm_service
        self.api_key = self.config.api.google_api_key
        self.cse_id = self.config.api.google_cse_id
        self.google_enabled = bool(self.api_key and self.cse_id)

        if not self.google_enabled:
            logger.debug(
                "Genre enhancement disabled - Google Search API not configured"
            )

    async def enhance_genres(self: "GenreService", event_data: EventData) -> EventData:
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

    def _build_event_context(
        self: "GenreService", event_data: EventData
    ) -> dict[str, Any]:
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
        self: "GenreService", artist_name: str, event_context: dict[str, Any]
    ) -> list[str]:
        """Search for an artist's genres using Google and an LLM."""

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

            # Use LLM to analyze and extract genres
            genres = await self._extract_genres_with_llm(
                artist_name, search_text, event_context
            )

            return genres

        except Exception as e:
            logger.error(f"Failed to search genres for {artist_name}: {e}")
            return []

    async def _google_search(self: "GenreService", query: str) -> list[dict[str, Any]]:
        """Execute Google search for artist information."""
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
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

    def _extract_search_text(
        self: "GenreService", results: list[dict[str, Any]]
    ) -> str:
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

    async def _extract_genres_with_llm(
        self: "GenreService",
        artist_name: str,
        search_text: str,
        event_context: dict[str, Any],
    ) -> list[str]:
        """Use LLM to extract genres from search text."""
        prompt = GenrePrompts.build_artist_verification_prompt(
            artist_name, search_text, event_context
        )
        try:
            response = await self.llm.analyze_text(prompt)
            if not response:
                return []
            return self._parse_genre_response(response)
        except Exception as e:
            logger.warning(f"LLM genre analysis failed: {e}")
            return []

    def _parse_genre_response(self: "GenreService", response: str) -> list[str]:
        """Parse genre response from LLM."""
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
