"""Claude API service for event data extraction."""

import base64
import logging
from typing import Optional, Dict, Any

from anthropic import AsyncAnthropic
from anthropic.types import ToolUseBlock

from app.config import Config
from app.schemas import EventData
from app.errors import APIError


logger = logging.getLogger(__name__)


class ClaudeService:
    """Service for Claude API interactions."""

    # Tool definition for structured extraction
    EXTRACTION_TOOL = {
        "name": "extract_event_data",
        "description": "Extract structured event information",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "venue": {"type": ["string", "null"]},
                "date": {"type": ["string", "null"]},
                "time": {
                    "type": ["object", "null"],
                    "properties": {
                        "start": {"type": ["string", "null"]},
                        "end": {"type": ["string", "null"]},
                    },
                },
                "promoters": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                "lineup": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                "genres": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                "long_description": {"type": ["string", "null"]},
                "short_description": {"type": ["string", "null"]},
                "location": {
                    "type": ["object", "null"],
                    "properties": {
                        "address": {"type": ["string", "null"]},
                        "city": {"type": ["string", "null"]},
                        "state": {"type": ["string", "null"]},
                        "country": {"type": ["string", "null"]},
                        "coordinates": {
                            "type": ["object", "null"],
                            "properties": {
                                "lat": {"type": ["number", "null"]},
                                "lng": {"type": ["number", "null"]},
                            },
                        },
                    },
                },
                "images": {
                    "type": ["object", "null"],
                    "properties": {
                        "full": {"type": ["string", "null"]},
                        "thumbnail": {"type": ["string", "null"]},
                    },
                },
                "minimum_age": {"type": ["string", "null"]},
                "cost": {"type": ["string", "null"]},
                "ticket_url": {"type": ["string", "null"]},
            },
            "required": ["title"],
        },
    }

    def __init__(self, config: Config):
        """Initialize Claude service."""
        self.config = config
        self.client = AsyncAnthropic(api_key=config.api.anthropic_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.max_tokens = 4096

    async def extract_from_html(
        self, html: str, url: str, max_length: int = 50000
    ) -> Optional[EventData]:
        """Extract event data from HTML content."""
        # Truncate if too long
        if len(html) > max_length:
            html = html[:max_length] + "\n<!-- truncated -->"

        prompt = f"""Extract event information from this webpage.

Source URL: {url}

HTML Content:
```html
{html}
```

Extract all available event information. Create concise descriptions."""

        try:
            result = await self._call_with_tool(prompt)
            if result:
                result["source_url"] = url
                return EventData(**result)
        except Exception as e:
            logger.error(f"Failed to extract from HTML: {e}")
            raise APIError("Claude", str(e))

    async def extract_from_image(
        self, image_data: bytes, mime_type: str, url: str
    ) -> Optional[EventData]:
        """Extract event data from an image."""
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        prompt = f"""Extract event information from this event flyer/poster.

Source URL: {url}

Extract all visible event details."""

        try:
            result = await self._call_with_vision(prompt, image_b64, mime_type)
            if result:
                result["source_url"] = url
                # Set the image URL since we know it's an image
                result["images"] = {"full": url, "thumbnail": url}
                return EventData(**result)
        except Exception as e:
            logger.error(f"Failed to extract from image: {e}")
            raise APIError("Claude", str(e))

    async def _call_with_tool(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Make API call with tool use."""
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0.1,
            tools=[self.EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "extract_event_data"},
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract tool response
        for content in message.content:
            if (
                isinstance(content, ToolUseBlock)
                and content.name == "extract_event_data"
            ):
                return content.input

        return None

    async def _call_with_vision(
        self, prompt: str, image_b64: str, mime_type: str
    ) -> Optional[Dict[str, Any]]:
        """Make API call with vision."""
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0.1,
            tools=[self.EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "extract_event_data"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": image_b64,
                            },
                        },
                    ],
                }
            ],
        )

        # Extract tool response
        for content in message.content:
            if (
                isinstance(content, ToolUseBlock)
                and content.name == "extract_event_data"
            ):
                return content.input

        return None
