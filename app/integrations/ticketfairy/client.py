"""TicketFairy API client for submitting events."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.error_messages import CommonMessages
from app.errors import APIError, handle_errors_async
from app.integrations.base import BaseClient
from app.shared.http import get_http_service

from .config import get_ticketfairy_config

logger = logging.getLogger(__name__)


class TicketFairyClient(BaseClient):
    """Client for submitting events to TicketFairy API."""

    def __init__(self: TicketFairyClient) -> None:
        self.http = get_http_service()
        self.config = get_ticketfairy_config()

    @handle_errors_async(reraise=True)
    async def submit(self: TicketFairyClient, data: dict[str, Any]) -> dict[str, Any]:
        """Submit event data to TicketFairy.

        Args:
            data: Event data to submit

        Returns:
            API response data

        Raises:
            APIError: On API errors
            ValueError: If API key not configured

        """
        if not self.config.api_key:
            error_msg = "TicketFairy API key not configured"
            raise ValueError(error_msg)

        # Prepare headers
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": self.config.origin,
        }

        # Make request using the lower-level post method to handle custom response parsing
        response = await self.http.post(
            f"{self.config.api_base_url}{self.config.draft_events_endpoint}",
            service="TicketFairy",
            headers=headers,
            json=data,
            timeout=self.config.timeout,
            raise_for_status=False,
        )

        # Handle empty response
        response_text = await response.text()
        if not response_text or response_text.strip() == "":
            service_name = "TicketFairy"
            error_msg = "Empty response from API"
            raise APIError(service_name, error_msg)

        # Parse response
        try:
            response_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            service_name = "TicketFairy"
            error_msg = f"Invalid JSON response: {e}. Response: {response_text}"
            raise APIError(service_name, error_msg) from e

        # Check for API errors
        if response.status >= 400:
            error_msg = CommonMessages.UNEXPECTED_ERROR
            if isinstance(response_data, dict):
                if "message" in response_data:
                    error_msg = response_data["message"]
                elif "error" in response_data:
                    error_msg = response_data["error"]

        return response_data
