"""Claude API service for event data extraction."""

import json
import logging
import base64
from typing import Optional, Dict, Any
from anthropic import AsyncAnthropic, APIStatusError
from anthropic.types import TextBlock

from app.config import Config
from app.schemas import EventData
from app.errors import APIError, AuthenticationError, handle_errors_async
from app.prompts import EventPrompts

logger = logging.getLogger(__name__)


class ClaudeService:
    """Service for Claude AI API interactions."""

    def __init__(self, config: Config):
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
                    "address": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
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
                            "thumbnail": {"type": "string"}
                        }
                    }
                },
                "required": ["title"]
            }
        }

        self.GENRE_TOOL = {
            "name": "enhance_genres",
            "description": "Enhance event genres based on artist and venue information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "genres": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["genres"]
            }
        }

    @handle_errors_async(reraise=True)
    async def extract_from_html(self, html: str, url: str) -> Optional[EventData]:
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
            needs_short_description=True
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

    @handle_errors_async(reraise=True)
    async def generate_descriptions(self, event_data: EventData) -> EventData:
        """Generate missing descriptions for an event."""
        # Build prompt using EventPrompts
        prompt = EventPrompts.build_description_prompt(
            event_data.model_dump(exclude_unset=True)
        )

        try:
            result = await self._call_with_tool(prompt)
            if result:
                if result.get("long_description"):
                    event_data.long_description = result["long_description"]
                if result.get("short_description"):
                    event_data.short_description = result["short_description"]
            return event_data
        except Exception as e:
            logger.error(f"Failed to generate descriptions: {e}")
            return event_data

    @handle_errors_async(reraise=True)
    async def analyze_text(self, prompt: str) -> Optional[str]:
        """Analyze text using Claude."""
        if not self.client:
            raise AuthenticationError("Claude")

        response = await self.client.messages.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.2,
        )
        return response.content[0].text.strip()

    @handle_errors_async(reraise=True)
    async def extract_event_data(
        self,
        prompt: str,
        image_b64: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Extract structured event data from a text prompt or image."""
        if image_b64 and mime_type:
            # Use vision for image extraction
            return await self._call_with_vision(prompt, image_b64, mime_type)
        else:
            # Use regular tool for text extraction
            return await self._call_with_tool(prompt)

    @handle_errors_async(reraise=True)
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
            message = await self.client.messages.create(
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

            # Extract text from response
            text_content = ""
            for content in message.content:
                if isinstance(content, TextBlock):
                    text_content += content.text

            if text_content:
                try:
                    # Try to extract JSON from the response
                    text_content = text_content.strip()
                    
                    # Look for JSON object boundaries
                    start_idx = text_content.find('{')
                    end_idx = text_content.rfind('}')
                    
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        json_str = text_content[start_idx:end_idx + 1]
                    else:
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
            
        except APIStatusError as e:
            logger.error(f"Claude vision API call failed: {e}")
            raise APIError("Claude", f"Vision call failed: {e.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during Claude vision call: {e}")
            raise APIError("Claude", f"Vision call failed with unexpected error: {e}")

    def _clean_response_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate response data before creating EventData."""
        cleaned = {}
        
        for key, value in data.items():
            if value is not None:
                # Convert empty strings to None for optional fields
                if isinstance(value, str) and value.strip() == "":
                    continue
                # Convert empty lists to None for optional fields
                elif isinstance(value, list) and len(value) == 0:
                    continue
                else:
                    cleaned[key] = value
                    
        return cleaned
    
    def _clean_response_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate response data before creating EventData."""
        cleaned = {}
        
        for key, value in data.items():
            if value is not None:
                # Convert empty strings to None for optional fields
                if isinstance(value, str) and value.strip() == "":
                    continue
                # Convert empty lists to None for optional fields
                elif isinstance(value, list) and len(value) == 0:
                    continue
                else:
                    cleaned[key] = value
                    
        return cleaned