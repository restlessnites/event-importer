import hashlib
import json
from typing import Any

from .connection import get_db_session
from .models import EventCache, Submission


def hash_event_data(event_data: dict[str, Any]) -> str:
    """Create a hash of event data for change detection"""
    # Create a canonical representation for hashing
    canonical = json.dumps(event_data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def cache_event(url: str, event_data: dict[str, Any]) -> EventCache:
    """Cache scraped event data"""
    data_hash = hash_event_data(event_data)

    with get_db_session() as db:
        # Check if event already exists
        existing = db.query(EventCache).filter(EventCache.source_url == url).first()

        if existing:
            # Update if data has changed
            if existing.data_hash != data_hash:
                existing.scraped_data = event_data
                existing.data_hash = data_hash
                # updated_at will be set automatically
            return existing
        # Create new cache entry
        cached_event = EventCache(
            source_url=url,
            scraped_data=event_data,
            data_hash=data_hash,
        )
        db.add(cached_event)
        db.flush()  # Get the ID
        return cached_event


def get_cached_event(url: str) -> dict[str, Any] | None:
    """Get cached event data by URL"""
    with get_db_session() as db:
        event_cache = db.query(EventCache).filter(EventCache.source_url == url).first()
        if event_cache:
            # Return the scraped_data dict instead of the SQLAlchemy object
            return event_cache.scraped_data
        return None


def get_submission_status(event_id: int, service_name: str) -> Submission | None:
    """Get the latest submission status for an event and service"""
    with get_db_session() as db:
        return (
            db.query(Submission)
            .filter(
                Submission.event_cache_id == event_id,
                Submission.service_name == service_name,
            )
            .order_by(Submission.submitted_at.desc())
            .first()
        )


def has_been_submitted(event_id: int, service_name: str) -> bool:
    """Check if event has been successfully submitted to a service"""
    submission = get_submission_status(event_id, service_name)
    return submission is not None and submission.status == "success"


def mark_submission_failed(submission_id: int, error_message: str) -> None:
    """Mark a submission as failed"""
    with get_db_session() as db:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if submission:
            submission.status = "failed"
            submission.error_message = error_message
            submission.retry_count += 1


def mark_submission_success(submission_id: int, response_data: dict[str, Any]) -> None:
    """Mark a submission as successful"""
    with get_db_session() as db:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if submission:
            submission.status = "success"
            submission.response_data = response_data
            submission.error_message = None
