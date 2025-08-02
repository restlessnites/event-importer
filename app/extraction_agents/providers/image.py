"""Agent for importing events from direct image URLs."""

from __future__ import annotations

import logging
from typing import Any

from app.core.error_messages import AgentMessages, ServiceMessages
from app.core.schemas import EventData, ImportMethod, ImportStatus
from app.extraction_agents.base import BaseExtractionAgent
from app.services.image import ImageService
from app.services.llm.service import LLMService

logger = logging.getLogger(__name__)


class Image(BaseExtractionAgent):
    """Agent for importing events from image URLs (flyers/posters)."""

    image_service: ImageService

    def __init__(self, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> None:
        super().__init__(*args, **kwargs)
        self.image_service = self.get_service("image")

    @property
    def name(self: Image) -> str:
        return "Image"

    @property
    def import_method(self: Image) -> ImportMethod:
        return ImportMethod.IMAGE

    async def _perform_extraction(
        self: Image,
        url: str,
        request_id: str,
    ) -> EventData | None:
        """Provider-specific logic for extracting event data from image."""
        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            "Downloading image",
            0.2,
        )

        # Download and validate image
        result = await self.image_service.validate_and_download(url)
        if not result:
            raise Exception("Invalid or inaccessible image")

        image_data, mime_type = result

        await self.send_progress(
            request_id,
            ImportStatus.RUNNING,
            f"Processing {len(image_data) // 1024}KB image",
            0.5,
        )

        # Extract with LLM service
        try:
            llm_service: LLMService = self.get_service("llm")
            event_data = await llm_service.extract_from_image(
                image_data,
                mime_type,
                url,
            )
        except Exception as e:
            logger.exception(ServiceMessages.LLM_EXTRACTION_FAILED)
            raise Exception(AgentMessages.IMAGE_EXTRACT_FAILED) from e

        if not event_data:
            raise Exception(AgentMessages.IMAGE_EXTRACT_FAILED)

        return event_data
