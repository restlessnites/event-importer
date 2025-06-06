"""Generic web scraping agent using Zyte and Claude with improved image enhancement."""

import logging
from typing import Optional
from bs4 import BeautifulSoup

from app.agent import Agent
from app.schemas import EventData, ImportMethod, ImportStatus, ImageSearchResult


logger = logging.getLogger(__name__)


class WebAgent(Agent):
    """Agent for importing events from generic web pages."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use shared services from parent
        self.http = self.services["http"]
        self.zyte = self.services["zyte"]
        self.claude = self.services["claude"]
        self.image_service = self.services["image"]

    @property
    def name(self) -> str:
        return "WebScraper"

    @property
    def import_method(self) -> ImportMethod:
        return ImportMethod.WEB

    def can_handle(self, url: str) -> bool:
        """
        This method is not used for WebAgent since the importer
        routes HTML content to it by checking content-type.
        """
        return False

    async def import_event(self, url: str, request_id: str) -> Optional[EventData]:
        """Import event by scraping web page."""
        self.start_timer()

        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Fetching web page", 0.1
        )

        try:
            # Try HTML extraction first
            event_data = await self._try_html_extraction(url, request_id)

            # If HTML failed, try screenshot
            if not event_data:
                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    "HTML extraction failed, trying screenshot",
                    0.6,
                )
                event_data = await self._try_screenshot_extraction(url, request_id)

            if not event_data:
                raise Exception("Could not extract event data")

            # Enhance image if web extraction and Google is enabled
            if self.image_service.google_enabled:
                await self.send_progress(
                    request_id, ImportStatus.RUNNING, "Searching for better images", 0.9
                )
                event_data = await self._enhance_image(event_data)
            else:
                logger.info(
                    "Google image search not configured, skipping image enhancement"
                )

            await self.send_progress(
                request_id,
                ImportStatus.SUCCESS,
                "Successfully imported event",
                1.0,
                data=event_data,
            )

            return event_data

        except Exception as e:
            logger.error(f"Web import failed: {e}")
            await self.send_progress(
                request_id,
                ImportStatus.FAILED,
                f"Import failed: {str(e)}",
                1.0,
                error=str(e),
            )
            return None

    async def _try_html_extraction(
        self, url: str, request_id: str
    ) -> Optional[EventData]:
        """Try to extract from HTML."""
        try:
            # Fetch HTML
            html = await self.zyte.fetch_html(url)

            await self.send_progress(
                request_id, ImportStatus.RUNNING, "Extracting data from HTML", 0.3
            )

            # Clean HTML
            cleaned_html = self._clean_html(html)

            # Extract with Claude - it will generate descriptions if needed
            return await self.claude.extract_from_html(cleaned_html, url)

        except Exception as e:
            logger.warning(f"HTML extraction failed: {e}")
            return None

    async def _try_screenshot_extraction(
        self, url: str, request_id: str
    ) -> Optional[EventData]:
        """Try to extract from screenshot."""
        try:
            # Get screenshot
            screenshot_data, mime_type = await self.zyte.fetch_screenshot(url)

            await self.send_progress(
                request_id, ImportStatus.RUNNING, "Extracting data from screenshot", 0.8
            )

            # Extract with Claude - it will generate descriptions if needed
            return await self.claude.extract_from_image(screenshot_data, mime_type, url)

        except Exception as e:
            logger.warning(f"Screenshot extraction failed: {e}")
            return None

    def _clean_html(self, html: str) -> str:
        """Remove unnecessary elements from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove script, style, and other non-content tags
        for tag in soup(["script", "style", "meta", "link", "noscript"]):
            tag.decompose()

        # Get text with minimal HTML structure
        return str(soup)

    async def _enhance_image(self, event_data: EventData) -> EventData:
        """Try to find a better image for the event."""
        logger.info("Starting image enhancement process")

        # Get original image URL if any
        original_url = None
        if event_data.images:
            original_url = event_data.images.get("full") or event_data.images.get(
                "thumbnail"
            )
            logger.info(f"Original image URL: {original_url}")

        # Initialize tracking
        search_result = ImageSearchResult()

        # Rate original if exists
        if original_url:
            original_candidate = await self.image_service.rate_image(original_url)
            original_candidate.source = "original"
            search_result.original = original_candidate
            logger.info(f"Original image score: {original_candidate.score}")

        # Search for additional images
        try:
            logger.info(f"Searching for images for event: {event_data.title}")
            if event_data.lineup:
                logger.info(f"Using lineup: {event_data.lineup}")

            search_candidates = await self.image_service.search_event_images(event_data)
            logger.info(f"Found {len(search_candidates)} search candidates")

            # Rate each candidate
            for candidate in search_candidates:
                rated = await self.image_service.rate_image(candidate.url)
                rated.source = candidate.source
                # Only add candidates with positive scores
                if rated.score > 0:
                    search_result.candidates.append(rated)

        except Exception as e:
            logger.error(f"Image search failed: {e}", exc_info=True)

        # Select best image
        best = search_result.get_best_candidate()
        if best:
            logger.info(
                f"Selected best image with score {best.score} from {best.source}"
            )
            search_result.selected = best

            # Update event images
            event_data.images = {
                "full": best.url,
                "thumbnail": best.url,
            }
        else:
            logger.warning("No suitable images found")
            # Remove broken image data if no valid images
            if search_result.original and search_result.original.score == 0:
                event_data.images = None

        # Always set the search result to track what happened
        event_data.image_search = search_result

        return event_data
