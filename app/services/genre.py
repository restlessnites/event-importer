"""Genre enhancement service using web search and LLMs."""

import json
import logging
import re
from typing import Any

from app.config import Config
from app.core.error_messages import ServiceMessages
from app.core.errors import APIError, retry_on_error
from app.core.schemas import EventData
from app.services.llm.prompts import GenrePrompts
from app.services.llm.service import LLMService
from app.shared.data.genres import MusicGenres
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
                "Genre enhancement disabled - Google Search API not configured",
            )

    async def enhance_genres(
        self: "GenreService",
        event_data: EventData,
        supplementary_context: str | None = None,
    ) -> list[str]:
        """Enhance event with missing genre information.

        Only searches if:
        1. No genres are present
        2. We have artists to search for
        3. Google search is enabled

        Args:
            event_data: Event data to enhance
            supplementary_context: Optional context to help identify genres

        Returns:
            List of enhanced genres (or original genres if enhancement fails)
        """
        # Check if we already have genres
        if event_data.genres:
            return event_data.genres

        # Check if Google is enabled
        if not self.google_enabled:
            logger.warning("Genre enhancement skipped: Google Search not configured")
            return event_data.genres

        # Check if we have artists to search for
        if not event_data.lineup:
            if not supplementary_context:
                error_msg = (
                    "Cannot search for genres: Event has no lineup. "
                    "Please provide artist names in supplementary_context parameter."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            # Extract artist names from supplementary context
            logger.info(
                f"No lineup found. Using supplementary context as artist info: {supplementary_context}"
            )
            primary_artist = supplementary_context
            # Don't pass supplementary_context again since we're using it as the artist
            context_to_pass = None
        else:
            primary_artist = event_data.lineup[0]
            # Pass supplementary_context for additional context
            context_to_pass = supplementary_context

        logger.info(f"Searching for genres for event: {event_data.title}")

        try:
            found_genres = await self._search_artist_genres(
                primary_artist,
                self._build_event_context(event_data),
                context_to_pass,
            )

            if found_genres:
                # Validate and normalize genres
                validated = MusicGenres.validate_genres(found_genres)
                if validated:
                    genres = validated[:4]  # Limit to 4 genres
                    logger.info(f"Enhanced genres: {genres}")
                    return genres

        except (ValueError, TypeError, KeyError) as e:
            logger.warning(
                f"{ServiceMessages.GENRE_ENHANCEMENT_FAILED} for {primary_artist}: {e}"
            )

        return event_data.genres

    def _build_event_context(
        self: "GenreService",
        event_data: EventData,
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
        self: "GenreService",
        artist_name: str,
        event_context: dict[str, Any],
        supplementary_context: str | None = None,
    ) -> list[str]:
        """Search for an artist's genres using Google and an LLM."""
        # Build search query
        # Check if this looks like a description rather than an artist name
        # (happens when event has no lineup and supplementary_context is used as artist)
        is_description = len(artist_name.split()) > 4 or any(
            word in artist_name.lower()
            for word in ["similar", "like", "genre", "style"]
        )

        if supplementary_context:
            # Use supplementary context to help find genres
            if is_description:
                # Don't quote descriptions
                query = f"{artist_name} music genre"
            else:
                query = f'"{artist_name}" {supplementary_context} music genre'
            logger.debug(f"Searching for artist genres with context: {query}")
        else:
            if is_description:
                # Don't quote descriptions
                query = f"{artist_name} music genre"
            else:
                query = f'"{artist_name}" music genre artist'
            logger.debug(f"Searching for artist genres: {query}")

        try:
            # Search Google
            search_results = await self._google_search(query)
            if not search_results:
                logger.warning(f"No search results found for artist: {artist_name}")
                return []

            # Extract text from results
            search_text = self._extract_search_text(search_results)
            logger.debug(
                f"Extracted {len(search_text)} characters of text for genre analysis"
            )

            # Use LLM to analyze and extract genres
            genres = await self._extract_genres_with_llm(
                artist_name,
                search_text,
                event_context,
            )

            if genres:
                logger.info(f"Found {len(genres)} genres for {artist_name}: {genres}")
            else:
                logger.warning(
                    f"No genres extracted from search results for {artist_name}"
                )

            return genres

        except APIError as e:
            logger.error(f"API error during genre search for {artist_name}: {e}")
            raise  # Re-raise to be handled by caller
        except Exception:
            logger.exception(f"{ServiceMessages.GENRE_SEARCH_FAILED} for {artist_name}")
            raise  # Re-raise to be handled by caller

    async def _google_search(self: "GenreService", query: str) -> list[dict[str, Any]]:
        """Execute Google search for artist information."""
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": 5,  # Just need a few good results
        }

        try:
            logger.info(f"DEBUG: Google Genre Search params: {params}")
            logger.info(
                f"DEBUG: Params types: {[(k, type(v).__name__) for k, v in params.items()]}"
            )
            response = await self.http.get_json(
                "https://www.googleapis.com/customsearch/v1",
                service="GoogleGenreSearch",
                params=params,
                timeout=10,
            )

            # Check for API errors
            if "error" in response:
                error_info = response["error"]
                logger.error(f"Google API error for genres: {error_info}")
                raise APIError(
                    service="GoogleGenreSearch",
                    message=error_info.get("message", "Unknown Google API error"),
                    status_code=error_info.get("code", 0),
                )

            # Check search information
            search_info = response.get("searchInformation", {})
            total_results = search_info.get("totalResults", "0")
            logger.info(
                f"Google genre search - Total results: {total_results}, Query: '{query}'"
            )

            # Get results
            results = response.get("items", [])

            # Log if no results found
            if not results and int(total_results) > 0:
                logger.warning(
                    f"Google returned totalResults={total_results} but no items for genre query: '{query}'"
                )
            elif not results:
                logger.warning(f"No results found for genre query: '{query}'")

            return results

        except APIError:
            # Re-raise API errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Google genre search: {e}")
            raise APIError(
                service="GoogleGenreSearch",
                message=f"Search failed: {str(e)}",
                status_code=0,
            ) from e

    def _extract_search_text(
        self: "GenreService",
        results: list[dict[str, Any]],
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
        """Use LLM to extract genres from search text using structured output."""
        # Check if this is a genre description rather than an artist name
        is_genre_description = len(artist_name.split()) > 4 or any(
            word in artist_name.lower()
            for word in [
                "indie",
                "rock",
                "electronic",
                "jazz",
                "hip hop",
                "genre",
                "music",
                "style",
            ]
        )

        if is_genre_description:
            # Use a simpler prompt for genre extraction when supplementary context is genre-related
            prompt = GenrePrompts.build_genre_extraction_prompt(
                artist_name,
                search_text,
                event_context,
            )
        else:
            # Use the standard artist verification prompt
            prompt = GenrePrompts.build_artist_verification_prompt(
                artist_name,
                search_text,
                event_context,
            )

        try:
            # Create temporary EventData for Claude's enhance_genres method
            _temp_event = EventData(
                title=event_context.get("title", "Unknown Event"),
                lineup=[artist_name] if not is_genre_description else [],
                genres=[],  # Empty to trigger genre enhancement
                source_url="https://example.com",  # Required field
            )

            # Use Claude's structured genre enhancement with our custom prompt
            genres = await self.llm.extract_genres_with_context(prompt)

            if genres:
                logger.info(f"LLM found genres using structured output: {genres}")
                return genres

            logger.warning("LLM returned no genres from structured output")
            return []

        except Exception as e:
            logger.error(f"{ServiceMessages.LLM_GENRE_ANALYSIS_FAILED}: {e}")
            logger.debug(f"Genre extraction prompt was: {prompt[:500]}...")
            return []

    def _parse_genre_response(self: "GenreService", response: str) -> list[str]:
        """Parse genre response from LLM."""
        try:
            # First try to find JSON array in response
            match = re.search(r"\[.*?\]", response, re.DOTALL)
            if match:
                try:
                    genres = json.loads(match.group())
                    # Validate they're strings
                    valid_genres = [
                        g for g in genres if isinstance(g, str) and g.strip()
                    ]
                    if valid_genres:
                        return valid_genres
                except json.JSONDecodeError as e:
                    logger.debug(f"JSON parse failed: {e}")

            # If no JSON found or parsing failed, try to extract from text
            # Look for common patterns like "Genres: Rock, Pop" or bullet points
            patterns = [
                r"(?:Genres?|PRIMARY GENRES?):\s*([^\n]+)",
                r"(?:^|\n)[-•*]\s*([A-Z][a-zA-Z\s&-]+?)(?:\n|$)",
                r"(?:^|\n)(?:\d+\.)\s*([A-Z][a-zA-Z\s&-]+?)(?:\n|$)",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, response, re.MULTILINE)
                if matches:
                    # Clean and validate genres
                    genres = []
                    for match in matches:
                        # Split by comma if it's a comma-separated list
                        items = [item.strip() for item in match.split(",")]
                        genres.extend(items)

                    # Filter valid genres
                    valid_genres = [
                        g.strip()
                        for g in genres
                        if g.strip() and len(g.strip()) < 30  # Reasonable genre length
                    ][:4]  # Max 4 genres

                    if valid_genres:
                        logger.debug(
                            f"Extracted genres from text pattern: {valid_genres}"
                        )
                        return valid_genres

            logger.debug(f"No genres found in response: {response[:200]}...")
            return []

        except Exception as e:
            logger.error(f"Error parsing genre response: {e}")
            return []
