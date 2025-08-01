"""Generic web scraping agent using Zyte and Claude with improved image enhancement."""

from __future__ import annotations

import logging
import re
from typing import Any

from bs4 import BeautifulSoup, Comment

from app.core.error_messages import AgentMessages
from app.core.errors import SecurityPageError
from app.core.schemas import (
    EventData,
    ImportMethod,
    ImportStatus,
)
from app.extraction_agents.base import BaseExtractionAgent
from app.services.llm.service import LLMService
from app.services.zyte import ZyteService
from app.shared.timezone import get_timezone_from_location

logger = logging.getLogger(__name__)


class Web(BaseExtractionAgent):
    """Agent for importing events from a generic webpage."""

    llm: LLMService
    zyte: ZyteService

    def __init__(self, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> None:
        super().__init__(*args, **kwargs)
        self.llm = self.get_service("llm")
        self.zyte = self.get_service("zyte")

    @property
    def name(self: Web) -> str:
        return "WebScraper"

    @property
    def import_method(self: Web) -> ImportMethod:
        return ImportMethod.WEB

    async def _perform_extraction(
        self: Web,
        url: str,
        request_id: str,
    ) -> EventData | None:
        """Provider-specific logic for web scraping."""
        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Initializing web scraper",
            0.05,
        )
        try:
            event_data = await self._try_html_extraction(url, request_id)
            if not event_data:
                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    "HTML extraction failed, trying screenshot",
                    0.6,
                )
                event_data = await self._try_screenshot_extraction(url, request_id)
            if not event_data:
                raise Exception(AgentMessages.WEB_EXTRACTION_FAILED)
            return event_data
        except SecurityPageError:
            raise

    async def _try_html_extraction(
        self: Web,
        url: str,
        request_id: str,
    ) -> EventData | None:
        """Try to extract from HTML with detailed progress reporting."""
        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Fetching web page HTML", 0.1
        )
        html = await self.zyte.fetch_html(url)
        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Cleaning HTML content", 0.2
        )
        cleaned_html = self._clean_html(html)
        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Extracting event data from HTML", 0.3
        )
        try:
            event_data = await self.llm.extract_from_html(
                cleaned_html,
                url,
                needs_long_description=True,
                needs_short_description=True,
            )
            if (
                event_data
                and event_data.time
                and not event_data.time.timezone
                and event_data.location
            ):
                event_data.time.timezone = get_timezone_from_location(
                    event_data.location
                )
            return event_data
        except Exception:
            logger.exception("Failed to extract from HTML using LLM")
            return None

    async def _try_screenshot_extraction(
        self: Web,
        url: str,
        request_id: str,
    ) -> EventData | None:
        """Try to extract from screenshot with detailed progress reporting."""
        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Taking page screenshot", 0.65
        )
        screenshot_data, mime_type = await self.zyte.fetch_screenshot(url)
        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Extracting data from screenshot", 0.75
        )
        try:
            event_data = await self.llm.extract_from_image(
                screenshot_data,
                mime_type,
                url,
                needs_long_description=True,
                needs_short_description=True,
            )
            if (
                event_data
                and event_data.time
                and not event_data.time.timezone
                and event_data.location
            ):
                event_data.time.timezone = get_timezone_from_location(
                    event_data.location
                )
            return event_data
        except Exception:
            logger.exception("Failed to extract from screenshot using LLM")
            return None

    def _clean_html(self, html: str) -> str:
        """Clean HTML by removing unnecessary elements."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            for element in soup.find_all(
                ["script", "style", "link", "meta", "svg", "noscript"]
            ):
                element.decompose()
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            cleaned = str(soup)
            cleaned = re.sub(r'style="[^"]*"', "", cleaned)
            cleaned = re.sub(r"style='[^']*'", "", cleaned)
            cleaned = re.sub(r'data-[a-zA-Z0-9\-]+="[^"]*"', "", cleaned)
            cleaned = re.sub(r"data-[a-zA-Z0-9\-]+='[^']*'", "", cleaned)
            cleaned = re.sub(r'onclick="[^"]*"', "", cleaned)
            cleaned = re.sub(r'onload="[^"]*"', "", cleaned)
            cleaned = re.sub(r"\s+", " ", cleaned)
            cleaned = re.sub(r">\s+<", "><", cleaned)
            original_size, cleaned_size = len(html), len(cleaned)
            reduction = (1 - cleaned_size / original_size) * 100
            logger.info(
                f"HTML cleaned: {original_size:,} -> {cleaned_size:,} chars ({reduction:.1f}% reduction)"
            )
            return cleaned
        except Exception:
            logger.exception("Error cleaning HTML")
            return html
