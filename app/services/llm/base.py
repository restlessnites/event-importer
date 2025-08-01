"""Abstract base class for LLM services."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from app.config import Config
from app.core.schemas import EventData, EventTime

logger = logging.getLogger(__name__)


class BaseLLMService(ABC):
    """Abstract base class for Large Language Model services."""

    def __init__(self: BaseLLMService, config: Config) -> None:
        """Initialize the LLM service."""
        self.config = config

    def _clean_response_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Clean and validate response data before creating EventData."""
        cleaned = self._filter_null_and_empty_values(data)
        self._process_images_field(cleaned)
        self._process_time_field(cleaned)
        return cleaned

    def _filter_null_and_empty_values(self, data: dict[str, Any]) -> dict[str, Any]:
        """Filter out None values, empty strings, and empty lists."""
        cleaned_data = {}
        for key, value in data.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if isinstance(value, list) and not value:
                continue
            cleaned_data[key] = value
        return cleaned_data

    def _process_images_field(self, data: dict[str, Any]) -> None:
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

    def _process_time_field(self, data: dict[str, Any]) -> None:
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

    def _parse_time_from_string(self, time_str: str) -> EventTime | None:
        """Parse an EventTime object from a string."""
        parts = re.split(r"\\s*-\\s*|\\s+to\\s+", time_str, maxsplit=1)
        start_time = parts[0].strip() if parts else None
        end_time = parts[1].strip() if len(parts) > 1 else None

        if start_time and start_time.lower() not in ["", "null", "none", "n/a"]:
            try:
                return EventTime(start=start_time, end=end_time)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse time '{time_str}': {e}")
        return None

    def _parse_time_from_dict(self, time_dict: dict[str, Any]) -> EventTime | None:
        """Parse an EventTime object from a dictionary."""
        try:
            return EventTime(**time_dict)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to create EventTime from dict {time_dict}: {e}")
        return None

    @abstractmethod
    @abstractmethod
    async def extract_from_html(
        self: BaseLLMService,
        html: str,
        url: str,
        needs_long_description: bool = True,
        needs_short_description: bool = True,
    ) -> EventData | None:
        """Extract event data from HTML content."""
        raise NotImplementedError

    @abstractmethod
    async def extract_from_image(
        self: BaseLLMService,
        image_data: bytes,
        mime_type: str,
        url: str,
        needs_long_description: bool = True,
        needs_short_description: bool = True,
    ) -> EventData | None:
        """Extract event data from an image."""
        raise NotImplementedError

    @abstractmethod
    async def generate_descriptions(
        self: BaseLLMService,
        event_data: EventData,
        needs_long: bool,
        needs_short: bool,
        supplementary_context: str | None = None,
    ) -> EventData:
        """Generate missing descriptions for an event."""
        raise NotImplementedError

    @abstractmethod
    async def analyze_text(self: BaseLLMService, prompt: str) -> str | None:
        """Analyze text with the LLM and return a raw response."""
        raise NotImplementedError

    @abstractmethod
    async def extract_event_data(
        self: BaseLLMService,
        prompt: str,
        image_b64: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any] | None:
        """A generic method to extract structured event data."""
        raise NotImplementedError

    @abstractmethod
    async def enhance_genres(self: BaseLLMService, event_data: EventData) -> EventData:
        """Enhance event genres using the LLM."""
        raise NotImplementedError
