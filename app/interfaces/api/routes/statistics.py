from typing import Any

from fastapi import APIRouter, HTTPException

from app.shared.statistics import StatisticsService

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/events")
async def get_event_statistics() -> dict[str, Any]:
    """Get core event statistics without integration dependencies"""
    try:
        stats_service = StatisticsService()
        return stats_service.get_event_statistics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve event statistics: {e!s}",
        ) from e


@router.get("/submissions")
async def get_submission_statistics() -> dict[str, Any]:
    """Get submission/integration statistics"""
    try:
        stats_service = StatisticsService()
        return stats_service.get_submission_statistics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve submission statistics: {e!s}",
        ) from e


@router.get("/combined")
async def get_combined_statistics() -> dict[str, Any]:
    """Get all statistics combined"""
    try:
        stats_service = StatisticsService()
        return stats_service.get_combined_statistics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve combined statistics: {e!s}",
        ) from e


@router.get("/trends")
async def get_event_trends(days: int | None = 7) -> dict[str, Any]:
    """Get event trends over the specified number of days"""
    if days is not None and (days < 1 or days > 365):
        raise HTTPException(
            status_code=400,
            detail="Days parameter must be between 1 and 365",
        )

    try:
        stats_service = StatisticsService()
        return stats_service.get_event_trends(days or 7)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve event trends: {e!s}",
        ) from e


@router.get("/detailed")
async def get_detailed_statistics() -> dict[str, Any]:
    """Get comprehensive statistics including trends"""
    try:
        stats_service = StatisticsService()
        return stats_service.get_detailed_statistics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve detailed statistics: {e!s}",
        ) from e


@router.get("/health")
async def statistics_health() -> dict[str, str]:
    """Health check for statistics service"""
    return {"status": "healthy", "service": "statistics"}
