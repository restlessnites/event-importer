"""Service for OpenAI API interactions."""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from app.core.errors import APIError, ConfigurationError, handle_errors_async
from app.core.schemas import EventData
from app.services.llm.base import BaseLLMService
from app.services.llm.prompts import EventPrompts
from config import Config

logger = logging.getLogger(__name__)

# Error message constants
OPENAI_CLIENT_NOT_INITIALIZED = "OpenAI client not initialized - check API key"
OPENAI_API_KEY_NOT_FOUND = "OpenAI API key not found in configuration"


class OpenAI(BaseLLMService):
    # Tool definitions...
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

    def __init__(self: OpenAI, config: Config) -> None:
        """Initialize OpenAI service."""
        super().__init__(config)
        if not config.api.openai_api_key:
            raise ConfigurationError(OPENAI_API_KEY_NOT_FOUND)
        self.client = AsyncOpenAI(api_key=config.api.openai_api_key)
        self.model = "gpt-4-turbo-preview"
        self.max_tokens = 4096

    def _add_json_requirement(self: OpenAI, prompt: str) -> str:
        """Add JSON requirement to any prompt used with OpenAI."""
        return f"Return the information as a valid JSON object.\n{prompt}"

    @handle_errors_async(reraise=True)
    async def extract_from_html(
        self: OpenAI,
        html: str,
        url: str,
        needs_long_description: bool = True,
        needs_short_description: bool = True,
        max_length: int = 50000,
    ) -> EventData | None:
        """Extract event data from HTML content."""
        if not self.client:
            raise ConfigurationError(OPENAI_CLIENT_NOT_INITIALIZED)

        if len(html) > max_length:
            html = html[:max_length] + "\n<!-- truncated -->"

        prompt = EventPrompts.build_extraction_prompt(
            content=html,
            url=url,
            content_type="html",
            needs_long_description=needs_long_description,
            needs_short_description=needs_short_description,
        )
        prompt = self._add_json_requirement(prompt)

        result = await self._call_with_tool(prompt)
        if result:
            result["source_url"] = url
            cleaned_result = self._clean_response_data(result)
            return EventData(**cleaned_result)
        return None

    @handle_errors_async(reraise=True)
    async def extract_from_image(
        self: OpenAI,
        image_data: bytes,
        mime_type: str,
        url: str,
        needs_long_description: bool = True,
        needs_short_description: bool = True,
    ) -> EventData | None:
        """Extract event data from an image."""
        if not self.client:
            raise ConfigurationError(OPENAI_CLIENT_NOT_INITIALIZED)

        image_b64 = base64.b64encode(image_data).decode("utf-8")
        prompt = EventPrompts.build_extraction_prompt(
            content="",
            url=url,
            content_type="image",
            needs_long_description=needs_long_description,
            needs_short_description=needs_short_description,
        )
        prompt = self._add_json_requirement(prompt)

        result = await self._call_with_vision(prompt, image_b64, mime_type)
        if result:
            result["source_url"] = url
            result["images"] = {"full": url, "thumbnail": url}
            cleaned_result = self._clean_response_data(result)
            return EventData(**cleaned_result)
        return None

    @handle_errors_async(reraise=True)
    async def generate_descriptions(
        self: OpenAI,
        event_data: EventData,
        needs_long: bool,
        needs_short: bool,
        supplementary_context: str | None = None,
    ) -> EventData:
        """Generate missing descriptions for an event based on explicit needs."""
        if not self.client:
            raise ConfigurationError(OPENAI_CLIENT_NOT_INITIALIZED)

        if not needs_long and not needs_short:
            return event_data

        prompt = EventPrompts.build_description_generation_prompt(
            event_data,
            needs_long=needs_long,
            needs_short=needs_short,
            supplementary_context=supplementary_context,
        )
        prompt = self._add_json_requirement(prompt)

        result = await self._call_with_tool(
            prompt,
            tool=self.DESCRIPTION_TOOL,
            tool_name="generate_descriptions",
        )

        updated_event = event_data.model_copy(deep=True)
        if result:
            if needs_long and result.get("long_description"):
                updated_event.long_description = result.get("long_description")
            if needs_short and result.get("short_description"):
                short_desc = result.get("short_description", "")
                max_len = self.config.processing.short_description_max_length
                updated_event.short_description = short_desc[:max_len]
        return updated_event

    @handle_errors_async(reraise=True)
    async def analyze_text(self: OpenAI, prompt: str) -> str | None:
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
        self: OpenAI,
        prompt: str,
        image_b64: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Extract structured event data from a text prompt or image."""
        if not self.client:
            raise ConfigurationError(OPENAI_CLIENT_NOT_INITIALIZED)

        if image_b64 and mime_type:
            return await self._call_with_vision(prompt, image_b64, mime_type)
        return await self._call_with_tool(prompt)

    async def enhance_genres(self: OpenAI, event_data: EventData) -> EventData:
        """Enhance event genres using OpenAI."""
        if not self.client:
            raise ConfigurationError(OPENAI_CLIENT_NOT_INITIALIZED)
        if not event_data.genres:
            return event_data

        prompt = EventPrompts.build_genre_enhancement_prompt(
            event_data.model_dump(exclude_unset=True)
        )
        prompt = self._add_json_requirement(prompt)

        try:
            result = await self._call_with_tool(
                prompt, tool=self.GENRE_TOOL, tool_name="enhance_genres"
            )
            if result and result.get("genres"):
                event_data.genres = result["genres"]
        except Exception:
            logger.exception("Failed to enhance genres")
        return event_data

    async def _call_with_tool(
        self: OpenAI,
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
                raise APIError("OpenAI", error_msg) from e
        except Exception as e:
            logger.exception("OpenAI tool call failed")
            raise APIError("OpenAI", str(e)) from e

    async def _call_with_vision(
        self: OpenAI,
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
            response_text = response.choices[0].message.content
            if not response_text:
                return None

            match = re.search(r"```json\n(.*)\n```", response_text, re.DOTALL)
            json_str = match.group(1) if match else response_text
            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.exception("Failed to decode JSON from vision response")
            error_msg = f"JSON decode error: {e}"
            raise APIError("OpenAI", error_msg) from e
        except Exception as e:
            logger.exception("OpenAI vision call failed")
            error_msg = f"Vision call failed: {e}"
            raise APIError("OpenAI", error_msg) from e
