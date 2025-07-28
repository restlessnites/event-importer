"""Event import API routes."""

import logging

from fastapi import APIRouter, HTTPException

from app.core.router import Router
from app.interfaces.api.models.requests import (
    ImportEventRequest,
)
from app.interfaces.api.models.responses import (
    ImportEventResponse,
    ProgressResponse,
    RebuildDescriptionResponse,
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
        logger.exception("Import error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/import/{request_id}/progress", response_model=ProgressResponse)
async def get_import_progress(request_id: str) -> ProgressResponse:
    """Get progress for an import request."""
    try:
        router_instance = get_router()
        result = await router_instance.get_progress(request_id)

        return ProgressResponse(**result)

    except Exception as e:
        logger.exception("Progress error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/{event_id}/rebuild-descriptions", response_model=RebuildDescriptionResponse
)
async def rebuild_event_descriptions(
    event_id: int,
) -> RebuildDescriptionResponse:
    """Rebuild descriptions for a specific event."""
    try:
        router_instance = get_router()
        updated_event = await router_instance.importer.rebuild_descriptions(event_id)

        if updated_event:
            return RebuildDescriptionResponse(
                success=True,
                event_id=event_id,
                message="Descriptions rebuilt successfully",
                data=updated_event,
            )
        raise HTTPException(
            status_code=404,
            detail=f"Event not found or failed to rebuild for ID: {event_id}",
        )

    except Exception as e:
        logger.exception(f"Failed to rebuild descriptions for event {event_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e
