"""TicketFairy routes."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from ...shared.database.connection import get_db_session, init_db
from ...shared.database.models import EventCache, Submission
from .submitter import TicketFairySubmitter


class SubmissionRequest(BaseModel):
    selector: str = "unsubmitted"
    url: str | None = None
    dry_run: bool = False


class URLSubmissionRequest(BaseModel):
    url: str
    dry_run: bool = False


router = APIRouter(prefix="/integrations/ticketfairy", tags=["ticketfairy"])


@router.post("/submit")
async def submit_events(request: SubmissionRequest) -> dict[str, Any]:
    """Submit events to TicketFairy"""
    try:
        submitter = TicketFairySubmitter()

        if request.url:
            result = await submitter.submit_by_url(request.url, dry_run=request.dry_run)
        else:
            result = await submitter.submit_events(
                request.selector, dry_run=request.dry_run,
            )

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Submission failed: {e!s}",
        ) from e


@router.post("/submit-url")
async def submit_by_url(request: URLSubmissionRequest) -> dict[str, Any]:
    """Submit a specific event by URL"""
    try:
        submitter = TicketFairySubmitter()
        result = await submitter.submit_by_url(request.url, dry_run=request.dry_run)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Submission failed: {e!s}",
        ) from e


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Get TicketFairy submission status"""
    try:
        with get_db_session() as db:
            # Get submission counts by status
            status_counts = (
                db.query(Submission.status, func.count(Submission.id))
                .filter(Submission.service_name == "ticketfairy")
                .group_by(Submission.status)
                .all()
            )

            # Get total cached events
            total_events = db.query(func.count(EventCache.id)).scalar()

            # Get unsubmitted count
            submitted_event_ids = (
                db.query(Submission.event_cache_id)
                .filter(Submission.service_name == "ticketfairy")
                .subquery()
            )
            unsubmitted_count = (
                db.query(func.count(EventCache.id))
                .filter(~EventCache.id.in_(submitted_event_ids))
                .scalar()
            )

            status_breakdown = {status: count for status, count in status_counts}

            return {
                "service": "ticketfairy",
                "total_events": total_events,
                "unsubmitted": unsubmitted_count,
                "status_breakdown": status_breakdown,
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get status: {e!s}",
        ) from e


@router.post("/retry-failed")
async def retry_failed(dry_run: bool = False) -> dict[str, Any]:
    """Retry failed submissions"""
    try:
        submitter = TicketFairySubmitter()
        result = await submitter.submit_events("failed", dry_run=dry_run)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retry failed: {e!s}") from e


# Initialize database when module is imported
init_db()
