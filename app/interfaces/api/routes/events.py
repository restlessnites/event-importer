"""Event import API routes."""

import logging

from fastapi import APIRouter, HTTPException

from app.core.router import Router
from app.interfaces.api.models import (
    ImportEventRequest,
    ImportEventResponse,
    ProgressResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])

# Global router instance
_router: Router | None = None


def get_router() -> Router:
    """Get the global router instance."""
    global _router
    if _router is None:
        _router = Router()
    return _router


@router.post("/import", response_model=ImportEventResponse)
async def import_event(request: ImportEventRequest) -> ImportEventResponse:
    """Import an event from a URL."""
    try:
        # Convert request to dict
        request_data = {
            "url": str(request.url),
            "timeout": request.timeout,
        }

        if request.force_method:
            request_data["force_method"] = request.force_method

        if request.include_raw_data:
            request_data["include_raw_data"] = request.include_raw_data

        # Route the request
        router_instance = get_router()
        result = await router_instance.route_request(request_data)

        # Convert to response model
        return ImportEventResponse(**result)

    except Exception as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/import/{request_id}/progress", response_model=ProgressResponse)
async def get_import_progress(request_id: str) -> ProgressResponse:
    """Get progress for an import request."""
    try:
        router_instance = get_router()
        result = await router_instance.get_progress(request_id)

        return ProgressResponse(**result)

    except Exception as e:
        logger.error(f"Progress error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
