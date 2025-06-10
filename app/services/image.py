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
from app.errors import retry_on_error


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

        # Skip avoided domains
        if any(domain in url.lower() for domain in self.AVOID_DOMAINS):
            candidate.score = 0
            candidate.reason = "avoided_domain"
            return candidate

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

        except Exception as e:
            logger.debug(f"Failed to rate image {url}: {e}")
            candidate.score = 0
            candidate.reason = "rating_failed"

        return candidate

    @retry_on_error(max_attempts=2)
    async def search_event_images(
        self, event_data: EventData, limit: int = 10
    ) -> List[ImageCandidate]:
        """Search for event images using Google Custom Search."""
        if not self.google_enabled:
            logger.debug("Google search not enabled")
            return []

        # Build search queries
        queries = self._build_search_queries(event_data)
        if not queries:
            logger.warning("No search queries could be built from event data")
            return []

        all_candidates = []
        seen_urls = set()

        for query in queries[:2]:  # Limit to 2 queries to avoid rate limits
            logger.info(f"🔎 Searching Google Images for: {query}")

            try:
                results = await self._search_google_images(query, limit=limit)

                for item in results:
                    url = item.get("link")
                    if not url or url in seen_urls:
                        continue

                    seen_urls.add(url)

                    # Create candidate with metadata
                    candidate = ImageCandidate(
                        url=url,
                        source="google_search",
                    )

                    # Add context info if available
                    if item.get("image", {}).get("width"):
                        candidate.dimensions = f"{item['image']['width']}x{item['image'].get('height', '?')}"

                    all_candidates.append(candidate)

                # Brief delay between searches
                if len(queries) > 1:
                    await self.http._ensure_session()  # Keep session alive

            except Exception as e:
                logger.error(f"Search query failed for '{query}': {e}")
                continue

        logger.info(f"Found {len(all_candidates)} unique image URLs from search")
        return all_candidates

    def _build_search_queries(self, event_data: EventData) -> List[str]:
        """Build effective search queries from event data."""
        queries = []

        # Extract key information
        artists = event_data.lineup[:2] if event_data.lineup else []  # Top 2 artists
        venue = event_data.venue
        title = event_data.title
        genres = event_data.genres[:2] if event_data.genres else []  # Top 2 genres

        # Clean title to extract potential artist name
        title_artist = self._extract_artist_from_title(title)

        # Strategy 1: Primary artist + specific terms
        if artists and artists[0]:
            artist = artists[0]
            queries.extend(
                [
                    f'"{artist}" band photo',
                    f'"{artist}" musician official',
                    f'"{artist}" concert poster',
                ]
            )
        elif title_artist:
            queries.extend(
                [
                    f'"{title_artist}" band photo',
                    f'"{title_artist}" musician',
                ]
            )

        # Strategy 2: Full event title (might find actual event posters)
        if title:
            # Clean up title for search
            clean_title = re.sub(r"\s+presents?\s+", " ", title, flags=re.IGNORECASE)
            clean_title = re.sub(r"\s+at\s+.*$", "", clean_title, flags=re.IGNORECASE)
            if clean_title and clean_title != title:
                queries.append(f'"{clean_title}" event poster')

        # Strategy 3: Venue + genre (for venue-specific events)
        if venue and genres:
            queries.append(f'"{venue}" {genres[0]} concert')

        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q.lower() not in seen:
                seen.add(q.lower())
                unique_queries.append(q)

        return unique_queries[:3]  # Return top 3 queries

    def _extract_artist_from_title(self, title: str) -> Optional[str]:
        """Extract likely artist name from event title."""
        if not title:
            return None

        # Common patterns in event titles
        patterns = [
            r"^(.+?)\s+(?:live\s+)?at\s+",  # "Artist at Venue"
            r"^(.+?)\s+presents?\s+",  # "Venue presents Artist"
            r"^(.+?)\s+\|\s+",  # "Artist | Venue"
            r"^(.+?)\s+[-–]\s+",  # "Artist - Date"
            r"^(.+?)\s+\(",  # "Artist (info)"
            r"^(.+?)\s+w(?:ith)?\/",  # "Artist w/ Support"
        ]

        for pattern in patterns:
            match = re.match(pattern, title, re.IGNORECASE)
            if match:
                artist = match.group(1).strip()
                # Filter out common venue names or generic terms
                if artist.lower() not in [
                    "the",
                    "dj",
                    "live",
                    "show",
                    "event",
                    "night",
                ]:
                    return artist

        # If no pattern matches, check if title is just an artist name
        # (no common venue/event words)
        venue_words = ["venue", "club", "hall", "theater", "theatre", "center", "house"]
        if not any(word in title.lower() for word in venue_words):
            # Remove trailing event info
            clean = re.sub(r"\s*\([^)]+\)\s*$", "", title)  # Remove parentheses
            clean = re.sub(
                r"\s+(?:tour|show|live|concert).*$", "", clean, flags=re.IGNORECASE
            )
            if clean and len(clean) < 50:  # Reasonable length for artist name
                return clean.strip()

        return None

    async def _search_google_images(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Execute Google Custom Search API request."""
        params = {
            "key": self.config.api.google_api_key,
            "cx": self.config.api.google_cse_id,
            "q": query,
            "searchType": "image",
            "num": min(limit, 10),  # API max is 10
            "imgSize": "large",
            "imgType": "photo",
            "safe": "off",
            "fileType": "jpg,png,webp",
        }

        try:
            response = await self.http.get_json(
                "https://www.googleapis.com/customsearch/v1",
                service="Google",
                params=params,
                timeout=15,
            )

            if "items" not in response:
                logger.debug(f"No results for query: {query}")
                return []

            return response["items"]

        except Exception as e:
            logger.error(f"Google Custom Search failed: {e}")
            raise

    async def find_best_image(
        self, event_data: EventData, original_url: Optional[str] = None
    ) -> Optional[ImageCandidate]:
        """Find the best image for an event."""
        candidates = []

        # Rate original if provided
        if original_url:
            logger.info(f"Rating original image: {original_url}")
            original = await self.rate_image(original_url)
            original.source = "original"
            if original.score > 0:
                candidates.append(original)
                logger.info(f"Original image score: {original.score}")

        # Search for additional images if enabled
        if self.google_enabled:
            logger.info("Searching for additional event images...")
            search_results = await self.search_event_images(event_data)

            # Rate each search result
            for i, candidate in enumerate(search_results):
                logger.debug(
                    f"Rating search result {i+1}/{len(search_results)}: {candidate.url}"
                )
                rated = await self.rate_image(candidate.url)
                rated.source = "google_search"
                if rated.score > 0:
                    candidates.append(rated)

            logger.info(f"Rated {len(candidates)} total images")

        # Return best candidate
        if candidates:
            best = max(candidates, key=lambda c: c.score)
            logger.info(
                f"Best image (score={best.score}, source={best.source}): {best.url}"
            )
            return best

        logger.warning("No suitable images found")
        return None
