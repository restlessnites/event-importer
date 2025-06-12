"""Enhanced image search service with better query building and candidate selection."""

import logging
from typing import Optional, List, Tuple, Dict, Any
from io import BytesIO
from urllib.parse import quote_plus
import re

from PIL import Image

from app.config import Config
from app.shared.http import HTTPService
from app.schemas import EventData, ImageCandidate
from app.errors import retry_on_error, handle_errors_async


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

    def __init__(self, config: Config, http_service: HTTPService):
        """Initialize image service."""
        self.config = config
        self.http = http_service
        self.google_enabled = bool(
            config.api.google_api_key and config.api.google_cse_id
        )

        if self.google_enabled:
            logger.info("✅ Google Custom Search configured - image search enabled")
        else:
            logger.warning(
                "⚠️ Google Custom Search not configured - image search disabled"
            )

    @handle_errors_async(reraise=True)
    async def validate_and_download(
        self, url: str, max_size: Optional[int] = None
    ) -> Optional[Tuple[bytes, str]]:
        """Download and validate an image."""
        max_size = max_size or self.config.extraction.max_image_size

        # Download the image
        image_data = await self.http.download(
            url,
            service="Image",
            max_size=max_size,
        )

        # Basic validation
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

    @handle_errors_async(reraise=True)
    async def rate_image(self, url: str) -> ImageCandidate:
        """Rate an image for event suitability."""
        candidate = ImageCandidate(url=url, source="unknown")

        # Skip avoided domains
        if any(domain in url.lower() for domain in self.AVOID_DOMAINS):
            candidate.score = 0
            candidate.reason = "avoided_domain"
            return candidate

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

            # Size bonus (bigger is better for event images)
            if width >= 1000 or height >= 1000:
                score += 100
            elif width >= 800 or height >= 800:
                score += 50
            elif width >= 600 or height >= 600:
                score += 25

            # STRONG preference order: portrait > square > landscape
            if aspect_ratio >= 1.4:  # Strongly portrait (1.4:1 or taller)
                score += 300
                logger.debug(
                    f"Strong portrait bonus for {url}: +300 (ratio: {aspect_ratio:.2f})"
                )
            elif aspect_ratio >= 1.2:  # Moderately portrait (1.2:1 to 1.4:1)
                score += 250
                logger.debug(
                    f"Portrait bonus for {url}: +250 (ratio: {aspect_ratio:.2f})"
                )
            elif (
                aspect_ratio >= 0.9 and aspect_ratio <= 1.1
            ):  # Square-ish (0.9:1 to 1.1:1)
                score += 150
                logger.debug(
                    f"Square bonus for {url}: +150 (ratio: {aspect_ratio:.2f})"
                )
            elif aspect_ratio >= 0.7:  # Acceptable landscape (0.7:1 to 0.9:1)
                score += 50
                logger.debug(
                    f"Landscape bonus for {url}: +50 (ratio: {aspect_ratio:.2f})"
                )
            # Very wide landscape (< 0.7:1) gets no bonus

            # Priority domain bonus
            if any(domain in url.lower() for domain in self.PRIORITY_DOMAINS):
                score += 100
                logger.debug(f"Priority domain bonus for {url}: +100")

            # File size penalty if too large
            if size_kb > 5000:  # > 5MB
                score -= 50

            # Special handling for music sources (more lenient)
            is_music_source = any(
                domain in url.lower()
                for domain in ["bandcamp", "last.fm", "spotify", "soundcloud"]
            )
            if is_music_source and size_kb < 50:
                # Small images from music sources might be album art - still valuable
                score += 25

            candidate.score = max(0, score)  # Ensure non-negative
            logger.debug(
                f"Rated {url}: score={candidate.score}, dims={candidate.dimensions}, ratio={aspect_ratio:.2f}"
            )

        return candidate

    @handle_errors_async(reraise=True)
    @retry_on_error(max_attempts=2)
    async def search_event_images(
        self, event_data: EventData, limit: int = 10
    ) -> List[ImageCandidate]:
        """Search for event images using Google Custom Search."""
        if not self.google_enabled:
            return []

        # Build search queries
        queries = self._build_search_queries(event_data)
        candidates: List[ImageCandidate] = []

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
    async def find_best_image(
        self, event_data: EventData, original_url: Optional[str] = None
    ) -> Optional[ImageCandidate]:
        """Find the best image for an event."""
        candidates: List[ImageCandidate] = []

        # Add original URL if provided
        if original_url:
            candidate = await self.rate_image(original_url)
            if candidate.score > 0:
                candidate.source = "original"
                candidates.append(candidate)

        # Search for additional images
        if self.google_enabled:
            search_candidates = await self.search_event_images(event_data)
            candidates.extend(search_candidates)

        if not candidates:
            return None

        # Sort by score and return the best
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[0]

    def _build_search_queries(self, event_data: EventData) -> List[str]:
        """Build search queries for image search."""
        queries = []

        # Extract artist from title if possible
        artist = self._extract_artist_from_title(event_data.title)
        if artist:
            # Artist + venue
            if event_data.venue:
                queries.append(f"{artist} {event_data.venue} concert")
                queries.append(f"{artist} {event_data.venue} live")

            # Artist + city
            if event_data.location and event_data.location.city:
                queries.append(f"{artist} {event_data.location.city} concert")
                queries.append(f"{artist} {event_data.location.city} live")

            # Artist + date
            if event_data.date:
                queries.append(f"{artist} {event_data.date} concert")
                queries.append(f"{artist} {event_data.date} live")

        # Title + venue
        if event_data.venue:
            queries.append(f"{event_data.title} {event_data.venue}")
            queries.append(f"{event_data.title} {event_data.venue} concert")

        # Title + city
        if event_data.location and event_data.location.city:
            queries.append(f"{event_data.title} {event_data.location.city}")
            queries.append(f"{event_data.title} {event_data.location.city} concert")

        # Title + date
        if event_data.date:
            queries.append(f"{event_data.title} {event_data.date}")
            queries.append(f"{event_data.title} {event_data.date} concert")

        # Add some generic queries
        if artist:
            queries.append(f"{artist} live performance")
            queries.append(f"{artist} concert photo")

        # Remove duplicates while preserving order
        seen = set()
        return [q for q in queries if not (q in seen or seen.add(q))]

    def _extract_artist_from_title(self, title: str) -> Optional[str]:
        """Extract artist name from event title."""
        # Common patterns to remove
        patterns = [
            r"\s*-\s*.*$",  # Everything after a dash
            r"\s*:.*$",  # Everything after a colon
            r"\s*\(.*\)",  # Everything in parentheses
            r"\s*\[.*\]",  # Everything in brackets
            r"\s*feat\..*$",  # Everything after "feat."
            r"\s*w/\s*.*$",  # Everything after "w/"
            r"\s*with\s+.*$",  # Everything after "with"
            r"\s*presents\s+.*$",  # Everything after "presents"
            r"\s*tour\s*$",  # "tour" at the end
            r"\s*live\s*$",  # "live" at the end
            r"\s*concert\s*$",  # "concert" at the end
            r"\s*show\s*$",  # "show" at the end
        ]

        # Apply patterns
        artist = title
        for pattern in patterns:
            artist = re.sub(pattern, "", artist, flags=re.IGNORECASE)

        # Clean up
        artist = artist.strip()
        if not artist:
            return None

        return artist

    @handle_errors_async(reraise=True)
    async def _search_google_images(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for images using Google Custom Search API."""
        if not self.google_enabled:
            return []

        # Build the search URL
        base_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.config.api.google_api_key,
            "cx": self.config.api.google_cse_id,
            "q": query,
            "searchType": "image",
            "num": min(limit, 10),  # Google limits to 10 per request
            "safe": "active",
            "imgType": "photo",
            "imgSize": "large",
            "rights": "cc_publicdomain|cc_attribute|cc_sharealike",
        }

        # Make the request
        response = await self.http.get(
            base_url,
            params=params,
            service="Google",
        )

        # Parse results
        results = response.get("items", [])
        return results
