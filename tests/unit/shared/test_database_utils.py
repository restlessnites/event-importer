"""Tests for database utility functions."""

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.schemas import EventData
from app.shared.database.utils import get_event, save_event


@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    return EventData(
        title="Test Event",
        venue="Test Venue",
        date="2025-03-01",
        lineup=["Artist 1", "Artist 2"],
        genres=["house", "techno"],
        source_url="https://example.com/event/123",
    )


def test_event_success(db_session: Session, sample_event):
    """Test successfully caching an event."""
    url = "https://example.com/event/123"

    # Cache the event - convert to dict
    save_event(url=url, event_data=sample_event.model_dump(), db=db_session)

    # Retrieve it using get_event to verify
    cached_data = get_event(url, db=db_session)
    assert cached_data is not None
    assert cached_data["title"] == "Test Event"


def test_event_empty(db_session: Session):
    """Test caching an event with empty data raises validation error."""
    url = "https://example.com/event/empty"

    # Empty data should fail validation
    with pytest.raises(ValidationError) as exc_info:
        save_event(url=url, event_data={}, db=db_session)

    # Verify it's missing required fields
    assert "title" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)


def test_event_update_existing(db_session: Session, sample_event):
    """Test updating an existing cached event."""
    url = "https://example.com/event/123"

    # First cache
    save_event(url=url, event_data=sample_event.model_dump(), db=db_session)

    # Get the first cached data
    first_data = get_event(url, db=db_session)
    assert first_data["title"] == "Test Event"

    # Update with new data
    updated_event = sample_event.model_copy()
    updated_event.title = "Updated Event"

    save_event(url=url, event_data=updated_event.model_dump(), db=db_session)

    # Get the updated data
    updated_data = get_event(url, db=db_session)
    assert updated_data["title"] == "Updated Event"


def test_get_event_found(db_session: Session, sample_event):
    """Test retrieving a cached event."""
    url = "https://example.com/event/123"

    # Cache an event
    save_event(url=url, event_data=sample_event.model_dump(), db=db_session)

    # Retrieve it
    cached_data = get_event(url, db=db_session)

    assert cached_data is not None
    assert cached_data["title"] == "Test Event"


def test_get_event_not_found(db_session: Session):
    """Test retrieving a non-existent cached event."""
    url = "https://example.com/nonexistent"

    cached_data = get_event(url, db=db_session)

    assert cached_data is None


def test_get_event_twice(db_session: Session, sample_event):
    """Test caching and retrieving the same event."""
    url = "https://example.com/event/123"

    # Cache an event
    save_event(url=url, event_data=sample_event.model_dump(), db=db_session)

    # Retrieve it twice
    first_get = get_event(url, db=db_session)
    second_get = get_event(url, db=db_session)

    assert first_get is not None
    assert second_get is not None
    assert first_get["title"] == second_get["title"]
