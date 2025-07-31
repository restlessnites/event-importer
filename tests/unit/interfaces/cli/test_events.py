"""Tests for CLI events commands."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from app.interfaces.cli.commands import cli
from app.schemas import EventData, EventLocation, EventTime
from app.shared.database.models import EventCache


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_event_data():
    """Create mock event data."""
    return EventData(
        title="Test Concert",
        venue="The Fillmore",
        date="2025-01-01",
        time=EventTime(start="20:00", timezone="America/Los_Angeles"),
        location=EventLocation(city="San Francisco", state="CA", country="USA"),
        short_description="Rock concert at The Fillmore",
        long_description="A great rock concert at the historic Fillmore venue.",
        genres=["Rock", "Alternative"],
        source_url="https://example.com/event/123",
    )


class TestEventsCLI:
    """Test cases for events CLI commands."""

    def test_list_events_empty(self, runner, db_session, monkeypatch):
        """Test listing events when database is empty."""
        monkeypatch.setattr(
            "app.interfaces.cli.events.get_db_session", lambda: db_session
        )
        result = runner.invoke(cli, ["events", "list"])

        assert result.exit_code == 0
        assert "No events found" in result.output

    def test_list_events_with_data(
        self, runner, db_session, mock_event_data, monkeypatch
    ):
        """Test listing events with data."""
        monkeypatch.setattr(
            "app.interfaces.cli.events.get_db_session", lambda: db_session
        )

        # Add a test event to the database
        event = EventCache(
            source_url="https://example.com/event/123",
            scraped_data=mock_event_data.model_dump(mode="json"),
            data_hash="test_hash",
            scraped_at=datetime.now(UTC),
        )
        db_session.add(event)
        db_session.commit()

        result = runner.invoke(cli, ["events", "list"])

        assert result.exit_code == 0
        assert "Test Concert" in result.output
        assert "example.com" in result.output

    def test_show_event_details(self, runner, db_session, mock_event_data, monkeypatch):
        """Test showing event details."""
        monkeypatch.setattr(
            "app.interfaces.cli.events.get_db_session", lambda: db_session
        )

        # Add a test event to the database
        event = EventCache(
            source_url="https://example.com/event/123",
            scraped_data=mock_event_data.model_dump(mode="json"),
            data_hash="test_hash",
            scraped_at=datetime.now(UTC),
        )
        db_session.add(event)
        db_session.commit()

        result = runner.invoke(cli, ["events", "details", str(event.id)])

        assert result.exit_code == 0
        assert "TEST CONCERT" in result.output
        assert "The Fillmore" in result.output

    def test_show_event_not_found(self, runner, db_session, monkeypatch):
        """Test showing details for non-existent event."""
        monkeypatch.setattr(
            "app.interfaces.cli.events.get_db_session", lambda: db_session
        )
        result = runner.invoke(cli, ["events", "details", "999"])

        assert result.exit_code == 1
        assert "Event with ID 999 not found" in result.output

    def test_import_event_success(self, runner, mock_event_data):
        """Test importing an event successfully."""
        with patch("app.interfaces.cli.import_event._perform_import") as mock_import:
            mock_result = {
                "success": True,
                "data": mock_event_data.model_dump(mode="json"),
                "method_used": "web",
                "import_time": 1.5,
            }
            mock_import.return_value = mock_result

            result = runner.invoke(
                cli, ["events", "import", "https://example.com/event"]
            )

            assert result.exit_code == 0
            assert "Event imported successfully!" in result.output
            assert "Test Concert" in result.output

    def test_import_event_failure(self, runner):
        """Test importing an event with failure."""
        with patch("app.interfaces.cli.import_event._perform_import") as mock_import:
            # The function raises an exception on failure
            mock_import.side_effect = Exception("Failed to fetch URL")

            result = runner.invoke(
                cli, ["events", "import", "https://example.com/event"]
            )

            assert result.exit_code != 0  # Should be non-zero on failure
            assert "Failed to fetch URL" in result.output

    def test_import_event_with_options(self, runner, mock_event_data):
        """Test importing an event with options."""
        with patch("app.interfaces.cli.import_event._perform_import") as mock_import:
            mock_result = {
                "success": True,
                "data": mock_event_data.model_dump(mode="json"),
                "method_used": "api",
                "import_time": 0.8,
            }
            mock_import.return_value = mock_result

            result = runner.invoke(
                cli,
                [
                    "events",
                    "import",
                    "https://example.com/event",
                    "--method",
                    "api",
                    "--timeout",
                    "30",
                    "--ignore-cache",
                ],
            )

            assert result.exit_code == 0
            assert "Event imported successfully!" in result.output

            # Verify the import was called with correct options
            mock_import.assert_called_once()
            args = mock_import.call_args[0]
            assert args[0] == "https://example.com/event"
            assert args[1] == "api"  # method
            assert args[2] == 30  # timeout
            assert args[3] is True  # ignore_cache
