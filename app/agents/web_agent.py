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
