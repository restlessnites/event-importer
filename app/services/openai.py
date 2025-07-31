"""Service for OpenAI API interactions."""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from app.config import Config
from app.errors import APIError, ConfigurationError, handle_errors_async
from app.prompts import EventPrompts
from app.schemas import EventData, EventTime

logger = logging.getLogger(__name__)

# Error message constants
OPENAI_CLIENT_NOT_INITIALIZED = "OpenAI client not initialized - check API key"
OPENAI_API_KEY_NOT_FOUND = "OpenAI API key not found in configuration"


class OpenAIService:
    # Tool definition for structured extraction
    EXTRACTION_TOOL = {
        "type": "function",
        "function": {
            "name": "extract_event_data",
            "description": "Extract structured event information",
            "parameters": {
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
                            "timezone": {"type": ["string", "null"]},
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
        },
    }

    # Tool for description generation
    DESCRIPTION_TOOL = {
        "type": "function",
        "function": {
            "name": "generate_descriptions",
            "description": "Generate event descriptions",
            "parameters": {
                "type": "object",
                "properties": {
                    "long_description": {"type": ["string", "null"]},
                    "short_description": {"type": ["string", "null"]},
                },
                "required": [],
            },
        },
    }

    # Tool for genre enhancement
    GENRE_TOOL = {
        "type": "function",
        "function": {
            "name": "enhance_genres",
            "description": "Enhance and categorize event genres",
            "parameters": {
                "type": "object",
                "properties": {
                    "genres": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of enhanced genre categories",
                    },
                },
                "required": ["genres"],
            },
        },
    }

    def __init__(self: OpenAIService, config: Config) -> None:
        """Initialize OpenAI service."""
        if not config.api.openai_api_key:
            raise ConfigurationError(OPENAI_API_KEY_NOT_FOUND)
        self.client = AsyncOpenAI(api_key=config.api.openai_api_key)
        self.model = "gpt-4-turbo-preview"
        self.max_tokens = 4096

    def _add_json_requirement(self: OpenAIService, prompt: str) -> str:
        """Add JSON requirement to any prompt used with OpenAI."""
        return f"Return the information as a valid JSON object.\\n{prompt}"

    def _clean_response_data(
        self: OpenAIService,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Clean and validate response data before creating EventData."""
        cleaned = self._filter_null_and_empty_values(data)
        self._process_images_field(cleaned)
        self._process_time_field(cleaned)
        return cleaned

    def _filter_null_and_empty_values(
        self: OpenAIService,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Filter out None values and empty strings."""
        return {
            key: value
            for key, value in data.items()
            if value is not None and not (isinstance(value, str) and not value.strip())
        }

    def _process_images_field(self: OpenAIService, data: dict[str, Any]) -> None:
        """Clean and validate the 'images' field in the data dictionary."""
        images_value = data.get("images")
        if not isinstance(images_value, dict):
            data.pop("images", None)
            return

        cleaned_images = {
            key: val.strip()
            for key, val in images_value.items()
            if val and isinstance(val, str) and val.strip()
        }

        if cleaned_images:
            data["images"] = cleaned_images
        else:
            data.pop("images", None)

    def _process_time_field(self: OpenAIService, data: dict[str, Any]) -> None:
        """Parse and validate the 'time' field in the data dictionary."""
        time_value = data.get("time")
        if not time_value:
            return

        parsed_time = None
        if isinstance(time_value, str):
            parsed_time = self._parse_time_from_string(time_value)
        elif isinstance(time_value, dict):
            parsed_time = self._parse_time_from_dict(time_value)

        if parsed_time:
            data["time"] = parsed_time
        else:
            data.pop("time", None)

    def _parse_time_from_string(
        self: OpenAIService,
        time_str: str,
    ) -> EventTime | None:
        """Parse an EventTime object from a string."""
        parts = re.split(r"\s*-\s*|\s+to\s+", time_str, maxsplit=1)
        start_time = parts[0].strip() if parts else None
        end_time = parts[1].strip() if len(parts) > 1 else None

        if start_time and start_time.lower() not in ["", "null", "none", "n/a"]:
            try:
                return EventTime(start=start_time, end=end_time)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse time '{time_str}': {e}")
        return None

    def _parse_time_from_dict(
        self: OpenAIService,
        time_dict: dict[str, Any],
    ) -> EventTime | None:
        """Parse an EventTime object from a dictionary."""
        try:
            return EventTime(**time_dict)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to create EventTime from dict {time_dict}: {e}")
        return None

    @handle_errors_async(reraise=True)
    async def extract_from_html(
        self: OpenAIService,
        html: str,
        url: str,
        max_length: int = 50000,
    ) -> EventData | None:
        """Extract event data from HTML content."""
        if not self.client:
            raise ConfigurationError(OPENAI_CLIENT_NOT_INITIALIZED)

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
        # Add JSON requirement for OpenAI
        prompt = self._add_json_requirement(prompt)

        result = await self._call_with_tool(prompt)
        if result:
            result["source_url"] = url
            # Clean the response data before validation
            cleaned_result = self._clean_response_data(result)
            return EventData(**cleaned_result)
        return None

    @handle_errors_async(reraise=True)
    async def extract_from_image(
        self: OpenAIService,
        image_data: bytes,
        mime_type: str,
        url: str,
    ) -> EventData | None:
        """Extract event data from an image."""
        if not self.client:
            raise ConfigurationError(OPENAI_CLIENT_NOT_INITIALIZED)

        image_b64 = base64.b64encode(image_data).decode("utf-8")

        # Build prompt using EventPrompts
        prompt = EventPrompts.build_extraction_prompt(
            content="",  # Empty for images
            url=url,
            content_type="image",
            needs_long_description=True,
            needs_short_description=True,
        )
        # Add JSON requirement for OpenAI
        prompt = self._add_json_requirement(prompt)

        result = await self._call_with_vision(prompt, image_b64, mime_type)
        if result:
            result["source_url"] = url
            # Set the image URL since we know it's an image
            result["images"] = {"full": url, "thumbnail": url}
            # Clean the response data before validation
            cleaned_result = self._clean_response_data(result)
            return EventData(**cleaned_result)
        return None

    @handle_errors_async(reraise=True)
    async def generate_descriptions(
        self: OpenAIService,
        event_data: EventData,
        force_rebuild: bool = False,
        supplementary_context: str | None = None,
    ) -> EventData:
        """Generate missing descriptions for an event."""
        if not self.client:
            raise ConfigurationError(OPENAI_CLIENT_NOT_INITIALIZED)

        # Check if we need to generate descriptions (missing or too short)
        needs_long = (
            not event_data.long_description or len(event_data.long_description) < 200
        )
        needs_short = (
            not event_data.short_description or len(event_data.short_description) > 100
        )

        if not force_rebuild and not needs_long and not needs_short:
            return event_data

        # Build prompt using centralized EventPrompts
        prompt = EventPrompts.build_description_generation_prompt(
            event_data,
            needs_long=needs_long,
            needs_short=needs_short,
            supplementary_context=supplementary_context,
        )
        # Add JSON requirement for OpenAI
        prompt = self._add_json_requirement(prompt)

        result = await self._call_with_tool(
            prompt,
            tool=self.DESCRIPTION_TOOL,
            tool_name="generate_descriptions",
        )

        if result:
            # Update only missing descriptions
            if force_rebuild or (needs_long and result.get("long_description")):
                event_data.long_description = result.get("long_description")
            if force_rebuild or (needs_short and result.get("short_description")):
                # Ensure it's under 100 chars
                event_data.short_description = result.get("short_description", "")[:100]

        return event_data

    @handle_errors_async(reraise=True)
    async def analyze_text(self: OpenAIService, prompt: str) -> str | None:
        """Analyze text with OpenAI and return raw response."""
        if not self.client:
            raise ConfigurationError(OPENAI_CLIENT_NOT_INITIALIZED)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    @handle_errors_async(reraise=True)
    async def extract_event_data(
        self: OpenAIService,
        prompt: str,
        image_b64: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Extract structured event data from a text prompt or image."""
        if not self.client:
            raise ConfigurationError(OPENAI_CLIENT_NOT_INITIALIZED)

        if image_b64 and mime_type:
            # Use vision for image extraction
            return await self._call_with_vision(prompt, image_b64, mime_type)
        # Use regular tool for text extraction
        return await self._call_with_tool(prompt)

    async def enhance_genres(self: OpenAIService, event_data: EventData) -> EventData:
        """Enhance event genres using OpenAI."""
        if not self.client:
            raise ConfigurationError(OPENAI_CLIENT_NOT_INITIALIZED)

        if not event_data.genres:
            return event_data

        # Build prompt using EventPrompts
        prompt = EventPrompts.build_genre_enhancement_prompt(
            event_data.model_dump(exclude_unset=True),
        )
        # Add JSON requirement for OpenAI
        prompt = self._add_json_requirement(prompt)

        try:
            result = await self._call_with_tool(
                prompt,
                tool=self.GENRE_TOOL,
                tool_name="enhance_genres",
            )
            if result and result.get("genres"):
                event_data.genres = result["genres"]
        except Exception:
            logger.exception("Failed to enhance genres")

        return event_data

    async def _call_with_tool(
        self: OpenAIService,
        prompt: str,
        tool: dict[str, Any] | None = None,
        tool_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Make API call with tool use."""
        if not tool:
            tool = self.EXTRACTION_TOOL
            tool_name = "extract_event_data"
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                tools=[tool],
                tool_choice={"type": "function", "function": {"name": tool_name}},
                max_tokens=self.max_tokens,
            )
            content = response.choices[0].message.tool_calls[0].function.arguments
            try:
                return json.loads(content)
            except Exception as e:
                logger.exception("Failed to parse JSON from OpenAI response")
                error_msg = f"Failed to parse JSON: {e}"
                service_name = "OpenAI"
                raise APIError(service_name, error_msg) from e
        except Exception as e:
            logger.exception("OpenAI tool call failed")
            service_name = "OpenAI"
            raise APIError(service_name, str(e)) from e

    async def _call_with_vision(
        self: OpenAIService,
        prompt: str,
        image_b64: str,
        mime_type: str,
    ) -> dict[str, Any] | None:
        """Call OpenAI vision API with a given prompt and image."""
        if not self.client:
            raise ConfigurationError(OPENAI_CLIENT_NOT_INITIALIZED)

        logger.debug(f"Calling OpenAI vision with model {self.model}")
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_b64}",
                                },
                            },
                        ],
                    },
                ],
                max_tokens=self.max_tokens,
            )

            # The response should be a JSON object, so we look for that.
            response_text = response.choices[0].message.content
            if not response_text:
                return None

            # Extract JSON from the response text
            match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
            json_str = match.group(1) if match else response_text

            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.exception("Failed to decode JSON from vision response")
            error_msg = f"JSON decode error: {e}"
            service_name = "OpenAI"
            raise APIError(service_name, error_msg) from e
        except Exception as e:
            logger.exception("OpenAI vision call failed")
            error_msg = f"Vision call failed: {e}"
            service_name = "OpenAI"
            raise APIError(service_name, error_msg) from e
