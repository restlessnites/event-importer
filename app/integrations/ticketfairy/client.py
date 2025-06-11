import httpx
import json
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from ..base import BaseClient
from .config import (
    TICKETFAIRY_API_KEY,
    TICKETFAIRY_API_URL,
    TICKETFAIRY_ORIGIN,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY
)


class TicketFairyClient(BaseClient):
    """HTTP client for TicketFairy API"""
    
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_DELAY, min=1, max=10)
    )
    async def submit(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit event data to TicketFairy API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TICKETFAIRY_API_KEY}",
            "Origin": TICKETFAIRY_ORIGIN,
        }
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            try:
                response = await client.post(
                    TICKETFAIRY_API_URL,
                    headers=headers,
                    json=data
                )
                
                # Handle empty response
                response_text = response.text
                if not response_text or response_text.strip() == "":
                    raise Exception("Empty response from TicketFairy API")
                
                # Parse response
                try:
                    response_data = response.json()
                except json.JSONDecodeError as e:
                    raise Exception(f"Invalid JSON response: {e}. Response: {response_text}")
                
                # Check for API errors
                if not response.is_success:
                    error_msg = "Unknown error"
                    if isinstance(response_data, dict):
                        if "message" in response_data:
                            if isinstance(response_data["message"], dict):
                                error_msg = response_data["message"].get("message", str(response_data["message"]))
                            else:
                                error_msg = str(response_data["message"])
                        elif "error" in response_data:
                            error_msg = str(response_data["error"])
                    
                    raise Exception(f"TicketFairy API error ({response.status_code}): {error_msg}")
                
                return response_data
                
            except httpx.TimeoutException:
                raise Exception("Request to TicketFairy API timed out")
            except httpx.RequestError as e:
                raise Exception(f"Request error: {str(e)}")
            except Exception as e:
                # Re-raise our custom exceptions
                if "TicketFairy API error" in str(e) or "Empty response" in str(e):
                    raise
                # Wrap other exceptions
                raise Exception(f"Unexpected error submitting to TicketFairy: {str(e)}") 