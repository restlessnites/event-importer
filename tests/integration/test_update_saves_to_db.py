"""Integration test to ensure update_event saves to the database."""

from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.importer import EventImporter
from app.core.schemas import EventData
from app.shared.database.models import Base, Event
from app.shared.database.utils import save_event
from config import config


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()
    yield session
    session.close()


@pytest.mark.asyncio
async def test_update_event_saves_to_database(test_db, monkeypatch):
    """Test that update_event properly saves changes to the database."""

    # Patch the database session getter
    @contextmanager
    def mock_get_db_session():
        yield test_db

    monkeypatch.setattr("app.shared.database.utils.get_db_session", mock_get_db_session)

    # Create initial event
    initial_event = EventData(
        title="Original Title",
        venue="Original Venue",
        date="2025-08-16",
        source_url="https://test.com/event",
        lineup=["Artist 1"],
        genres=["Electronic"],
    )

    # Save initial event
    saved_event = save_event(
        str(initial_event.source_url), initial_event.model_dump(mode="json"), db=test_db
    )
    test_db.commit()
    event_id = saved_event.id

    # Verify initial save
    db_event = test_db.query(Event).filter(Event.id == event_id).first()
    assert db_event is not None
    assert db_event.scraped_data["title"] == "Original Title"
    assert db_event.scraped_data["venue"] == "Original Venue"

    # Create importer and update the event
    importer = EventImporter(config)
    updates = {
        "title": "Updated Title",
        "venue": "Updated Venue",
        "lineup": ["Artist 1", "Artist 2", "Artist 3"],
    }

    result = await importer.update_event(event_id, updates)

    # Verify update returned correct data
    assert result is not None
    assert result.title == "Updated Title"
    assert result.venue == "Updated Venue"
    assert result.lineup == ["Artist 1", "Artist 2", "Artist 3"]

    # CRITICAL: Verify changes were saved to database
    # Re-query the event because the session was closed
    updated_db_event = test_db.query(Event).filter(Event.id == event_id).first()
    assert updated_db_event is not None
    assert updated_db_event.scraped_data["title"] == "Updated Title"
    assert updated_db_event.scraped_data["venue"] == "Updated Venue"
    assert updated_db_event.scraped_data["lineup"] == [
        "Artist 1",
        "Artist 2",
        "Artist 3",
    ]

    # Verify other fields remained unchanged
    assert updated_db_event.scraped_data["genres"] == ["Electronic"]
    assert updated_db_event.scraped_data["date"] == "2025-08-16"


@pytest.mark.asyncio
async def test_update_nonexistent_event_returns_none(test_db, monkeypatch):
    """Test that updating a non-existent event returns None."""

    @contextmanager
    def mock_get_db_session():
        yield test_db

    monkeypatch.setattr("app.shared.database.utils.get_db_session", mock_get_db_session)

    importer = EventImporter(config)
    result = await importer.update_event(999, {"title": "New Title"})

    assert result is None
