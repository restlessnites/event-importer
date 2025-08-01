"""Enhanced image search service with better query building and candidate selection."""

import html
import logging
import re
from collections.abc import Awaitable, Callable
from io import BytesIO
from typing import Any
from urllib.parse import urlparse

from PIL import Image, UnidentifiedImageError

from app.config import Config
from app.core.errors import APIError, handle_errors_async
from app.core.schemas import EventData, ImageCandidate, ImageResult, ImageSearchResult
from app.shared.http import HTTPService

logger = logging.getLogger(__name__)


ProgressCallback = Callable[[str, float], Awaitable[None]]


class ImageService:
    """Service for image validation, rating, and search."""

    # Domains to avoid (stock photos, etc)
    AVOID_DOMAINS = [
        "getty",
        "shutterstock",
        "alamy",
        "istockphoto",
        "stock.adobe",
        "depositphotos",
        "dreamstime",
        "lookaside.instagram.com",
        "lookaside.fbsbx.com",
    ]

    # Priority domains for music content
    PRIORITY_DOMAINS = [
        "spotify",
        "last.fm",
        "discogs",
        "allmusic",
        "pitchfork",
        "rollingstone",
        "billboard",
        "musicbrainz",
        "bandcamp",
        "soundcloud",
    ]

    def __init__(
        self: "ImageService",
        config: Config,
        http_service: HTTPService,
    ) -> None:
        """Initialize image service."""
        self.config = config
        self.http = http_service
        self.google_enabled = bool(
            config.api.google_api_key and config.api.google_cse_id,
        )
        # These are needed for the search call
        self.api_key = config.api.google_api_key
        self.cse_id = config.api.google_cse_id

        # Image validation settings
        self.max_image_size = 2 * 1024 * 1024  # 2MB
        self.min_image_width = 500
        self.min_image_height = 500

        if self.google_enabled:
            logger.info("Google Custom Search configured - image search enabled")
        else:
            logger.warning(
                "Google Custom Search not configured - image search disabled",
            )

    @handle_errors_async(reraise=True)
    async def validate_and_download(
        self: "ImageService",
        url: str,
        max_size: int | None = None,
        http_service: HTTPService | None = None,
    ) -> tuple[bytes, str] | None:
        """Download and validate an image."""
        max_size = max_size or self.max_image_size
        http = http_service or self.http

        # Download image data, disabling SSL verification for robustness
        image_data = await http.download(
            url,
            max_size=max_size,
            service="ImageValidator",
            verify_ssl=False,
        )

        # Validate with Pillow
        try:
            with Image.open(BytesIO(image_data)) as img:
                # Check dimensions
                if (
                    img.width < self.min_image_width
                    or img.height < self.min_image_height
                ):
                    return None

            # Get content-type from headers if possible, or guess from data
            mime_type = "image/jpeg"  # Default, will be refined
            return image_data, mime_type

        except UnidentifiedImageError:
            logger.warning(f"Could not identify image from URL: {url}")
            return None

    @handle_errors_async(reraise=True)
    async def rate_image(self: "ImageService", url: str) -> ImageCandidate:
        """Rate an image based on various factors."""
        candidate = ImageCandidate(url=url)

        # Immediately reject images from blocked domains
        parsed_url = urlparse(url)
        if any(domain in parsed_url.netloc for domain in self.AVOID_DOMAINS):
            candidate.score = 0
            candidate.reason = "Domain is blacklisted"
            return candidate

        score = 0
        reasons = []

        # Use a dedicated HTTPService instance to avoid session closure issues
        async with HTTPService(self.config) as http:
            try:
                # 1. Download and validate image
                result = await self.validate_and_download(url, http_service=http)
                if not result:
                    candidate.reason = "Invalid or inaccessible image"
                    candidate.score = 0
                    return candidate

                image_data, mime_type = result
                with Image.open(BytesIO(image_data)) as img:
                    candidate.dimensions = f"{img.width}x{img.height}"

                # 2. Check for priority domains
                if any(domain in parsed_url.netloc for domain in self.PRIORITY_DOMAINS):
                    reasons.append("Priority domain")
                    score += 20

                # 3. Analyze image data (basic)
                if len(image_data) > 100 * 1024:  # Over 100KB
                    score += 30
                    reasons.append("Good size")

                # 4. Check content-type
                if "jpeg" in mime_type:
                    score += 10
                    reasons.append("JPEG format")

                # Final score calculation
                candidate.score = max(0, 100 + score)
                candidate.reason = ", ".join(reasons) if reasons else "OK"

            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Rating failed for {url}: {e}")
                candidate.score = 0
                candidate.reason = f"Rating error: {e}"

            return candidate

    @handle_errors_async(reraise=True)
    async def enhance_event_image(
        self: "ImageService",
        event_data: EventData,
        progress_callback: ProgressCallback | None = None,
        failure_collector: Any | None = None,
        force_search: bool = False,
        supplementary_context: str | None = None,
    ) -> ImageResult:
        """Enhance the image for an event by searching for better alternatives.

        Returns:
            ImageResult with original and enhanced image URLs
        """
        # Start with original image info
        original_url = event_data.images.get("full") if event_data.images else None
        result = ImageResult(original_image_url=original_url)

        if not self.google_enabled:
            logger.warning("Image enhancement skipped: Google Search not configured.")
            return result

        logger.info(f"Starting image enhancement for event: {event_data.title}")
        search_result = ImageSearchResult()

        async def send_progress(message: str, percent: float) -> None:
            if progress_callback:
                await progress_callback(message, percent)

        # The main workflow is broken into private helpers to reduce complexity
        original_url = await self._rate_original_image_if_present(
            event_data, search_result, send_progress, failure_collector
        )
        new_candidates = await self._search_for_new_candidates(
            event_data, send_progress, failure_collector, supplementary_context
        )
        search_result.candidates = await self._rate_found_candidates(
            new_candidates, send_progress, failure_collector
        )

        await send_progress("Selecting best image", 0.95)
        best_image_url = self._select_best_image(
            search_result, original_url, force_search
        )

        # Set the selected candidate on search_result
        if best_image_url:
            for candidate in [search_result.original] + search_result.candidates:
                if candidate and candidate.url == best_image_url:
                    search_result.selected = candidate
                    break

        # Build result
        result.enhanced_image_url = best_image_url if best_image_url != original_url else original_url
        result.thumbnail_url = result.enhanced_image_url
        result.search_result = search_result

        return result

    async def _rate_original_image_if_present(
        self: "ImageService",
        event_data: EventData,
        search_result: ImageSearchResult,
        send_progress: ProgressCallback,
        failure_collector: Any | None = None,
    ) -> str | None:
        """Rate original image if present, update search_result, and return URL."""
        original_url = (
            event_data.images.get("full") or event_data.images.get("thumbnail")
            if event_data.images
            else None
        )
        if not original_url:
            return None

        await send_progress("Rating original image", 0.05)
        try:
            candidate = await self.rate_image(original_url)
            candidate.source = "original"
            search_result.original = candidate
            logger.info(f"Original image rated: score {candidate.score}")
        except Exception as e:
            logger.warning(f"Failed to rate original image {original_url}: {e}")
            if failure_collector and hasattr(failure_collector, "add_failure"):
                if isinstance(e, APIError):
                    failure_collector.add_failure(e.service, e)
                else:
                    failure_collector.add_failure("ImageService", e)
        return original_url

    async def _execute_search_query(
        self: "ImageService",
        query: str,
        query_index: int,
        failure_collector: Any | None = None,
    ) -> list[ImageCandidate]:
        """Execute a single image search query and return candidates, handling errors."""
        try:
            results = await self._search_google_images(query, 5)
            logger.info(
                f"Google Image Search returned {len(results)} results for query: '{query}'"
            )
            if not results:
                error_msg = (
                    f"Google Image Search returned no results for query: '{query}'"
                )
                if failure_collector:
                    failure_collector.add_failure(
                        "GoogleImageSearch", ValueError(error_msg)
                    )
                return []
            return [
                ImageCandidate(url=url, source=f"query_{query_index}")
                for result in results
                if (url := result.get("link"))
            ]
        except Exception as e:
            logger.warning(f"Search query '{query}' failed: {e}")
            if failure_collector and hasattr(failure_collector, "add_failure"):
                service = e.service if isinstance(e, APIError) else "GoogleImageSearch"
                failure_collector.add_failure(service, e)
            return []

    async def _search_for_new_candidates(
        self: "ImageService",
        event_data: EventData,
        send_progress: ProgressCallback,
        failure_collector: Any | None = None,
        supplementary_context: str | None = None,
    ) -> list[ImageCandidate]:
        """Search for new image candidates using generated queries."""
        queries = self._build_search_queries(event_data)
        if supplementary_context:
            queries.insert(0, supplementary_context)
            logger.info(f"Added supplementary context query: '{supplementary_context}'")

        if not queries:
            logger.warning("No search queries generated for image search")
            return []

        await send_progress(f"Searching with {len(queries)} queries", 0.15)
        search_candidates: list[ImageCandidate] = []
        for i, query in enumerate(queries):
            progress = 0.15 + ((i + 1) / len(queries) * 0.3)
            await send_progress(
                f"Query {i + 1}/{len(queries)}: '{query[:30]}...'", progress
            )

            new_candidates = await self._execute_search_query(
                query, i, failure_collector
            )

            # Add new, unique candidates to the list
            added_count = 0
            for candidate in new_candidates:
                if not any(c.url == candidate.url for c in search_candidates):
                    search_candidates.append(candidate)
                    added_count += 1
            logger.info(
                f"Found {len(new_candidates)} results, added {added_count} unique candidates from query: '{query}'"
            )
        return search_candidates

    async def _rate_found_candidates(
        self: "ImageService",
        candidates: list[ImageCandidate],
        send_progress: ProgressCallback,
        failure_collector: Any | None = None,
    ) -> list[ImageCandidate]:
        """Rate a list of found image candidates."""
        await send_progress(f"Rating {len(candidates)} candidates", 0.5)
        if not candidates:
            return []

        rated_candidates: list[ImageCandidate] = []
        for i, candidate in enumerate(candidates):
            progress = 0.5 + ((i + 1) / len(candidates) * 0.4)
            await send_progress(f"Rating image {i + 1}/{len(candidates)}", progress)
            try:
                rated = await self.rate_image(candidate.url)
                rated.source = candidate.source
                if rated.score > 0:
                    rated_candidates.append(rated)
            except Exception as e:
                logger.warning(f"Failed to rate image {candidate.url}: {e}")
                if failure_collector and hasattr(failure_collector, "add_failure"):
                    if isinstance(e, APIError):
                        failure_collector.add_failure(e.service, e)
                    else:
                        failure_collector.add_failure("ImageService", e)
        return rated_candidates

    def _select_best_image(
        self: "ImageService",
        search_result: ImageSearchResult,
        original_url: str | None,
        force_search: bool = False,
    ) -> str | None:
        """Select the best image from candidates and return its URL."""
        best_candidate = search_result.get_best_candidate()

        # If force_search is True, prefer search results over original
        # Only use original if no search candidates found
        if force_search and search_result.candidates:
            # Find best among search candidates only (exclude original)
            search_only_candidates = [
                c for c in search_result.candidates if c.url != original_url
            ]
            if search_only_candidates:
                best_search_candidate = max(
                    search_only_candidates, key=lambda c: c.score
                )
                logger.info(
                    f"Force search: Selected new image (score: {best_search_candidate.score}): {best_search_candidate.url}"
                )
                return best_search_candidate.url

        # Normal flow: select best overall candidate
        if best_candidate and best_candidate.url != original_url:
            logger.info(
                f"Selected new image (score: {best_candidate.score}): {best_candidate.url}"
            )
            return best_candidate.url
        logger.info("Keeping original image.")
        return original_url

    def _select_and_update_best_image(
        self: "ImageService",
        event_data: EventData,
        search_result: ImageSearchResult,
        original_url: str | None,
        force_search: bool = False,
    ) -> None:
        """Select the best image from candidates and update event_data (legacy method)."""
        best_url = self._select_best_image(search_result, original_url, force_search)
        if best_url:
            event_data.images = {
                "full": best_url,
                "thumbnail": best_url,
            }
            # Find and set the selected candidate
            for candidate in [search_result.original] + search_result.candidates:
                if candidate and candidate.url == best_url:
                    search_result.selected = candidate
                    break
            return

    def _get_primary_artist_for_search(
        self: "ImageService", event_data: EventData
    ) -> str:
        """Extract the primary artist from the event title if lineup is not available."""
        # Start with the full title
        title = event_data.title

        # Decode HTML entities
        title = html.unescape(title)

        # Remove "at [Venue]" part
        if event_data.venue:
            venue_pattern = re.compile(
                f"\\s+at\\s+{re.escape(event_data.venue)}\\s*$", re.IGNORECASE
            )
            title = venue_pattern.sub("", title)

        # Basic cleanup of common suffixes
        title = re.sub(
            r"\\s+\\(live\\)$|\\s+dj set\\s*$", "", title, flags=re.IGNORECASE
        ).strip()

        return title.strip()

    def _build_search_queries(self: "ImageService", event_data: EventData) -> list[str]:
        """Build a list of search queries for Google Image Search."""
        # Check if we have actual artists in the lineup
        if event_data.lineup and len(event_data.lineup) > 0:
            # Use the first artist for focused searches
            artist = event_data.lineup[0]
            queries = [
                f'"{artist}" press photo',
                f'"{artist}" musician official photo',
                f'"{artist}" band photo',
            ]
            logger.info(f"Building artist queries for '{artist}': {queries}")
            return queries

        # No lineup - use event-focused queries
        # Extract just the event name without venue
        event_name = self._get_primary_artist_for_search(event_data)
        logger.info(f"No lineup found. Event name extracted: '{event_name}'")

        # For events without lineup, search for event materials
        queries = [
            f"{event_name} event poster",
            f"{event_name} flyer",
            f"{event_data.venue} event {event_name}"
            if event_data.venue
            else f"{event_name} event",
        ]
        logger.info(f"Building event queries: {queries}")
        return queries

    @handle_errors_async(reraise=True)
    async def _search_google_images(
        self: "ImageService",
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for images using Google Custom Search API."""
        if not self.google_enabled:
            return []

        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "searchType": "image",
            "num": limit,
            "imgSize": "large",
            "imgType": "photo",
            "safe": "off",
            "fileType": "jpg,png,webp",
            "rights": "cc_publicdomain,cc_attribute,cc_sharealike,cc_noncommercial,cc_nonderived",
        }

        try:
            logger.info(f"DEBUG: Google Image Search params: {params}")
            logger.info(
                f"DEBUG: Params types: {[(k, type(v).__name__) for k, v in params.items()]}"
            )
            response = await self.http.get_json(
                "https://www.googleapis.com/customsearch/v1",
                service="GoogleImageSearch",
                params=params,
            )

            # Log the full response structure to understand what's happening
            if "error" in response:
                error_info = response["error"]
                logger.error(f"Google API error: {error_info}")
                raise APIError(
                    service="GoogleImageSearch",
                    message=error_info.get("message", "Unknown Google API error"),
                    status_code=error_info.get("code", 0),
                )

            # Check if we have search information
            search_info = response.get("searchInformation", {})
            total_results = search_info.get("totalResults", "0")
            logger.info(
                f"Google search info - Total results: {total_results}, Query: '{query}'"
            )

            # Get the actual results
            results = response.get("items", [])

            # If no items but no error, log why
            if not results and int(total_results) > 0:
                logger.warning(
                    f"Google returned totalResults={total_results} but no items for query: '{query}'"
                )

            return results if results else []

        except APIError:
            # Re-raise API errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Google search: {e}")
            raise APIError(
                service="GoogleImageSearch",
                message=f"Search failed: {str(e)}",
                status_code=0,
            ) from e
