"""Generic web scraping agent using Zyte and Claude with improved image enhancement."""

from __future__ import annotations

import logging
import re
from typing import Any

from bs4 import BeautifulSoup, Comment

from app.error_messages import AgentMessages
from app.errors import SecurityPageError
from app.schemas import (
    EventData,
    ImportMethod,
    ImportStatus,
)
from app.services.image import ImageService
from app.services.llm import LLMService
from app.services.zyte import ZyteService
from app.shared.agent import Agent
from app.shared.http import HTTPService
from app.shared.timezone import get_timezone_from_location

logger = logging.getLogger(__name__)


class WebAgent(Agent):
    """Agent for importing events from a generic webpage.
    This is the fallback agent when no specific agent matches.
    """

    llm: LLMService
    http: HTTPService
    image_service: ImageService
    zyte: ZyteService

    def __init__(self, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> None:
        super().__init__(*args, **kwargs)
        # Use shared services with proper error handling
        self.llm = self.get_service("llm")
        self.http = self.get_service("http")
        self.image_service = self.get_service("image")
        self.zyte = self.get_service("zyte")

    @property
    def name(self: WebAgent) -> str:
        return "WebScraper"

    @property
    def import_method(self: WebAgent) -> ImportMethod:
        return ImportMethod.WEB

    async def import_event(
        self: WebAgent,
        url: str,
        request_id: str,
    ) -> EventData | None:
        """Import event by scraping web page with enhanced error handling."""
        self.start_timer()

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Initializing web scraper",
            0.05,
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
                error_msg = AgentMessages.WEB_EXTRACTION_FAILED
                raise Exception(error_msg)

            # Enhance image if web extraction and Google is enabled
            if self.image_service.google_enabled:
                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    "Starting image enhancement",
                    0.85,
                )
                event_data = await self._enhance_image_with_progress(
                    event_data,
                    request_id,
                )
            else:
                logger.info(
                    "Google image search not configured, skipping image enhancement",
                )
                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    "Image enhancement disabled (no Google API)",
                    0.9,
                )

            # Generate and enhance descriptions
            if event_data:
                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    "Enhancing descriptions",
                    0.98,
                )
                try:
                    llm_service = self.get_service("llm")
                    event_data = await llm_service.generate_descriptions(event_data)
                except (ValueError, TypeError, KeyError):
                    logger.exception("Description enhancement failed")
                    # Continue without descriptions rather than failing completely

            await self.send_progress(
                request_id,
                ImportStatus.SUCCESS,
                "Successfully imported event",
                1.0,
                data=event_data,
            )

            return event_data

        except SecurityPageError:
            # Re-raise security page errors to be handled by the main importer.
            # This provides a clearer error message to the user and prevents fallback
            # to other methods that will also fail.
            raise
        except Exception as e:
            logger.exception("Web import failed")
            await self.send_progress(
                request_id,
                ImportStatus.FAILED,
                f"Import failed: {e!s}",
                1.0,
                error=str(e),
            )
            return None

    async def _try_html_extraction(
        self: WebAgent,
        url: str,
        request_id: str,
    ) -> EventData | None:
        """Try to extract from HTML with detailed progress reporting."""
        # Fetch HTML
        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Fetching web page HTML",
            0.1,
        )
        html = await self.zyte.fetch_html(url)

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Cleaning HTML content",
            0.2,
        )

        # Clean HTML
        cleaned_html = self._clean_html(html)

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Extracting event data from HTML",
            0.3,
        )

        # Extract with LLM service - it will generate descriptions if needed
        try:
            llm_service = self.get_service("llm")
            event_data = await llm_service.extract_from_html(cleaned_html, url)

            # Post-process: Add timezone if missing but location is available
            if (
                event_data
                and event_data.time
                and not event_data.time.timezone
                and event_data.location
            ):
                timezone = get_timezone_from_location(event_data.location)
                event_data.time.timezone = timezone

            return event_data
        except Exception:
            logger.exception("Failed to extract from HTML using LLM")
            return None

    async def _try_screenshot_extraction(
        self: WebAgent,
        url: str,
        request_id: str,
    ) -> EventData | None:
        """Try to extract from screenshot with detailed progress reporting."""
        # Get screenshot
        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Taking page screenshot",
            0.65,
        )
        screenshot_data, mime_type = await self.zyte.fetch_screenshot(url)

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Extracting data from screenshot",
            0.75,
        )

        # Extract with LLM service - it will generate descriptions if needed
        try:
            llm_service = self.get_service("llm")
            event_data = await llm_service.extract_from_image(
                screenshot_data,
                mime_type,
                url,
            )

            # Post-process: Add timezone if missing but location is available
            if (
                event_data
                and event_data.time
                and not event_data.time.timezone
                and event_data.location
            ):
                timezone = get_timezone_from_location(event_data.location)
                event_data.time.timezone = timezone

            return event_data
        except Exception:
            logger.exception("Failed to extract from screenshot using LLM")
            return None

    def _clean_html(self, html: str) -> str:
        """Clean HTML by removing unnecessary elements that bloat the content.
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
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
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
                f"HTML cleaned: {original_size:,} -> {cleaned_size:,} chars ({reduction:.1f}% reduction)",
            )

            return cleaned

        except Exception:
            logger.exception("Error cleaning HTML")
            # If cleaning fails, return original
            return html

    async def _enhance_image_with_progress(
        self: WebAgent,
        event_data: EventData,
        request_id: str,
    ) -> EventData:
        """Enhance image by calling the ImageService, with progress reporting."""
        logger.info("Starting image enhancement process via ImageService")

        # The enhancement process runs from 85% to 98% of the total import time
        base_progress = 0.85
        progress_range = 0.13  # 0.98 - 0.85

        async def progress_callback(message: str, service_percent: float) -> None:
            """Maps service progress (0.0-1.0) to agent's progress range."""
            agent_percent = base_progress + (service_percent * progress_range)
            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                message,
                agent_percent,
            )

        try:
            event_data = await self.image_service.enhance_event_image(
                event_data,
                progress_callback=progress_callback,
            )

            # Send a final status update for this stage
            final_message = "Image enhancement complete"
            if event_data.image_search and event_data.image_search.selected:
                final_message = f"Using enhanced image (score: {event_data.image_search.selected.score})"
            elif event_data.image_search and event_data.image_search.original:
                final_message = f"Keeping original image (score: {event_data.image_search.original.score})"

            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                final_message,
                base_progress + progress_range,
            )

        except Exception as e:
            logger.exception("Image enhancement failed")
            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                f"Image enhancement failed: {str(e)[:50]}",
                base_progress + progress_range,
            )
            # Don't fail the entire import if image enhancement fails

        return event_data
