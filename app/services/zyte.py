"""Zyte API service for web scraping."""

from __future__ import annotations

import base64
import logging
from typing import Any

from app.config import Config
from app.errors import APIError, SecurityPageError
from app.services.security_detector import SecurityPageDetector
from app.shared.http import HTTPService

logger = logging.getLogger(__name__)


class ZyteService:
    """Service for interacting with the Zyte API."""

    def __init__(self: ZyteService, config: Config, http_service: HTTPService) -> None:
        """Initialize Zyte service."""
        self.config = config
        self.http = http_service

    async def fetch_html(self: ZyteService, url: str) -> str:
        """Fetch HTML from a URL using Zyte API.
        This version has retries removed to simplify error handling.
        """
        payload = {
            "url": url,
            "browserHtml": True,
            "javascript": True,
            "actions": [
                {
                    "action": "waitForTimeout",
                    "timeout": self.config.zyte.javascript_wait,
                },
            ],
        }
        if self.config.zyte.use_residential_proxy:
            payload["geolocation"] = self.config.zyte.geolocation

        try:
            html, response_url = await self._make_request(payload)

            # Check for security pages
            is_security, reason = SecurityPageDetector.detect_security_page(
                html, response_url,
            )
            if is_security:
                # Log a warning with details
                logger.warning(f"Security page detected for {url}: {reason}")
                raise SecurityPageError(reason, url=url)

            return html
        except Exception as e:
            if not isinstance(e, SecurityPageError | APIError):
                logger.exception(f"Zyte HTML fetch failed for {url}")
            raise

    async def fetch_screenshot(self: ZyteService, url: str) -> tuple[bytes, str]:
        """Fetch a screenshot of a web page using Zyte API.
        This version has retries removed to simplify error handling.
        """
        payload = {
            "url": url,
            "screenshot": True,
            "screenshotOptions": {
                "fullPage": self.config.zyte.screenshot_full_page,
            },
            "javascript": True,
            "actions": [
                {
                    "action": "waitForTimeout",
                    "timeout": self.config.zyte.javascript_wait,
                },
            ],
        }
        if self.config.zyte.use_residential_proxy:
            payload["geolocation"] = self.config.zyte.geolocation

        try:
            image_bytes, _ = await self._make_request(payload, is_screenshot=True)
        except Exception as e:
            if not isinstance(e, SecurityPageError | APIError):
                logger.exception(f"Zyte screenshot fetch failed for {url}")
            raise
        else:
            return image_bytes, "image/png"  # Zyte screenshots are PNGs

    async def _make_request(
        self: ZyteService, payload: dict[str, Any], is_screenshot: bool = False,
    ) -> tuple[Any, str]:
        """Make the actual request to Zyte API."""
        if not self.config.api.zyte_key:
            service_name = "Zyte"
            error_msg = "No API key provided"
            raise APIError(service_name, error_msg)

        try:
            response = await self.http.post_json(
                self.config.zyte.api_url,
                service="Zyte",
                json=payload,
                auth=(self.config.api.zyte_key or "", ""),
            )

            response_url = response.get("url", payload["url"])

            if is_screenshot:
                if "screenshot" not in response:
                    service_name = "Zyte"
                    error_msg = "No screenshot in response"
                    raise APIError(service_name, error_msg)
                screenshot_b64 = response["screenshot"]
                screenshot_data = base64.b64decode(screenshot_b64)
                return screenshot_data, response_url
            if "browserHtml" not in response:
                service_name = "Zyte"
                error_msg = "No HTML in response"
                raise APIError(service_name, error_msg)
            return response["browserHtml"], response_url

        except Exception as e:
            logger.debug(f"Zyte request failed: {e}")
            service_name = "Zyte"
            error_msg = f"Request failed: {e}"
            raise APIError(service_name, error_msg) from e
