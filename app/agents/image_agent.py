"""Agent for importing events from direct image URLs."""

import logging
from typing import Optional

from app.shared.agent import Agent
from app.schemas import EventData, ImportMethod, ImportStatus


logger = logging.getLogger(__name__)


class ImageAgent(Agent):
    """Agent for importing events from image URLs (flyers/posters)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use shared services
        self.http = self.services["http"]
        self.claude = self.services["claude"]
        self.image_service = self.services["image"]

    @property
    def name(self) -> str:
        return "ImageExtractor"

    @property
    def import_method(self) -> ImportMethod:
        return ImportMethod.IMAGE

    async def import_event(self, url: str, request_id: str) -> Optional[EventData]:
        """Import event from image URL."""
        self.start_timer()

        await self.send_progress(
            request_id, ImportStatus.RUNNING, "Downloading image", 0.2
        )

        try:
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

            # Extract with Claude - it will generate descriptions if needed
            event_data = await self.claude.extract_from_image(
                image_data, mime_type, url
            )

            if not event_data:
                raise Exception("Could not extract event information from image")

            await self.send_progress(
                request_id,
                ImportStatus.SUCCESS,
                "Successfully imported event from image",
                1.0,
                data=event_data,
            )

            return event_data

        except Exception as e:
            logger.error(f"Image import failed: {e}")
            await self.send_progress(
                request_id,
                ImportStatus.FAILED,
                f"Import failed: {str(e)}",
                1.0,
                error=str(e),
            )
            return None
