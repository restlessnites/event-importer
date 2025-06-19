"""Enhanced image search service with better query building and candidate selection."""

import logging
import re
from io import BytesIO
from typing import Any
from urllib.parse import urlparse

from PIL import Image, UnidentifiedImageError

from app.config import Config
from app.errors import handle_errors_async, retry_on_error
from app.schemas import EventData, ImageCandidate
from app.shared.http import HTTPService

logger = logging.getLogger(__name__)


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
        self: "ImageService", config: Config, http_service: HTTPService
    ) -> None:
        """Initialize image service."""
        self.config = config
        self.http = http_service
        self.google_enabled = bool(
            config.api.google_api_key and config.api.google_cse_id
        )
        # These are needed for the search call
        self.api_key = config.api.google_api_key
        self.cse_id = config.api.google_cse_id

        if self.google_enabled:
            logger.info("✅ Google Custom Search configured - image search enabled")
        else:
            logger.warning(
                "⚠️ Google Custom Search not configured - image search disabled"
            )

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
            url, max_size=max_size, service="ImageValidator", verify_ssl=False
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
        from app.shared.http import HTTPService

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

            except Exception as e:
                logger.warning(f"Rating failed for {url}: {e}")
                candidate.score = 0
                candidate.reason = f"Rating error: {e}"

            return candidate

    @handle_errors_async(reraise=True)
    @retry_on_error(max_attempts=2)
    async def search_event_images(
        self: "ImageService", event_data: EventData, limit: int = 10
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

    def _get_primary_artist_for_search(
        self: "ImageService", event_data: EventData
    ) -> str | None:
        """Extract the main artist name from event data for image searching."""
        if event_data.lineup:
            return event_data.lineup[0]

        title = event_data.title

        # Clean up common venue/event prefixes and suffixes from the title

        clean_patterns = [
            r"^(live at|at the|concert at|presents?)\s+",
            r"\s+(live|concert|show|tour)$",
            r"\s+(tickets?|event)$",
        ]

        for pattern in clean_patterns:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)

        return title.strip() if title.strip() else None

    def _build_search_queries(self: "ImageService", event_data: EventData) -> list[str]:
        """Build a list of search queries for Google Image Search."""
        artist_name = self._get_primary_artist_for_search(event_data)
        if not artist_name:
            # Fallback to just the title if no artist can be determined
            return [f'"{event_data.title}" event flyer']

        # Use focused queries for high-quality press and official photos
        queries = [
            f'"{artist_name}" press photo',
            f'"{artist_name}" musician official photo',
            f'"{artist_name}" band photo',
        ]
        return queries

    @handle_errors_async(reraise=True)
    async def _search_google_images(
        self: "ImageService", query: str, limit: int = 10
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
