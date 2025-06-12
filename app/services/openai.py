import os
from openai import AsyncOpenAI
from typing import Any, Dict, Optional
from app.schemas import EventData
from app.config import Config
from app.errors import APIError, handle_errors_async
from app.prompts import EventPrompts
import logging
import base64
import json

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service for OpenAI API interactions."""

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
        """Initialize OpenAI service."""
        self.config = config
        self.api_key = getattr(config.api, 'openai_api_key', None) or os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = "gpt-4-turbo-preview"
        self.max_tokens = 4096

    def _add_json_requirement(self, prompt: str) -> str:
        """Add JSON requirement to any prompt used with OpenAI."""
        return f"Return the information as a valid JSON object.\n\n{prompt}"

    def _clean_response_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean OpenAI response data to ensure Pydantic validation compatibility."""
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
        
        # Convert empty string for ticket_url to None to avoid validation errors
        if "ticket_url" in data and data["ticket_url"] == "":
            data["ticket_url"] = None
            
        return data

    @handle_errors_async(reraise=True)
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
        # Add JSON requirement for OpenAI
        prompt = self._add_json_requirement(prompt)

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

    @handle_errors_async(reraise=True)
    async def analyze_text(self, prompt: str) -> Optional[str]:
        """Analyze text with OpenAI and return raw response."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    async def _call_with_tool(
        self, prompt: str, tool: Optional[dict] = None, tool_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Make API call with tool use."""
        if not tool:
            tool = self.EXTRACTION_TOOL
            tool_name = "extract_event_data"
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=self.max_tokens,
                temperature=0.1,
            )
            content = response.choices[0].message.content
            try:
                # Try to parse the first valid JSON object from the response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    return json.loads(content[json_start:json_end])
                else:
                    raise ValueError("No JSON object found in response")
            except Exception as e:
                logger.error(f"Failed to parse JSON from OpenAI response: {e}; content: {content}")
                raise APIError("OpenAI", f"Failed to parse JSON: {e}")
        except Exception as e:
            logger.error(f"OpenAI tool call failed: {e}")
            raise APIError("OpenAI", str(e))

    async def _call_with_vision(
        self, prompt: str, image_b64: str, mime_type: str
    ) -> Optional[Dict[str, Any]]:
        """Call OpenAI's vision model with a prompt and image."""
        if not self.client:
            raise ConfigurationError("OpenAI client not initialized")

        # Call OpenAI vision model
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
                                "url": f"data:{mime_type};base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=self.max_tokens,
            temperature=0.1,
        )
        content = response.choices[0].message.content
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                return json.loads(content[json_start:json_end])
            else:
                raise ValueError("No JSON object found in response")
        except Exception as e:
            logger.error(f"Failed to parse JSON from OpenAI vision response: {e}; content: {content}")
            raise APIError("OpenAI", f"Failed to parse JSON: {e}")

    async def enhance_genres(self, event_data: EventData) -> EventData:
        """Enhance event genres using OpenAI."""
        if not event_data.genres:
            return event_data

        # Build prompt using EventPrompts
        prompt = EventPrompts.build_genre_enhancement_prompt(
            event_data.model_dump(exclude_unset=True)
        )
        # Add JSON requirement for OpenAI
        prompt = self._add_json_requirement(prompt)

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