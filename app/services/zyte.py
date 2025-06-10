"""Zyte API service for web scraping."""

import base64
import logging
from typing import Tuple

import aiohttp

from app.config import Config
from app.shared.http import HTTPService
from app.errors import APIError, retry_on_error


logger = logging.getLogger(__name__)


class ZyteService:
    """Service for Zyte web scraping API."""

    def __init__(self, config: Config, http_service: HTTPService):
        """Initialize Zyte service."""
        self.config = config
        self.http = http_service
        self.api_url = config.zyte.api_url
        self.api_key = config.api.zyte_key

    @retry_on_error(max_attempts=3)
    async def fetch_html(self, url: str) -> str:
        """Fetch rendered HTML from a URL."""
        payload = {
            "url": url,
            "browserHtml": True,
            "javascript": True,
            "actions": [
                {
                    "action": "waitForTimeout",
                    "timeout": self.config.zyte.javascript_wait,
                }
            ],
        }

        # Add optional settings
        if self.config.zyte.use_residential_proxy:
            payload["ipType"] = "residential"
        if self.config.zyte.geolocation:
            payload["geolocation"] = self.config.zyte.geolocation

        try:
            response = await self.http.post_json(
                self.api_url,
                service="Zyte",
                json=payload,
                auth=aiohttp.BasicAuth(self.api_key, ""),
            )

            if "browserHtml" not in response:
                raise APIError("Zyte", "No HTML in response")

            return response["browserHtml"]

        except Exception as e:
            logger.error(f"Zyte HTML fetch failed: {e}")
            raise

    @retry_on_error(max_attempts=2)
    async def fetch_screenshot(self, url: str) -> Tuple[bytes, str]:
        """Fetch screenshot of a URL."""
        payload = {
            "url": url,
            "screenshot": True,
            "screenshotOptions": {
                "fullPage": self.config.zyte.screenshot_full_page,
                "format": "jpeg",
            },
        }

        try:
            response = await self.http.post_json(
                self.api_url,
                service="Zyte",
                json=payload,
                auth=aiohttp.BasicAuth(self.api_key, ""),
                timeout=60,  # Screenshots take longer
            )

            if "screenshot" not in response:
                raise APIError("Zyte", "No screenshot in response")

            screenshot_b64 = response["screenshot"]
            screenshot_bytes = base64.b64decode(screenshot_b64)

            return screenshot_bytes, "image/jpeg"

        except Exception as e:
            logger.error(f"Zyte screenshot failed: {e}")
            raise
