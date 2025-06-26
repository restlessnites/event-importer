# app/core/router.py
"""Simple request router using the importer."""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_config
from app.core.importer import EventImporter
from app.errors import handle_errors_async
from app.schemas import ImportRequest, ImportStatus

logger = logging.getLogger(__name__)


class Router:
    """Routes import requests to the importer."""

    def __init__(self: Router) -> None:
        """Initialize router with importer."""
        self.config = get_config()
        self.importer = EventImporter(self.config)

    @handle_errors_async(reraise=False)
    async def route_request(
        self: Router, request_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Route an import request.

        Args:
            request_data: Raw request data

        Returns:
            Response data as dict

        """
        try:
            # Parse request
            request = ImportRequest(**request_data)

            logger.info(f"Routing import request for: {request.url}")

            # Execute import
            result = await self.importer.import_event(request)

            # Convert to response format
            if result.status == ImportStatus.SUCCESS and result.event_data:
                return {
                    "success": True,
                    "data": result.event_data.model_dump(mode="json"),
                    "method_used": result.method_used.value
                    if result.method_used
                    else None,
                    "import_time": result.import_time,
                }
            return {
                "success": False,
                "error": result.error or "Import failed",
                "method_used": result.method_used.value
                if result.method_used
                else None,
            }

        except (ValueError, TypeError, KeyError) as e:
            logger.exception("Router error")
            return {
                "success": False,
                "error": str(e),
            }

    async def get_progress(self: Router, request_id: str) -> dict[str, Any]:
        """Get progress history for a request."""
        history = self.importer.get_progress_history(request_id)

        return {
            "request_id": request_id,
            "updates": [update.model_dump(mode="json") for update in history],
        }
