"""Agent for importing events from direct image URLs."""

from __future__ import annotations

import logging
from typing import Any

from app.error_messages import AgentMessages, ServiceMessages
from app.schemas import EventData, ImportMethod, ImportStatus
from app.services.image import ImageService
from app.shared.agent import Agent
from app.shared.http import HTTPService

logger = logging.getLogger(__name__)




class ImageAgent(Agent):
    """Agent for importing events from image URLs (flyers/posters)."""

    http: HTTPService
    image_service: ImageService

    def __init__(self, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> None:
        super().__init__(*args, **kwargs)
        # Use shared services with proper error handling
        self.http = self.get_service("http")
        self.image_service = self.get_service("image")

    @property
    def name(self: ImageAgent) -> str:
        return "ImageAgent"

    @property
    def import_method(self: ImageAgent) -> ImportMethod:
        return ImportMethod.IMAGE

    async def import_event(
        self: ImageAgent, url: str, request_id: str
    ) -> EventData | None:
        """Import event from image URL."""
        self.start_timer()

        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Downloading image", 0.2
        )

        try:
            # Download and validate image
            result = await self.image_service.validate_and_download(url)
            if not result:
                error_msg = "Invalid or inaccessible image"
                raise Exception(error_msg)

            image_data, mime_type = result

            await self.send_progress(
                request_id,
                ImportStatus.RUNNING,
                f"Processing {len(image_data) // 1024}KB image",
                0.5,
            )

            # Extract with LLM service - use safe service access
            try:
                llm_service = self.get_service("llm")
                event_data = await llm_service.extract_from_image(
                    image_data, mime_type, url
                )
            except Exception as e:
                logger.exception(ServiceMessages.LLM_EXTRACTION_FAILED)
                error_msg = AgentMessages.IMAGE_EXTRACT_FAILED
                raise Exception(error_msg) from e

            if not event_data:
                error_msg = AgentMessages.IMAGE_EXTRACT_FAILED
                raise Exception(error_msg)

            await self.send_progress(
                request_id,
                ImportStatus.SUCCESS,
                "Successfully imported event from image",
                1.0,
                data=event_data,
            )

            return event_data

        except (ValueError, TypeError, KeyError) as e:
            logger.exception(AgentMessages.IMAGE_IMPORT_FAILED)
            await self.send_progress(
                request_id,
                ImportStatus.FAILED,
                f"Import failed: {str(e)}",
                1.0,
                error=str(e),
            )
            return None
