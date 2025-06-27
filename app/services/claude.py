"""Claude API service for event data extraction."""

import base64
import json
import logging
import re
from typing import Any

from anthropic import APIStatusError, AsyncAnthropic
from anthropic.types import TextBlock

from app.config import Config
from app.errors import APIError, AuthenticationError, handle_errors_async
from app.prompts import EventPrompts
from app.schemas import EventData, EventTime

logger = logging.getLogger(__name__)

# Service name constant
CLAUDE_SERVICE_NAME = "Claude"


class ClaudeService:
    """Service for Claude AI API interactions."""

    def __init__(self: "ClaudeService", config: Config) -> None:
        self.config = config
        self.client = None
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens = 4096

        # Get API key from config (match existing pattern)
        api_key = config.api.anthropic_key
        if api_key:
            self.client = AsyncAnthropic(api_key=api_key)

        # Tool definitions
        self.EXTRACTION_TOOL = {
            "name": "extract_event_data",
            "description": "Extract structured event data from content",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "venue": {"type": "string"},
                    "date": {"type": "string"},
                    "location": {
                        "type": "object",
                        "properties": {
                            "address": {"type": "string", "description": "Street address"},
                            "city": {"type": "string", "description": "City name"},
                            "state": {"type": "string", "description": "State/province"},
                            "country": {"type": "string", "description": "Country name"},
                            "coordinates": {"type": "object", "description": "Lat/lng coordinates (optional)"},
                        },
                    },
                    "time": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string", "description": "Start time in HH:MM format"},
                            "end": {"type": "string", "description": "End time in HH:MM format"},
                            "timezone": {"type": "string", "description": "Timezone (optional)"},
                        },
                    },
                    "doors_time": {"type": "string"},
                    "lineup": {"type": "array", "items": {"type": "string"}},
                    "genres": {"type": "array", "items": {"type": "string"}},
                    "price": {"type": "string"},
                    "age_restriction": {"type": "string"},
                    "long_description": {"type": "string"},
                    "short_description": {"type": "string"},
                    "website": {"type": "string"},
                    "tickets_url": {"type": "string"},
                    "images": {
                        "type": "object",
                        "properties": {
                            "full": {"type": "string"},
                            "thumbnail": {"type": "string"},
                        },
                    },
                },
                "required": ["title"],
            },
        }

        self.GENRE_TOOL = {
            "name": "enhance_genres",
            "description": "Enhance event genres based on artist and venue information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "genres": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["genres"],
            },
        }

    @handle_errors_async(reraise=True)
    async def extract_from_html(
        self: "ClaudeService", html: str, url: str,
    ) -> EventData | None:
        """Extract event data from HTML."""
        max_length = 50000

        # Truncate if too long
        if len(html) > max_length:
            html = html[:max_length] + "\n<!-- truncated -->"

        # Build prompt using EventPrompts
        prompt = EventPrompts.build_extraction_prompt(
            content=html,
            url=url,
            content_type="html",
            needs_long_description=True,
            needs_short_description=True,
        )

        result = await self._call_with_tool(prompt)
        if result:
            result["source_url"] = url
            # Clean the response data before validation
            cleaned_result = self._clean_response_data(result)
            return EventData(**cleaned_result)
        return None

    @handle_errors_async(reraise=True)
    async def extract_from_image(
        self: "ClaudeService", image_data: bytes, mime_type: str, url: str,
    ) -> EventData | None:
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
            # Add source_url and image url
            result["source_url"] = url
            result["images"] = {"full": url, "thumbnail": url}

            # Clean the response data before validation
            cleaned_result = self._clean_response_data(result)

            # Handle time parsing more robustly - let EventTime model handle it
            time_value = cleaned_result.get("time")
            if time_value:
                if isinstance(time_value, str):
                    # Clean up common invalid time formats
                    time_str = time_value.strip()

                    # Skip obviously invalid times
                    if time_str.lower() in ["", "null", "none", "n/a", "tbd", "tba"]:
                        cleaned_result.pop("time", None)
                    elif (
                        time_str.endswith(":") and len(time_str) <= 3
                    ):  # Handle cases like "7:"
                        logger.warning(f"Invalid time format '{time_str}', skipping")
                        cleaned_result.pop("time", None)
                    else:
                        # Split time range if present
                        parts = re.split(r"\s*-\s*|\s+to\s+", time_str, maxsplit=1)
                        start_time = parts[0].strip() if parts else None
                        end_time = parts[1].strip() if len(parts) > 1 else None

                        # Only create EventTime if we have valid time strings
                        if (start_time and len(start_time) > 1):
                            # Must be more than just a digit
                            try:
                                # Let EventTime parse the time format (it handles AM/PM)
                                cleaned_result["time"] = EventTime(
                                    start=start_time, end=end_time,
                                )
                                logger.info(
                                    f"Successfully parsed time: start='{start_time}', end='{end_time}'",
                                )
                            except (ValueError, TypeError) as e:
                                logger.warning(
                                    f"Failed to parse time '{time_value}': {e}",
                                )
                                # Remove invalid time rather than failing the whole import
                                cleaned_result.pop("time", None)
                        else:
                            # Remove empty/invalid time
                            logger.warning(f"Time too short or invalid: '{start_time}'")
                            cleaned_result.pop("time", None)
                elif isinstance(time_value, dict):
                    # Already a dict, let EventTime validate it
                    try:
                        cleaned_result["time"] = EventTime(**time_value)
                        logger.info(
                            f"Successfully created EventTime from dict: {time_value}",
                        )
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Failed to create EventTime from dict {time_value}: {e}",
                        )
                        cleaned_result.pop("time", None)
                else:
                    # Handle other types - convert to string and try again
                    logger.warning(
                        f"Unexpected time type {type(time_value)}: {time_value}",
                    )
                    cleaned_result.pop("time", None)

            # Now, create the EventData object with the processed data
            return EventData(**cleaned_result)

        return None

    @handle_errors_async(reraise=True)
    async def generate_descriptions(
        self: "ClaudeService", event_data: EventData,
    ) -> EventData:
        """Generate missing descriptions for an event."""
        # Determine which descriptions need to be generated/fixed
        needs_long = (
            not event_data.long_description or len(event_data.long_description) < 100
        )
        needs_short = (
            not event_data.short_description or len(event_data.short_description) > 100
        )

        # Build prompt using EventPrompts
        prompt = EventPrompts.build_description_only_prompt(
            event_data.model_dump(exclude_unset=True),
            needs_long=needs_long,
            needs_short=needs_short,
        )

        try:
            result = await self._call_with_tool(prompt)
            if result:
                if result.get("long_description"):
                    event_data.long_description = result["long_description"]
                if result.get("short_description"):
                    event_data.short_description = result["short_description"]
            return event_data
        except Exception:
            logger.exception("Failed to generate descriptions")
            return event_data

    @handle_errors_async(reraise=True)
    async def analyze_text(self: "ClaudeService", prompt: str) -> str | None:
        """Analyze text using Claude."""
        if not self.client:
            raise AuthenticationError(CLAUDE_SERVICE_NAME)

        response = await self.client.messages.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.2,
        )
        return response.content[0].text.strip()

    @handle_errors_async(reraise=True)
    async def extract_event_data(
        self: "ClaudeService",
        prompt: str,
        image_b64: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Extract structured event data from a text prompt or image."""
        if image_b64 and mime_type:
            # Use vision for image extraction
            return await self._call_with_vision(prompt, image_b64, mime_type)
        # Use regular tool for text extraction
        return await self._call_with_tool(prompt)

    @handle_errors_async(reraise=True)
    async def enhance_genres(self: "ClaudeService", event_data: EventData) -> EventData:
        """Enhance event genres using Claude."""
        if not event_data.genres:
            return event_data

        # Build prompt using EventPrompts
        prompt = EventPrompts.build_genre_enhancement_prompt(
            event_data.model_dump(exclude_unset=True),
        )

        try:
            result = await self._call_with_tool(
                prompt, tool=self.GENRE_TOOL, tool_name="enhance_genres",
            )
            if result and result.get("genres"):
                event_data.genres = result["genres"]
            return event_data
        except Exception:
            logger.exception("Failed to enhance genres")
            return event_data

    async def _call_with_tool(
        self: "ClaudeService",
        prompt: str,
        tool: dict | None = None,
        tool_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Make API call with tool use."""
        if not self.client:
            raise AuthenticationError(CLAUDE_SERVICE_NAME)

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

            if tool_use and hasattr(tool_use, "input"):
                content = tool_use.input
                try:
                    if isinstance(content, dict):
                        return content
                    return json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        f"Claude tool response was not a valid JSON object: {content}",
                    )
                    return {"raw_text": str(content)}
            else:
                logger.warning("No tool use block found in Claude response")
                return None

        except APIStatusError as e:
            logger.exception("Claude API call failed")
            error_msg = f"API call failed: {e.status_code} - {e.response.text}"
            raise APIError(CLAUDE_SERVICE_NAME, error_msg) from e
        except Exception as e:
            # Don't log as error, let the LLMService handle it as a fallback
            logger.debug(f"Claude tool call failed: {e}")
            raise APIError(CLAUDE_SERVICE_NAME, str(e)) from e

    async def _call_with_vision(
        self: "ClaudeService", prompt: str, image_b64: str, mime_type: str,
    ) -> dict[str, Any] | None:
        """Call Claude's vision model with a prompt and image."""
        if not self.client:
            raise AuthenticationError(CLAUDE_SERVICE_NAME)

        try:
            message = await self.client.messages.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": image_b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    },
                ],
                max_tokens=self.max_tokens,
                temperature=0.1,
            )

            if message.content and isinstance(message.content[0], TextBlock):
                content = message.content[0].text.strip()

                # The response should be a JSON object, so let's try to parse it
                try:
                    # Remove markdown backticks if present
                    if content.startswith("```json"):
                        content = content[7:-3].strip()
                    elif content.startswith("```"):
                        content = content[3:-3].strip()

                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.exception("Failed to parse JSON from Claude vision response")
                    # Re-raise as an APIError to be handled by the LLM service
                    error_msg = f"Vision call failed: Claude API error: Failed to parse JSON: {e}"
                    raise APIError(CLAUDE_SERVICE_NAME, error_msg) from e
            else:
                logger.warning("No text content found in Claude vision response")
                return None

        except APIStatusError as e:
            logger.exception("Claude vision API call failed")
            error_msg = f"Vision call failed: {e.status_code} - {e.response.text}"
            raise APIError(CLAUDE_SERVICE_NAME, error_msg) from e
        except Exception as e:
            logger.exception("An unexpected error occurred during Claude vision call")
            error_msg = f"Vision call failed with unexpected error: {e}"
            raise APIError(CLAUDE_SERVICE_NAME, error_msg) from e

    def _clean_response_data(
        self: "ClaudeService", data: dict[str, Any],
    ) -> dict[str, Any]:
        """Clean and validate response data before creating EventData."""
        cleaned = {}

        for key, value in data.items():
            if value is not None:
                # Convert empty strings to None for optional fields
                if (isinstance(value, str) and value.strip() == "") or (isinstance(value, list) and len(value) == 0):
                    continue
                cleaned[key] = value

        return cleaned
