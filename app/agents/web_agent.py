"""Generic web scraping agent using Zyte and Claude with improved image enhancement."""

from __future__ import annotations

import logging
import re
from typing import Any

from bs4 import BeautifulSoup, Comment

from app.errors import SecurityPageError
from app.schemas import (
    EventData,
    ImageCandidate,
    ImageSearchResult,
    ImportMethod,
    ImportStatus,
)
from app.services.image import ImageService
from app.services.llm import LLMService
from app.services.zyte import ZyteService
from app.shared.agent import Agent
from app.shared.http import HTTPService

logger = logging.getLogger(__name__)


class WebAgent(Agent):
    """
    Agent for importing events from a generic webpage.
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
        self: WebAgent, url: str, request_id: str
    ) -> EventData | None:
        """Import event by scraping web page with enhanced error handling."""
        self.start_timer()

        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Initializing web scraper", 0.05
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
                    request_id, ImportStatus.RUNNING, "Starting image enhancement", 0.85
                )

                # Get more detailed progress during image enhancement
                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    "Building image search queries",
                    0.87,
                )

                event_data = await self._enhance_image_with_progress(
                    event_data, request_id
                )
            else:
                logger.info(
                    "Google image search not configured, skipping image enhancement"
                )
                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    "Image enhancement disabled (no Google API)",
                    0.9,
                )

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
        self: WebAgent, url: str, request_id: str
    ) -> EventData | None:
        """Try to extract from HTML with detailed progress reporting."""
        # Fetch HTML
        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Fetching web page HTML", 0.1
        )
        html = await self.zyte.fetch_html(url)

        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Cleaning HTML content", 0.2
        )

        # Clean HTML
        cleaned_html = self._clean_html(html)

        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Extracting event data from HTML", 0.3
        )

        # Extract with LLM service - it will generate descriptions if needed
        try:
            llm_service = self.get_service("llm")
            return await llm_service.extract_from_html(cleaned_html, url)
        except Exception as e:
            logger.error(f"Failed to extract from HTML using LLM: {e}")
            return None

    async def _try_screenshot_extraction(
        self: WebAgent, url: str, request_id: str
    ) -> EventData | None:
        """Try to extract from screenshot with detailed progress reporting."""
        # Get screenshot
        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Taking page screenshot", 0.65
        )
        screenshot_data, mime_type = await self.zyte.fetch_screenshot(url)

        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Extracting data from screenshot", 0.75
        )

        # Extract with LLM service - it will generate descriptions if needed
        try:
            llm_service = self.get_service("llm")
            return await llm_service.extract_from_image(
                screenshot_data, mime_type, url
            )
        except Exception as e:
            logger.error(f"Failed to extract from screenshot using LLM: {e}")
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

    async def _enhance_image(self: WebAgent, event_data: EventData) -> EventData:
        """Try to find a better image for the event with detailed progress reporting."""
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
            logger.info("Rating original image...")
            original_candidate = await self.image_service.rate_image(original_url)
            original_candidate.source = "original"
            search_result.original = original_candidate
            logger.info(f"Original image score: {original_candidate.score}")

        # Search for additional images
        try:
            logger.info(f"Building search queries for: {event_data.title}")
            if event_data.lineup:
                logger.info(f"Using lineup: {event_data.lineup}")

            # Build search queries and show them
            queries = self.image_service._build_search_queries(event_data)
            logger.info(f"Generated {len(queries)} search queries: {queries}")

            search_candidates = []
            for i, query in enumerate(queries):
                logger.info(f"Searching with query {i + 1}/{len(queries)}: '{query}'")
                try:
                    query_results = await self.image_service._search_google_images(
                        query, 5
                    )
                    logger.info(
                        f"Query '{query}' returned {len(query_results)} results"
                    )

                    for result in query_results:
                        url = result.get("link")
                        if url and not any(c.url == url for c in search_candidates):
                            search_candidates.append(
                                ImageCandidate(url=url, source=f"query_{i + 1}")
                            )
                except Exception as e:
                    logger.warning(f"Search query '{query}' failed: {e}")

            logger.info(f"Found {len(search_candidates)} unique image candidates")

            # Rate each candidate with progress
            rated_candidates = []
            for i, candidate in enumerate(search_candidates):
                logger.info(
                    f"Rating image {i + 1}/{len(search_candidates)}: {candidate.url}"
                )
                try:
                    rated = await self.image_service.rate_image(candidate.url)
                    rated.source = candidate.source
                    if rated.score > 0:
                        rated_candidates.append(rated)
                        logger.info(
                            f"Image {i + 1} score: {rated.score} ({rated.reason})"
                        )
                    else:
                        logger.info(f"Image {i + 1} rejected: {rated.reason}")
                except Exception as e:
                    logger.warning(f"Failed to rate image {candidate.url}: {e}")

            search_result.candidates = rated_candidates

            # Choose the best candidate
            best_candidate = search_result.get_best_candidate()

            if best_candidate and best_candidate.url != original_url:
                logger.info(
                    f"Selected better image: {best_candidate.url} (score: {best_candidate.score}, source: {best_candidate.source})"
                )

                # Update event data with the new image
                event_data.images = {
                    "full": best_candidate.url,
                    "thumbnail": best_candidate.url,  # Use full for thumbnail as well for simplicity
                }
                search_result.selected = best_candidate

            else:
                logger.info("No better image found, keeping original")
                if search_result.original:
                    search_result.selected = search_result.original

            # Store the search result in event data for debugging/analysis
            event_data.image_search = search_result

        except Exception as e:
            logger.error(f"Image enhancement failed: {e}")
            # Don't fail the entire import if image enhancement fails

        return event_data

    async def _enhance_image_with_progress(
        self: WebAgent, event_data: EventData, request_id: str
    ) -> EventData:
        """Enhance image with detailed progress reporting."""
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
            await self.send_progress(
                request_id, ImportStatus.RUNNING, "Rating original image", 0.88
            )
            logger.info("Rating original image...")
            original_candidate = await self.image_service.rate_image(original_url)
            original_candidate.source = "original"
            search_result.original = original_candidate
            logger.info(f"Original image score: {original_candidate.score}")

        # Search for additional images
        try:
            logger.info(f"Building search queries for: {event_data.title}")
            if event_data.lineup:
                logger.info(f"Using lineup: {event_data.lineup}")

            # Build search queries and show them
            queries = self.image_service._build_search_queries(event_data)
            logger.info(f"Generated {len(queries)} search queries: {queries}")

            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                f"Searching with {len(queries)} queries",
                0.89,
            )

            search_candidates = []
            for i, query in enumerate(queries):
                logger.info(f"Searching with query {i + 1}/{len(queries)}: '{query}'")
                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    f"Query {i + 1}/{len(queries)}: '{query[:30]}...'",
                    0.89 + (i * 0.02),
                )
                try:
                    query_results = await self.image_service._search_google_images(
                        query, 5
                    )
                    logger.info(
                        f"Query '{query}' returned {len(query_results)} results"
                    )

                    for result in query_results:
                        url = result.get("link")
                        if url and not any(c.url == url for c in search_candidates):
                            search_candidates.append(
                                ImageCandidate(url=url, source=f"query_{i + 1}")
                            )
                except Exception as e:
                    logger.warning(f"Search query '{query}' failed: {e}")

            logger.info(f"Found {len(search_candidates)} unique image candidates")

            # Rate each candidate with progress
            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                f"Rating {len(search_candidates)} image candidates",
                0.93,
            )

            rated_candidates = []
            for i, candidate in enumerate(search_candidates):
                logger.info(
                    f"Rating image {i + 1}/{len(search_candidates)}: {candidate.url}"
                )
                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    f"Rating image {i + 1}/{len(search_candidates)}",
                    0.93 + (i * 0.005),
                )
                try:
                    rated = await self.image_service.rate_image(candidate.url)
                    rated.source = candidate.source
                    if rated.score > 0:
                        rated_candidates.append(rated)
                        logger.info(
                            f"Image {i + 1} score: {rated.score} ({rated.reason})"
                        )
                    else:
                        logger.info(f"Image {i + 1} rejected: {rated.reason}")
                except Exception as e:
                    logger.warning(f"Failed to rate image {candidate.url}: {e}")

            search_result.candidates = rated_candidates

            # Choose the best candidate
            await self.send_progress(
                request_id, ImportStatus.RUNNING, "Selecting best image", 0.96
            )

            best_candidate = search_result.get_best_candidate()

            if best_candidate and best_candidate.url != original_url:
                logger.info(
                    f"Selected better image: {best_candidate.url} (score: {best_candidate.score}, source: {best_candidate.source})"
                )

                # Update event data with the new image
                event_data.images = {
                    "full": best_candidate.url,
                    "thumbnail": best_candidate.url,  # Use full for thumbnail as well for simplicity
                }
                search_result.selected = best_candidate

                await self.send_progress(
                    request_id,
                    ImportStatus.RUNNING,
                    f"Enhanced image (score: {best_candidate.score})",
                    0.98,
                )

            else:
                logger.info("No better image found, keeping original")
                if search_result.original:
                    search_result.selected = search_result.original

                await self.send_progress(
                    request_id, ImportStatus.RUNNING, "Keeping original image", 0.98
                )

            # Store the search result in event data for debugging/analysis
            event_data.image_search = search_result

        except Exception as e:
            logger.error(f"Image enhancement failed: {e}")
            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                f"Image enhancement failed: {str(e)[:50]}",
                0.95,
            )
            # Don't fail the entire import if image enhancement fails

        return event_data
