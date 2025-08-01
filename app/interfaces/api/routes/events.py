"""Event import API routes."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.router import Router
from app.core.schemas import EventData
from app.interfaces.api.models.requests import (
    ImportEventRequest,
    RebuildDescriptionRequest,
    RebuildGenresRequest,
    RebuildImageRequest,
    UpdateEventRequest,
)
from app.interfaces.api.models.responses import (
    ImportEventResponse,
    ProgressResponse,
    RebuildDescriptionResponse,
    RebuildGenresResponse,
    RebuildImageResponse,
    UpdateEventResponse,
)
from app.shared.database.connection import get_db_session
from app.shared.database.models import EventCache
from app.shared.service_errors import ServiceErrorFormatter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])

# Global router instance - reset on reload
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

        if request.ignore_cache:
            request_data["ignore_cache"] = request.ignore_cache

        # Route the request
        router_instance = get_router()
        result = await router_instance.route_request(request_data)

        # Add formatted service failure info if present
        if result.get("service_failures"):
            failure_info = ServiceErrorFormatter.format_for_api(
                result["service_failures"]
            )
            result.update(failure_info)

        # Check if import failed
        if not result.get("success", False):
            error_msg = result.get("error", "Import failed")
            # Determine appropriate status code based on error
            status_code = 400 if "invalid" in error_msg.lower() else 500
            raise HTTPException(status_code=status_code, detail=error_msg)

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


@router.get("")
async def list_events(
    limit: int = 50,
    source: str | None = None,
    skip: int = 0,
) -> dict[str, Any]:
    """List events with optional filtering."""

    try:
        with get_db_session() as db:
            query = db.query(EventCache)

            # Filter by source domain if specified
            if source:
                query = query.filter(EventCache.source_url.like(f"%{source}%"))

            # Get total count
            total = query.count()

            # Get paginated results
            events = (
                query.order_by(EventCache.scraped_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )

            # Format results
            results = []
            for event in events:
                data = event.scraped_data or {}
                results.append(
                    {
                        "id": event.id,
                        "title": data.get("title", "Untitled Event"),
                        "venue": data.get("venue"),
                        "date": data.get("date"),
                        "source_url": event.source_url,
                        "scraped_at": event.scraped_at.isoformat()
                        if event.scraped_at
                        else None,
                        "genres": data.get("genres", []),
                        "lineup": data.get("lineup", []),
                    }
                )

            return {
                "total": total,
                "limit": limit,
                "skip": skip,
                "events": results,
            }

    except Exception as e:
        logger.exception("List events error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{event_id}")
async def get_event(event_id: int) -> dict[str, Any]:
    """Get a single event by ID."""

    try:
        with get_db_session() as db:
            event = db.query(EventCache).filter(EventCache.id == event_id).first()

            if not event:
                raise HTTPException(
                    status_code=404, detail=f"Event {event_id} not found"
                )

            data = event.scraped_data or {}
            return {
                "id": event.id,
                "title": data.get("title", "Untitled Event"),
                "venue": data.get("venue"),
                "date": data.get("date"),
                "end_date": data.get("end_date"),
                "time": data.get("time"),
                "location": data.get("location"),
                "lineup": data.get("lineup", []),
                "genres": data.get("genres", []),
                "short_description": data.get("short_description"),
                "long_description": data.get("long_description"),
                "images": data.get("images", {}),
                "cost": data.get("cost"),
                "ticket_url": data.get("ticket_url"),
                "source_url": event.source_url,
                "scraped_at": event.scraped_at.isoformat()
                if event.scraped_at
                else None,
                "promoters": data.get("promoters", []),
                "minimum_age": data.get("minimum_age"),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Get event error for ID {event_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/{event_id}/rebuild/description", response_model=RebuildDescriptionResponse
)
async def rebuild_event_description(
    event_id: int,
    request: RebuildDescriptionRequest,
) -> RebuildDescriptionResponse:
    """Rebuild a specific description for an event (preview only)."""
    try:
        router_instance = get_router()
        description_result = await router_instance.importer.rebuild_description(
            event_id,
            description_type=request.description_type,
            supplementary_context=request.supplementary_context,
        )

        if description_result:
            # Get the full event data to return
            with get_db_session() as db:
                event = db.query(EventCache).filter(EventCache.id == event_id).first()
                if event and event.scraped_data:
                    # Create EventData with updated descriptions
                    event_data = EventData(**event.scraped_data)
                    if description_result.short_description is not None:
                        event_data.short_description = (
                            description_result.short_description
                        )
                    if description_result.long_description is not None:
                        event_data.long_description = (
                            description_result.long_description
                        )

                    return RebuildDescriptionResponse(
                        success=True,
                        event_id=event_id,
                        message=f"{request.description_type.capitalize()} description regenerated (preview only)",
                        data=event_data,
                    )
        raise HTTPException(
            status_code=404,
            detail=f"Event not found or failed to rebuild for ID: {event_id}",
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"Failed to rebuild descriptions for event {event_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{event_id}", response_model=UpdateEventResponse)
async def update_event(
    event_id: int,
    request: UpdateEventRequest,
) -> UpdateEventResponse:
    """Update specific fields of an event."""
    try:
        # Get the router instance
        router_instance = get_router()

        # Get non-None fields from the request
        updates = request.model_dump(exclude_unset=True)

        if not updates:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        # Update the event
        updated_event = await router_instance.importer.update_event(event_id, updates)

        if updated_event:
            return UpdateEventResponse(
                success=True,
                event_id=event_id,
                message=f"Successfully updated {len(updates)} field(s)",
                data=updated_event,
                updated_fields=list(updates.keys()),
            )

        raise HTTPException(
            status_code=404, detail=f"Event not found with ID: {event_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update event {event_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{event_id}/rebuild/genres", response_model=RebuildGenresResponse)
async def rebuild_event_genres(
    event_id: int,
    request: RebuildGenresRequest,
) -> RebuildGenresResponse:
    """Rebuild genres for an event (preview only)."""
    try:
        router_instance = get_router()
        genre_result, service_failures = await router_instance.importer.rebuild_genres(
            event_id,
            supplementary_context=request.supplementary_context,
        )

        # Format service failures if any
        result: dict[str, Any] = {"service_failures": []}
        if service_failures:
            # Convert ServiceFailure objects to dicts for the formatter
            failure_dicts = [f.model_dump() for f in service_failures]
            result["service_failures"] = failure_dicts
            failure_info = ServiceErrorFormatter.format_for_api(failure_dicts)
            result.update(failure_info)

        if genre_result:
            # Get the full event data to return
            with get_db_session() as db:
                event = db.query(EventCache).filter(EventCache.id == event_id).first()
                if event and event.scraped_data:
                    # Create EventData with updated genres
                    event_data = EventData(**event.scraped_data)
                    event_data.genres = genre_result.genres

                    return RebuildGenresResponse(
                        success=True,
                        event_id=event_id,
                        message="Genres regenerated (preview only)",
                        data=event_data,
                        genres_found=genre_result.genres,
                        **result,  # Include service failure info
                    )

        # If no event data returned, include error info
        error_msg = f"Event not found or failed to rebuild genres for ID: {event_id}"
        if service_failures:
            error_msg += f". {result.get('service_failure_summary', '')}"

        raise HTTPException(
            status_code=404,
            detail=error_msg,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"Failed to rebuild genres for event {event_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# TODO: Move this to a shared location
def _extract_image_search_results_for_api(
    image_search: Any,
) -> tuple[list[dict], dict | None]:
    """Extract and format image candidates and best image from search results for API response."""
    if not image_search:
        return [], None

    candidates = [c.model_dump() for c in image_search.candidates]
    best_image = image_search.selected.model_dump() if image_search.selected else None

    if image_search.original:
        original_data = image_search.original.model_dump()
        original_data["source"] = "original"
        if not any(c["url"] == original_data["url"] for c in candidates):
            candidates.append(original_data)

    return candidates, best_image


@router.post("/{event_id}/rebuild/image", response_model=RebuildImageResponse)
async def rebuild_event_image(
    event_id: int,
    request: RebuildImageRequest,
) -> RebuildImageResponse:
    """Rebuild image for an event (preview only)."""
    try:
        router_instance = get_router()
        updated_event, service_failures = await router_instance.importer.rebuild_image(
            event_id,
            supplementary_context=request.supplementary_context,
        )

        result: dict[str, Any] = {"service_failures": []}
        if service_failures:
            failure_dicts = [f.model_dump() for f in service_failures]
            result["service_failures"] = failure_dicts
            result.update(ServiceErrorFormatter.format_for_api(failure_dicts))

        if updated_event:
            candidates, best_image = _extract_image_search_results_for_api(
                updated_event.image_search
            )
            return RebuildImageResponse(
                success=True,
                event_id=event_id,
                message="Image search completed (preview only)",
                data=updated_event,
                image_candidates=candidates,
                best_image=best_image,
                **result,
            )

        error_msg = f"Event not found or failed to rebuild image for ID: {event_id}"
        if service_failures:
            error_msg += f". {result.get('service_failure_summary', '')}"

        raise HTTPException(status_code=404, detail=error_msg)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to rebuild image for event {event_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e
