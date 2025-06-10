"""Claude API service for event data extraction."""

import base64
import logging
from typing import Optional, Dict, Any

from anthropic import AsyncAnthropic
from anthropic.types import ToolUseBlock

from app.config import Config
from app.schemas import EventData
from app.errors import APIError
from app.prompts import EventPrompts


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

    # Tool for description generation
    DESCRIPTION_TOOL = {
        "name": "generate_descriptions",
        "description": "Generate event descriptions",
        "input_schema": {
            "type": "object",
            "properties": {
                "long_description": {"type": ["string", "null"]},
                "short_description": {"type": ["string", "null"]},
            },
            "required": [],
        },
    }

    def __init__(self, config: Config):
        """Initialize Claude service."""
        self.config = config
        self.client = AsyncAnthropic(api_key=config.api.anthropic_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.max_tokens = 4096

    def _clean_response_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean Claude response data to ensure Pydantic validation compatibility."""
        if not data:
            return data
        
        # Handle images field - remove None values from the dict
        if "images" in data and data["images"]:
            images = data["images"]
            if isinstance(images, dict):
                # Remove any None values from the images dict
                cleaned_images = {k: v for k, v in images.items() if v is not None}
                # If no valid images remain, set to None
                data["images"] = cleaned_images if cleaned_images else None
        
        return data

    async def extract_from_html(
        self, html: str, url: str, max_length: int = 50000
    ) -> Optional[EventData]:
        """Extract event data from HTML content."""
        # Truncate if too long
        if len(html) > max_length:
            html = html[:max_length] + "\n<!-- truncated -->"

        # Build prompt using centralized prompt builder
        prompt = EventPrompts.build_extraction_prompt(
            content=html,
            url=url,
            content_type="html",
            needs_long_description=True,
            needs_short_description=True,
        )

        try:
            result = await self._call_with_tool(prompt)
            if result:
                result["source_url"] = url
                # Clean the response data before validation
                cleaned_result = self._clean_response_data(result)
                return EventData(**cleaned_result)
        except Exception as e:
            logger.error(f"Failed to extract from HTML: {e}")
            raise APIError("Claude", str(e))

    async def extract_from_image(
        self, image_data: bytes, mime_type: str, url: str
    ) -> Optional[EventData]:
        """Extract event data from an image."""
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        # Build prompt using centralized prompt builder
        prompt = EventPrompts.build_extraction_prompt(
            content="",  # Empty for images
            url=url,
            content_type="image",
            needs_long_description=True,
            needs_short_description=True,
        )

        try:
            result = await self._call_with_vision(prompt, image_b64, mime_type)
            if result:
                result["source_url"] = url
                # Set the image URL since we know it's an image
                result["images"] = {"full": url, "thumbnail": url}
                # Clean the response data before validation
                cleaned_result = self._clean_response_data(result)
                return EventData(**cleaned_result)
        except Exception as e:
            logger.error(f"Failed to extract from image: {e}")
            raise APIError("Claude", str(e))

    async def generate_descriptions(self, event_data: EventData) -> EventData:
        """Generate missing descriptions for an event."""
        # Check if we need to generate descriptions
        needs_long = not bool(event_data.long_description)
        needs_short = not bool(event_data.short_description)

        if not needs_long and not needs_short:
            return event_data

        # Convert EventData to dict for the prompt builder
        event_dict = event_data.model_dump(exclude_unset=True)

        # Build prompt for description generation only
        prompt = EventPrompts.build_description_only_prompt(
            event_data=event_dict,
            needs_long=needs_long,
            needs_short=needs_short,
        )

        try:
            result = await self._call_with_tool(
                prompt, tool=self.DESCRIPTION_TOOL, tool_name="generate_descriptions"
            )

            if result:
                # Update only missing descriptions
                if needs_long and result.get("long_description"):
                    event_data.long_description = result["long_description"]
                if needs_short and result.get("short_description"):
                    # Ensure it's under 100 chars
                    event_data.short_description = result["short_description"][:100]

            return event_data

        except Exception as e:
            logger.error(f"Failed to generate descriptions: {e}")
            # Return original data if generation fails
            return event_data

    async def analyze_text(self, prompt: str) -> Optional[str]:
        """
        Analyze text with Claude and return raw response.

        Used for general analysis tasks like genre extraction.
        """
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )

            if message.content and len(message.content) > 0:
                return message.content[0].text

            return None

        except Exception as e:
            logger.error(f"Claude text analysis failed: {e}")
            raise

    async def _call_with_tool(
        self, prompt: str, tool: Optional[dict] = None, tool_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Make API call with tool use."""
        if not tool:
            tool = self.EXTRACTION_TOOL
            tool_name = "extract_event_data"

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0.1,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool_name},
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract tool response
        for content in message.content:
            if isinstance(content, ToolUseBlock) and content.name == tool_name:
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
