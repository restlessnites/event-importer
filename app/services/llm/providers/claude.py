"""Claude API service for event data extraction."""

import base64
import json
import logging
from typing import Any

from anthropic import APIStatusError, AsyncAnthropic
from anthropic.types import TextBlock

from app.core.errors import APIError, AuthenticationError, handle_errors_async
from app.core.schemas import EventData
from app.services.llm.base import BaseLLMService
from app.services.llm.prompts import EventPrompts
from config import Config

logger = logging.getLogger(__name__)

# Service name constant
CLAUDE_SERVICE_NAME = "Claude"


class Claude(BaseLLMService):
    """Provider for Claude AI API interactions."""

    def __init__(self: "Claude", config: Config) -> None:
        super().__init__(config)
        self.client = None
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens = 4096

        api_key = config.api.anthropic_api_key
        if api_key:
            self.client = AsyncAnthropic(api_key=api_key)

        # Tool definitions...
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
                            "address": {"type": "string"},
                            "city": {"type": "string"},
                            "state": {"type": "string"},
                            "country": {"type": "string"},
                            "coordinates": {"type": "object"},
                        },
                    },
                    "time": {"type": "object"},
                    "lineup": {"type": "array", "items": {"type": "string"}},
                    "genres": {"type": "array", "items": {"type": "string"}},
                    "long_description": {"type": "string"},
                    "short_description": {"type": "string"},
                },
                "required": ["title"],
            },
        }
        self.GENRE_TOOL = {
            "name": "enhance_genres",
            "description": "Enhance event genres",
            "input_schema": {
                "type": "object",
                "properties": {
                    "genres": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["genres"],
            },
        }

    @handle_errors_async(reraise=True)
    async def extract_from_html(
        self: "Claude",
        html: str,
        url: str,
        needs_long_description: bool = True,
        needs_short_description: bool = True,
    ) -> EventData | None:
        """Extract event data from HTML."""
        max_length = 50000
        if len(html) > max_length:
            html = html[:max_length] + "\n<!-- truncated -->"

        prompt = EventPrompts.build_extraction_prompt(
            content=html,
            url=url,
            content_type="html",
            needs_long_description=needs_long_description,
            needs_short_description=needs_short_description,
        )

        result = await self._call_with_tool(prompt)
        if result:
            result["source_url"] = url
            cleaned_result = self._clean_response_data(result)
            return EventData(**cleaned_result)
        return None

    @handle_errors_async(reraise=True)
    async def extract_from_image(
        self: "Claude",
        image_data: bytes,
        mime_type: str,
        url: str,
        needs_long_description: bool = True,
        needs_short_description: bool = True,
    ) -> EventData | None:
        """Extract event data from an image."""
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        prompt = EventPrompts.build_extraction_prompt(
            content="",
            url=url,
            content_type="image",
            needs_long_description=needs_long_description,
            needs_short_description=needs_short_description,
        )
        schema_json = json.dumps(self.EXTRACTION_TOOL["input_schema"])
        vision_prompt = f"{prompt}\n\nRespond ONLY with a valid JSON object conforming to this schema:\n{schema_json}"

        result = await self._call_with_vision(vision_prompt, image_b64, mime_type)
        if result:
            result["source_url"] = url
            result["images"] = {"full": url, "thumbnail": url}
            cleaned_result = self._clean_response_data(result)
            return EventData(**cleaned_result)
        return None

    @handle_errors_async(reraise=True)
    async def generate_descriptions(
        self: "Claude",
        event_data: EventData,
        needs_long: bool,
        needs_short: bool,
        supplementary_context: str | None = None,
    ) -> EventData:
        """Generate missing descriptions for an event."""
        if not needs_long and not needs_short:
            return event_data

        prompt = EventPrompts.build_description_generation_prompt(
            event_data,
            needs_long=needs_long,
            needs_short=needs_short,
            supplementary_context=supplementary_context,
        )

        try:
            result = await self._call_with_tool(prompt)
            updated_event = event_data.model_copy(deep=True)
            if result:
                if needs_long and result.get("long_description"):
                    updated_event.long_description = result.get("long_description")
                if needs_short and result.get("short_description"):
                    updated_event.short_description = result.get("short_description")
            return updated_event
        except Exception:
            logger.exception("Failed to generate descriptions")
            return event_data

    @handle_errors_async(reraise=True)
    async def analyze_text(self: "Claude", prompt: str) -> str | None:
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
        self: "Claude",
        prompt: str,
        image_b64: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Extract structured event data from a text prompt or image."""
        if image_b64 and mime_type:
            return await self._call_with_vision(prompt, image_b64, mime_type)
        return await self._call_with_tool(prompt)

    @handle_errors_async(reraise=True)
    async def enhance_genres(self: "Claude", event_data: EventData) -> EventData:
        """Enhance event genres using Claude."""
        if not event_data.genres:
            return event_data

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
        except Exception:
            logger.exception("Failed to enhance genres")
            return event_data

    async def _call_with_tool(
        self: "Claude",
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
            tool_use = next((c for c in message.content if c.type == "tool_use"), None)
            if tool_use and hasattr(tool_use, "input"):
                content = tool_use.input
                try:
                    return json.loads(content) if isinstance(content, str) else content
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Claude tool response not valid JSON: {content}")
                    return {"raw_text": str(content)}
            logger.warning("No tool use block in Claude response")
            return None
        except APIStatusError as e:
            logger.exception("Claude API call failed")
            raise APIError(
                CLAUDE_SERVICE_NAME, f"API call failed: {e.status_code}"
            ) from e
        except Exception as e:
            logger.debug(f"Claude tool call failed: {e}")
            raise APIError(CLAUDE_SERVICE_NAME, str(e)) from e

    async def _call_with_vision(
        self: "Claude",
        prompt: str,
        image_b64: str,
        mime_type: str,
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
                try:
                    if content.startswith("```json"):
                        content = content[7:-3].strip()
                    elif content.startswith("```"):
                        content = content[3:-3].strip()
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    raise APIError(
                        CLAUDE_SERVICE_NAME, f"Failed to parse JSON: {e}"
                    ) from e
            logger.warning("No text content in Claude vision response")
            return None
        except APIStatusError as e:
            logger.exception("Claude vision API call failed")
            raise APIError(
                CLAUDE_SERVICE_NAME, f"Vision call failed: {e.status_code}"
            ) from e
        except Exception as e:
            logger.exception("Unexpected error during Claude vision call")
            raise APIError(CLAUDE_SERVICE_NAME, f"Unexpected error: {e}") from e
