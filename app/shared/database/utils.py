import hashlib
import json

# Log the validation error
import logging
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.schemas import EventData
from app.shared.database.connection import get_db_session
from app.shared.database.models import EventCache, Submission

logger = logging.getLogger(__name__)


def hash_event_data(event_data: dict[str, Any]) -> str:
    """Create a hash of event data for change detection"""
    # Create a canonical representation for hashing
    canonical = json.dumps(event_data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def cache_event(
    url: str, event_data: dict[str, Any], db: Session | None = None
) -> EventCache:
    """Cache scraped event data

    Validates event data before caching to ensure data integrity.
    """
    # Validate the event data before caching
    try:
        # This will raise ValidationError if data is invalid
        validated = EventData(**event_data)
        # Use the validated model's data to ensure proper types
        event_data = validated.model_dump(mode="json")
    except ValidationError as e:
        logger.error(f"Invalid event data for {url}: {e}")
        raise

    data_hash = hash_event_data(event_data)

    def _cache(db_session: Session) -> EventCache:
        # Check if event already exists
        existing = (
            db_session.query(EventCache).filter(EventCache.source_url == url).first()
        )

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
        db_session.add(cached_event)
        db_session.flush()  # Get the ID
        return cached_event

    if db:
        return _cache(db)
    with get_db_session() as db_session:
        return _cache(db_session)


def get_cached_event(
    url: str | None = None, event_id: int | None = None, db: Session | None = None
) -> dict[str, Any] | None:
    """Get cached event data by URL or ID"""

    def _get(db_session: Session) -> dict[str, Any] | None:
        query = db_session.query(EventCache)
        if url:
            query = query.filter(EventCache.source_url == url)
        elif event_id:
            query = query.filter(EventCache.id == event_id)
        else:
            return None  # Either URL or event_id must be provided

        event_cache = query.first()
        if event_cache:
            # Return the scraped_data dict with the database ID included
            data = event_cache.scraped_data.copy()
            data["_db_id"] = event_cache.id
            return data
        return None

    if db:
        return _get(db)
    with get_db_session() as db_session:
        return _get(db_session)


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
