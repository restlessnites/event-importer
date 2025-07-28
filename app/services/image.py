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
from app.errors import handle_errors_async, retry_on_error
from app.schemas import EventData, ImageCandidate, ImageSearchResult
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

        if self.google_enabled:
            logger.info("✅ Google Custom Search configured - image search enabled")
        else:
            logger.warning(
                "⚠️ Google Custom Search not configured - image search disabled",
            )

    @staticmethod
    def get_domain(url: str) -> str:
        """Extract the domain from a URL, ignoring 'www.'."""
        try:
            parsed_url = urlparse(url)
            netloc = parsed_url.netloc
            if netloc.startswith("www."):
                return netloc[4:]
            return netloc
        except Exception:
            return ""

    @handle_errors_async(reraise=True)
    async def validate_and_download(
        self: "ImageService",
        url: str,
        max_size: int | None = None,
        http_service: HTTPService | None = None,
    ) -> tuple[bytes, str] | None:
        """Download and validate an image."""
        max_size = max_size or self.config.extraction.max_image_size
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
                    self.config.extraction.min_image_width
                    and img.width < self.config.extraction.min_image_width
                ) or (
                    self.config.extraction.min_image_height
                    and img.height < self.config.extraction.min_image_height
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
    @retry_on_error(max_attempts=2)
    async def search_event_images(
        self: "ImageService",
        event_data: EventData,
        limit: int = 10,
    ) -> list[ImageCandidate]:
        """Search for event images using Google Custom Search."""
        if not self.google_enabled:
            return []

        # Build search queries
        queries = self._build_search_queries(event_data)
        candidates: list[ImageCandidate] = []

        # Search each query
        for query in queries:
            results = await self._search_google_images(query, limit)
            for result in results:
                url = result.get("link")
                if not url:
                    continue

                # Skip if we already have this URL
                if any(c.url == url for c in candidates):
                    continue

                # Rate the image
                candidate = await self.rate_image(url)
                if candidate.score > 0:
                    candidates.append(candidate)

        # Sort by score and limit
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:limit]

    @handle_errors_async(reraise=True)
    async def enhance_event_image(
        self: "ImageService",
        event_data: EventData,
        progress_callback: ProgressCallback | None = None,
    ) -> EventData:
        """Enhance the image for an event by searching for better alternatives."""
        if not self.google_enabled:
            logger.warning("Image enhancement skipped: Google Search not configured.")
            return event_data

        logger.info(f"Starting image enhancement for event: {event_data.title}")
        search_result = ImageSearchResult()

        async def send_progress(message: str, percent: float) -> None:
            if progress_callback:
                await progress_callback(message, percent)

        # The main workflow is broken into private helpers to reduce complexity
        original_url = await self._rate_original_image_if_present(
            event_data, search_result, send_progress
        )
        new_candidates = await self._search_for_new_candidates(
            event_data, send_progress
        )
        search_result.candidates = await self._rate_found_candidates(
            new_candidates, send_progress
        )

        await send_progress("Selecting best image", 0.95)
        self._select_and_update_best_image(event_data, search_result, original_url)

        event_data.image_search = search_result
        return event_data

    async def _rate_original_image_if_present(
        self: "ImageService",
        event_data: EventData,
        search_result: ImageSearchResult,
        send_progress: ProgressCallback,
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
        return original_url

    async def _search_for_new_candidates(
        self: "ImageService", event_data: EventData, send_progress: ProgressCallback
    ) -> list[ImageCandidate]:
        """Search for new image candidates using generated queries."""
        queries = self._build_search_queries(event_data)
        await send_progress(f"Searching with {len(queries)} queries", 0.15)
        search_candidates: list[ImageCandidate] = []
        for i, query in enumerate(queries):
            progress = 0.15 + ((i + 1) / len(queries) * 0.3)
            await send_progress(
                f"Query {i + 1}/{len(queries)}: '{query[:30]}...'", progress
            )
            try:
                results = await self._search_google_images(query, 5)
                for result in results:
                    url = result.get("link")
                    if url and not any(c.url == url for c in search_candidates):
                        search_candidates.append(
                            ImageCandidate(url=url, source=f"query_{i}")
                        )
            except Exception as e:
                logger.warning(f"Search query '{query}' failed: {e}")
        return search_candidates

    async def _rate_found_candidates(
        self: "ImageService",
        candidates: list[ImageCandidate],
        send_progress: ProgressCallback,
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
        return rated_candidates

    def _select_and_update_best_image(
        self: "ImageService",
        event_data: EventData,
        search_result: ImageSearchResult,
        original_url: str | None,
    ) -> None:
        """Select the best image from candidates and update event_data."""
        best_candidate = search_result.get_best_candidate()
        if best_candidate and best_candidate.url != original_url:
            logger.info(
                f"Selected new image (score: {best_candidate.score}): {best_candidate.url}"
            )
            event_data.images = {
                "full": best_candidate.url,
                "thumbnail": best_candidate.url,
            }
            search_result.selected = best_candidate
        else:
            logger.info("Keeping original image.")
            if search_result.original:
                search_result.selected = search_result.original

    def _get_primary_artist_for_search(self: "ImageService", event_data: EventData) -> str:
        """Extract the primary artist from the event title if lineup is not available."""
        # Start with the full title
        title = event_data.title

        # Decode HTML entities
        title = html.unescape(title)

        # Remove "at [Venue]" part
        if event_data.venue:
            venue_pattern = re.compile(f"\\s+at\\s+{re.escape(event_data.venue)}\\s*$", re.IGNORECASE)
            title = venue_pattern.sub("", title)

        # Basic cleanup of common suffixes
        title = re.sub(r"\\s+\\(live\\)$|\\s+dj set\\s*$", "", title, flags=re.IGNORECASE).strip()

        return title.strip()

    def _build_search_queries(self: "ImageService", event_data: EventData) -> list[str]:
        """Build a list of search queries for Google Image Search."""
        artist_name = self._get_primary_artist_for_search(event_data)
        if not artist_name:
            # Fallback to just the title if no artist can be determined
            return [f'"{event_data.title}" event flyer']

        # Use focused queries for high-quality press and official photos
        return [
            f'"{artist_name}" press photo',
            f'"{artist_name}" musician official photo',
            f'"{artist_name}" band photo',
        ]

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

        response = await self.http.get_json(
            "https://www.googleapis.com/customsearch/v1",
            service="GoogleImageSearch",
            params=params,
        )

        results = response.get("items", [])
        return results if results else []
