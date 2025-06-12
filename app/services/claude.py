"""Claude API service for event data extraction."""

import base64
import logging
from typing import Optional, Dict, Any
import json
import os
import re

from anthropic import AsyncAnthropic, APIError as AnthropicAPIError

from app.config import Config
from app.schemas import EventData
from app.errors import APIError, AuthenticationError
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

    # Tool for genre enhancement
    GENRE_TOOL = {
        "name": "enhance_genres",
        "description": "Enhance event genres",
        "input_schema": {
            "type": "object",
            "properties": {
                "genres": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["genres"],
        },
    }

    def __init__(self, config: Config):
        """Initialize Claude service."""
        self.config = config
        self.api_key = getattr(config.api, 'anthropic_api_key', None) or os.getenv("ANTHROPIC_API_KEY")
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20240620"
        self.max_tokens = 4096

    def _clean_response_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean response data to handle potential inconsistencies."""
        if not data:
            return data

        # If time is an empty object, convert to None
        if "time" in data and data["time"] == {}:
            data["time"] = None

        # If location is an empty object, convert to None
        if "location" in data and data["location"] == {}:
            data["location"] = None

        # Convert empty string for ticket_url to None
        if "ticket_url" in data and data["ticket_url"] == "":
            data["ticket_url"] = None

        # If coordinates is an empty object, convert to None
        if (
            "location" in data
            and isinstance(data.get("location"), dict)
            and "coordinates" in data["location"]
            and data["location"]["coordinates"] == {}
        ):
            data["location"]["coordinates"] = None

        return data

    async def extract_from_html(
        self, html: str, url: str, max_length: int = 50000
    ) -> Optional[EventData]:
        """Extract event data from HTML content."""
        # Truncate if too long
        if len(html) > max_length:
            html = html[:max_length] + "\n<!-- truncated -->"

        # Build prompt using EventPrompts
        prompt = EventPrompts.build_extraction_prompt(
            content=html,
            url=url,
            content_type="html",
            needs_long_description=True,
            needs_short_description=True
        )

        result = await self._call_with_tool(prompt)
        if result:
            result["source_url"] = url
            # Clean the response data before validation
            cleaned_result = self._clean_response_data(result)
            return EventData(**cleaned_result)
        return None

    async def extract_from_image(
        self, image_data: bytes, mime_type: str, url: str
    ) -> Optional[EventData]:
        """Extract event data from an image."""
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        # Build prompt using EventPrompts
        prompt = EventPrompts.build_extraction_prompt(
            content="",  # Empty for images
            url=url,
            content_type="image",
            needs_long_description=True,
            needs_short_description=True,
        )

        # For vision, we can't use tools. We must ask for JSON in the prompt.
        # It's also better to be very specific about the JSON format.
        schema_json = json.dumps(self.EXTRACTION_TOOL["input_schema"])
        vision_prompt = (
            f"{prompt}\n\n"
            "Please analyze the image and extract all event information. "
            "Respond ONLY with a single valid JSON object that conforms to the following schema. "
            "Do not include any other text, conversation, or markdown backticks. Your entire response must be the JSON object and nothing else.\n"
            f"JSON Schema:\n{schema_json}"
        )

        result = await self._call_with_vision(vision_prompt, image_b64, mime_type)

        if result:
            # Add source_url and image url, then validate with Pydantic
            result["source_url"] = url
            result["images"] = {"full": url, "thumbnail": url}
            # Clean the response data before validation
            cleaned_result = self._clean_response_data(result)
            return EventData(**cleaned_result)
        return None

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
            needs_short=needs_short
        )

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

    async def analyze_text(self, prompt: str) -> Optional[str]:
        """Analyze text with Claude and return raw response."""
        response = await self.client.messages.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.2,
        )
        return response.content[0].text.strip()

    async def _call_with_tool(
        self, prompt: str, tool: Optional[dict] = None, tool_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Make API call with tool use."""
        if not self.client:
            raise AuthenticationError("Claude")

        if not tool:
            tool = self.EXTRACTION_TOOL
            tool_name = "extract_event_data"
        try:
            message = await self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                tools=[tool],
                tool_choice={"type": "tool", "name": tool_name},
                max_tokens=self.max_tokens,
                temperature=0.1,
            )

            # Find the tool use content block
            tool_use = next(
                (content for content in message.content if content.type == "tool_use"),
                None,
            )

            if tool_use and hasattr(tool_use, 'input'):
                content = tool_use.input
                try:
                    if isinstance(content, dict):
                        return content
                    return json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Claude tool response was not a valid JSON object: {content}")
                    return {"raw_text": str(content)}
            else:
                logger.warning("No tool use block found in Claude response")
                return None

        except Exception as e:
            # Don't log as error, let the LLMService handle it as a fallback
            logger.debug(f"Claude tool call failed: {e}")
            raise APIError("Claude", str(e))

    async def _call_with_vision(
        self, prompt: str, image_b64: str, mime_type: str
    ) -> Optional[Dict[str, Any]]:
        """Call Claude's vision model with a prompt and image."""
        if not self.client:
            raise AuthenticationError("Claude")

        try:
            response = await self.client.messages.create(
                model=self.model,
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
                max_tokens=self.max_tokens,
                temperature=0.1,
            )

            # In vision responses, the result is often in a text block
            text_content = next(
                (content.text for content in response.content if content.type == "text"),
                None,
            )

            if text_content:
                try:
                    # Find the JSON object in the response text, robustly.
                    # It might be wrapped in ```json ... ```
                    match = re.search(r"```json\s*(\{.*?\})\s*```", text_content, re.DOTALL)
                    if match:
                        json_str = match.group(1)
                    else:
                        # Fallback to finding first { and last }
                        json_start = text_content.find("{")
                        json_end = text_content.rfind("}") + 1
                        if json_start != -1 and json_end > json_start:
                            json_str = text_content[json_start:json_end]
                        else:
                            # If no JSON object is found, try to parse the whole content.
                            # This handles the case where the model returns *only* the JSON.
                            json_str = text_content

                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Failed to parse JSON from Claude vision response: {e}; content: {text_content}"
                    )
                    # Re-raise as an APIError to be handled by the LLM service
                    raise APIError("Claude", f"Vision call failed: Claude API error: Failed to parse JSON: {e}")
            else:
                logger.warning("No text content found in Claude vision response")
                return None
            
        except AnthropicAPIError as e:
            logger.error(f"Claude vision API call failed: {e}")
            raise APIError("Claude", f"Vision call failed: {e.status_code} - {e.message}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during Claude vision call: {e}")
            raise APIError("Claude", f"Vision call failed with unexpected error: {e}")

    async def enhance_genres(self, event_data: EventData) -> EventData:
        """Enhance event genres using Claude."""
        if not event_data.genres:
            return event_data

        # Build prompt using EventPrompts
        prompt = EventPrompts.build_genre_enhancement_prompt(
            event_data.model_dump(exclude_unset=True)
        )

        try:
            result = await self._call_with_tool(
                prompt, tool=self.GENRE_TOOL, tool_name="enhance_genres"
            )
            if result and result.get("genres"):
                event_data.genres = result["genres"]
            return event_data
        except Exception as e:
            logger.error(f"Failed to enhance genres: {e}")
            return event_data
