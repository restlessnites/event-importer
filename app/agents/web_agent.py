"""Generic web scraping agent using Zyte and Claude."""

import logging
from typing import Optional
from bs4 import BeautifulSoup

from app.agent import Agent
from app.schemas import EventData, ImportMethod, ImportStatus, ImageSearchResult
from app.services.zyte import ZyteService
from app.services.claude import ClaudeService
from app.services.image import ImageService
from app.http import get_http_service


logger = logging.getLogger(__name__)


class WebAgent(Agent):
    """Agent for importing events from generic web pages."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http = get_http_service()
        self.zyte = ZyteService(self.config, self.http)
        self.claude = ClaudeService(self.config)
        self.image_service = ImageService(self.config, self.http)

    @property
    def name(self) -> str:
        return "WebScraper"

    @property
    def import_method(self) -> ImportMethod:
        return ImportMethod.WEB

    def can_handle(self, url: str) -> bool:
        """
        This method is not used for WebAgent since the engine
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

            # Enhance image if web extraction
            if self.image_service.google_enabled:
                await self.send_progress(
                    request_id, ImportStatus.RUNNING, "Searching for better images", 0.9
                )
                event_data = await self._enhance_image(event_data)

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

            # Extract with Claude
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

            # Extract with Claude
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
        # Get original image URL if any
        original_url = None
        if event_data.images:
            original_url = event_data.images.get("full") or event_data.images.get(
                "thumbnail"
            )

        # Find best image
        best = await self.image_service.find_best_image(event_data, original_url)

        if best:
            # Track image search results
            search_result = ImageSearchResult()
            if original_url:
                original = await self.image_service.rate_image(original_url)
                original.source = "original"
                search_result.original = original

            search_result.selected = best
            event_data.image_search = search_result

            # Update main image
            event_data.images = {
                "full": best.url,
                "thumbnail": best.url,
            }

        return event_data
