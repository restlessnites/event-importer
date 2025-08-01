# app/core/router.py
"""Simple request router using the importer."""

from __future__ import annotations

import logging
from typing import Any

from app.core.importer import EventImporter
from app.core.schemas import ImportRequest, ImportStatus
from config import config

logger = logging.getLogger(__name__)


class Router:
    """Routes import requests to the importer."""

    def __init__(self: Router) -> None:
        """Initialize router with importer."""
        self.config = config
        self.importer = EventImporter(self.config)

    async def route_request(
        self: Router,
        request_data: dict[str, Any],
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
            result = await self.importer.import_event(request.url)

            # Convert to response format
            response = {
                "success": result.status == ImportStatus.SUCCESS,
                "method_used": result.method_used.value if result.method_used else None,
                "import_time": result.import_time,
            }

            # Add service failures if any
            if result.service_failures:
                response["service_failures"] = [
                    failure.model_dump() for failure in result.service_failures
                ]

            if result.status == ImportStatus.SUCCESS and result.event_data:
                response["data"] = result.event_data.model_dump(mode="json")
            else:
                response["error"] = result.error or "Import failed"

            return response

        except (ValueError, TypeError, KeyError) as e:
            logger.exception("Router error")
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.exception("Unexpected error in route_request")
            error_msg = str(e)
            # Extract more specific error information if available
            if hasattr(e, "__class__"):
                error_msg = f"{e.__class__.__name__}: {error_msg}"
            return {
                "success": False,
                "error": error_msg,
                "method_used": None,
            }

    async def get_progress(self: Router, request_id: str) -> dict[str, Any]:
        """Get progress history for a request."""
        history = self.importer.progress_tracker.get_history(request_id)

        return {
            "request_id": request_id,
            "updates": [update.model_dump(mode="json") for update in history],
        }

    async def close(self: Router) -> None:
        """Close any resources held by the router."""
        # Close HTTP service in the importer
        if hasattr(self.importer, "close"):
            await self.importer.close()
