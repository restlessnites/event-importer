"""TicketFairy API client for submitting events."""

import json
import logging
from typing import Dict, Any

from app.integrations.base import BaseClient
from app.shared.http import get_http_service
from app.errors import handle_errors_async, APIError
from .config import get_ticketfairy_config

logger = logging.getLogger(__name__)


class TicketFairyClient(BaseClient):
    """Client for submitting events to TicketFairy API."""

    def __init__(self):
        self.http = get_http_service()
        self.config = get_ticketfairy_config()

    @handle_errors_async(reraise=True)
    async def submit(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit event data to TicketFairy.

        Args:
            data: Event data to submit

        Returns:
            API response data

        Raises:
            APIError: On API errors
            ValueError: If API key not configured
        """
        if not self.config.api_key:
            raise ValueError("TicketFairy API key not configured")

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
            raise APIError("TicketFairy", "Empty response from API")

        # Parse response
        try:
            response_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise APIError(
                "TicketFairy",
                f"Invalid JSON response: {e}. Response: {response_text}",
            )

        # Check for API errors
        if response.status >= 400:
            error_msg = "Unknown error"
            if isinstance(response_data, dict):
                if "message" in response_data:
                    if isinstance(response_data["message"], dict):
                        error_msg = response_data["message"].get(
                            "message", str(response_data["message"])
                        )
                    else:
                        error_msg = str(response_data["message"])
                elif "error" in response_data:
                    error_msg = str(response_data["error"])

            raise APIError(
                "TicketFairy", 
                f"API error ({response.status}): {error_msg}", 
                response.status
            )

        return response_data