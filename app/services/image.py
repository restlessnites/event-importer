"""Image processing and search service."""

import logging
from typing import Optional, List, Tuple
from io import BytesIO

from PIL import Image

from app.config import Config
from app.http import HTTPService
from app.schemas import EventData, ImageCandidate


logger = logging.getLogger(__name__)


class ImageService:
    """Service for image validation, rating, and search."""

    def __init__(self, config: Config, http_service: HTTPService):
        """Initialize image service."""
        self.config = config
        self.http = http_service
        self.google_enabled = bool(
            config.api.google_api_key and config.api.google_cse_id
        )

    async def validate_and_download(
        self, url: str, max_size: Optional[int] = None
    ) -> Optional[Tuple[bytes, str]]:
        """Download and validate an image."""
        max_size = max_size or self.config.extraction.max_image_size

        try:
            # Download the image
            image_data = await self.http.download(
                url,
                service="Image",
                max_size=max_size,
            )

            # Basic validation
            try:
                with Image.open(BytesIO(image_data)) as img:
                    width, height = img.size
                    mime_type = f"image/{img.format.lower()}"

                    # Check minimum dimensions
                    if (
                        width < self.config.extraction.min_image_width
                        and height < self.config.extraction.min_image_height
                    ):
                        logger.debug(f"Image too small: {width}x{height}")
                        return None

                    return image_data, mime_type

            except Exception as e:
                logger.debug(f"Invalid image format: {e}")
                return None

        except Exception as e:
            logger.debug(f"Failed to download image: {e}")
            return None

    async def rate_image(self, url: str) -> ImageCandidate:
        """Rate an image for event suitability."""
        candidate = ImageCandidate(url=url, source="unknown")

        try:
            # Download and check the image
            result = await self.validate_and_download(url)
            if not result:
                candidate.score = 0
                candidate.reason = "validation_failed"
                return candidate

            image_data, _ = result

            # Analyze with PIL
            with Image.open(BytesIO(image_data)) as img:
                width, height = img.size
                aspect_ratio = height / width
                size_kb = len(image_data) / 1024

                candidate.dimensions = f"{width}x{height}"

                # Base score
                score = 50

                # Size bonus
                if width >= 1000 or height >= 1000:
                    score += 50
                elif width >= 800 or height >= 800:
                    score += 30

                # Aspect ratio bonus (prefer portrait for event flyers)
                if aspect_ratio >= 1.3:  # Portrait
                    score += 50
                elif aspect_ratio >= 1.1:
                    score += 30

                # File size penalty if too large
                if size_kb > 5000:  # > 5MB
                    score -= 20

                candidate.score = score

        except Exception as e:
            logger.debug(f"Failed to rate image {url}: {e}")
            candidate.score = 0
            candidate.reason = "rating_failed"

        return candidate

    async def search_event_images(
        self, event_data: EventData, limit: int = 5
    ) -> List[ImageCandidate]:
        """Search for event images using Google Custom Search."""
        if not self.google_enabled:
            return []

        # Build search query
        query_parts = []
        if event_data.lineup:
            query_parts.append(event_data.lineup[0])
        elif event_data.title:
            query_parts.append(event_data.title)

        if not query_parts:
            return []

        query = f"{query_parts[0]} band photo"

        try:
            # Search using Google Custom Search API
            params = {
                "key": self.config.api.google_api_key,
                "cx": self.config.api.google_cse_id,
                "q": query,
                "searchType": "image",
                "num": limit,
                "imgSize": "large",
                "imgType": "photo",
                "safe": "off",
            }

            response = await self.http.get_json(
                "https://www.googleapis.com/customsearch/v1",
                service="Google",
                params=params,
            )

            if "items" not in response:
                return []

            # Create candidates from results
            candidates = []
            for item in response["items"]:
                if "link" in item:
                    candidate = ImageCandidate(
                        url=item["link"],
                        source="google_search",
                    )
                    candidates.append(candidate)

            return candidates

        except Exception as e:
            logger.error(f"Image search failed: {e}")
            return []

    async def find_best_image(
        self, event_data: EventData, original_url: Optional[str] = None
    ) -> Optional[ImageCandidate]:
        """Find the best image for an event."""
        candidates = []

        # Rate original if provided
        if original_url:
            original = await self.rate_image(original_url)
            original.source = "original"
            if original.score > 0:
                candidates.append(original)

        # Search for additional images if enabled
        if self.google_enabled:
            search_results = await self.search_event_images(event_data)
            for candidate in search_results:
                rated = await self.rate_image(candidate.url)
                rated.source = "google_search"
                if rated.score > 0:
                    candidates.append(rated)

        # Return best candidate
        if candidates:
            return max(candidates, key=lambda c: c.score)

        return None
