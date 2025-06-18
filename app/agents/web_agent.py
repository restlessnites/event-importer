"""Generic web scraping agent using Zyte and Claude with improved image enhancement."""

import logging
from typing import Optional
from bs4 import BeautifulSoup, Comment
import re

from app.shared.agent import Agent
from app.schemas import EventData, ImportMethod, ImportStatus, ImageSearchResult
from app.errors import SecurityPageError

logger = logging.getLogger(__name__)


class WebAgent(Agent):
    """Agent for importing events from generic web pages."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use shared services from parent
        self.http = self.services["http"]
        self.zyte = self.services["zyte"]
        self.image_service = self.services["image"]

    @property
    def name(self) -> str:
        return "WebScraper"

    @property
    def import_method(self) -> ImportMethod:
        return ImportMethod.WEB

    async def import_event(self, url: str, request_id: str) -> Optional[EventData]:
        """Import event by scraping web page with enhanced error handling."""
        from app.errors import SecurityPageError
        
        self.start_timer()

        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Fetching web page", 0.1
        )

        try:
            # Try HTML extraction first
            event_data = await self._try_html_extraction(url, request_id)

            # If HTML failed, try screenshot (but not if it was a security page)
            if not event_data:
                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    "HTML extraction failed, trying screenshot",
                    0.6,
                )
                event_data = await self._try_screenshot_extraction(url, request_id)

            if not event_data:
                raise Exception("Could not extract event data from any method")

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

        except SecurityPageError as e:
            error_msg = f"Security page detected - website is blocking automated access: {e}"
            logger.error(f"Security page blocking import for {url}: {e}")
            await self.send_progress(
                request_id,
                ImportStatus.FAILED,
                error_msg,
                1.0,
                error=error_msg,
            )
            return None
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

    async def _try_html_extraction(self, url: str, request_id: str) -> Optional[EventData]:
        """Try to extract from HTML."""
        from app.errors import SecurityPageError
        
        try:
            # Fetch HTML
            html = await self.zyte.fetch_html(url)

            await self.send_progress(
                request_id, ImportStatus.RUNNING, "Extracting data from HTML", 0.3
            )

            # Clean HTML
            cleaned_html = self._clean_html(html)

            # Extract with Claude - it will generate descriptions if needed
            return await self.services["llm"].extract_from_html(cleaned_html, url)

        except SecurityPageError:
            # Re-raise security page errors - don't try screenshot on security pages
            raise
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
            return await self.services["llm"].extract_from_image(
                screenshot_data, mime_type, url
            )

        except Exception as e:
            logger.warning(f"Screenshot extraction failed: {e}")
            return None

    def _clean_html(self, html: str) -> str:
        """
        Clean HTML by removing unnecessary elements that bloat the content.
        This is generic and doesn't look for specific content.
        """
        try:
            # Parse the HTML
            soup = BeautifulSoup(html, "html.parser")

            # Remove script tags and their content
            for script in soup.find_all("script"):
                script.decompose()

            # Remove style tags and their content
            for style in soup.find_all("style"):
                style.decompose()

            # Remove link tags (usually CSS links)
            for link in soup.find_all("link"):
                link.decompose()

            # Remove meta tags
            for meta in soup.find_all("meta"):
                meta.decompose()

            # Remove comments
            for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
                comment.extract()

            # Remove svg tags (often huge icons)
            for svg in soup.find_all("svg"):
                svg.decompose()

            # Remove noscript tags
            for noscript in soup.find_all("noscript"):
                noscript.decompose()

            # Get the cleaned HTML
            cleaned = str(soup)

            # Additional text-based cleaning to remove inline styles and data attributes
            # Remove inline styles
            cleaned = re.sub(r'style="[^"]*"', "", cleaned)
            cleaned = re.sub(r"style='[^']*'", "", cleaned)

            # Remove data- attributes (often very long)
            cleaned = re.sub(r'data-[a-zA-Z0-9\\-]+="[^"]*"', "", cleaned)
            cleaned = re.sub(r"data-[a-zA-Z0-9\\-]+='[^']*'", "", cleaned)

            # Remove common tracking/analytics attributes
            cleaned = re.sub(r'onclick="[^"]*"', "", cleaned)
            cleaned = re.sub(r'onload="[^"]*"', "", cleaned)

            # Remove excessive whitespace
            cleaned = re.sub(r"\\s+", " ", cleaned)
            cleaned = re.sub(r">\\s+<", "><", cleaned)

            # Log the size reduction
            original_size = len(html)
            cleaned_size = len(cleaned)
            reduction = (1 - cleaned_size / original_size) * 100
            logger.info(
                f"HTML cleaned: {original_size:,} -> {cleaned_size:,} chars ({reduction:.1f}% reduction)"
            )

            return cleaned

        except Exception as e:
            logger.error(f"Error cleaning HTML: {e}")
            # If cleaning fails, return original
            return html

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
