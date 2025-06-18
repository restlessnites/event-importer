"""TicketFairy API client."""

import json
import logging
from typing import Dict, Any, Optional

import httpx

from app.errors import handle_errors_async, APIError, TimeoutError
from app.config import Config


logger = logging.getLogger(__name__)


class TicketFairyClient:
    """Client for TicketFairy API."""

    # API configuration
    TICKETFAIRY_API_URL = "https://www.ticketfairy.com/api/events"
    REQUEST_TIMEOUT = 30.0
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0

    def __init__(self, config: Config):
        """Initialize client with configuration."""
        self.config = config
        self.api_key = config.api.ticketfairy_api_key
        if not self.api_key:
            raise ValueError("TicketFairy API key not configured")

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
            TimeoutError: On timeout
        """
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Make request
        async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
            response = await client.post(
                self.TICKETFAIRY_API_URL,
                headers=headers,
                json=data
            )

            # Handle empty response
            response_text = response.text
            if not response_text or response_text.strip() == "":
                raise APIError("TicketFairy", "Empty response from API")

            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                raise APIError(
                    "TicketFairy",
                    f"Invalid JSON response: {e}. Response: {response_text}"
                )

            # Check for API errors
            if not response.is_success:
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
                    f"API error ({response.status_code}): {error_msg}"
                )

            return response_data 