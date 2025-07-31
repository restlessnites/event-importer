"""Tests for statistics module."""

from unittest.mock import MagicMock

from app.shared.statistics import StatisticsService


def test_get_event_statistics(mocker):
    """Test getting event statistics."""
    # Mock database session
    mock_session = MagicMock()
    mock_query = MagicMock()

    # Setup count returns
    mock_query.count.side_effect = [
        100,  # total_events
        10,  # events_today
        25,  # events_this_week
        80,  # events_with_submissions
        5,  # future_events
        3,  # events_this_month
        7,  # recent_events
    ]

    # Setup filter returns
    mock_query.filter.return_value = mock_query
    mock_query.join.return_value = mock_query
    mock_query.distinct.return_value = mock_query

    # Mock the values() and group_by() for source stats
    mock_query.values.return_value.all.return_value = [
        ("ra.co", 40),
        ("dice.fm", 30),
        ("ticketmaster.com", 30),
    ]
    mock_query.group_by.return_value = mock_query

    mock_session.query.return_value = mock_query

    # Make the mock_db work as a context manager
    mock_db = MagicMock()
    mock_db.__enter__.return_value = mock_session
    mock_db.__exit__.return_value = None

    # Create service with mocked session
    service = StatisticsService(db_session=mock_db)
    stats = service.get_event_statistics()

    # Verify results
    assert stats["total_events"] == 100
    assert stats["events_today"] == 10
    assert stats["events_this_week"] == 25
    assert stats["events_with_submissions"] == 80
    assert stats["unsubmitted_events"] == 20  # 100 - 80
    assert "last_updated" in stats


def test_get_submission_statistics(mocker):
    """Test getting submission statistics."""
    mock_session = MagicMock()
    mock_query = MagicMock()

    # First count will be total_submitted_events
    mock_query.count.return_value = 150

    # Mock the group_by queries for status and service counts
    status_all_result = [("success", 100), ("pending", 30), ("failed", 20)]

    service_all_result = [("ticketfairy", 150)]

    # Create a mock that returns the right data for each query
    def mock_all():
        if mock_query.group_by.call_count == 1:
            return status_all_result
        return service_all_result

    mock_query.group_by.return_value.all = mock_all
    mock_query.filter.return_value = mock_query

    mock_session.query.return_value = mock_query

    # Make the mock_db work as a context manager
    mock_db = MagicMock()
    mock_db.__enter__.return_value = mock_session
    mock_db.__exit__.return_value = None

    # Create service with mocked session
    service = StatisticsService(db_session=mock_db)
    stats = service.get_submission_statistics()

    # Verify results
    assert stats["total_submitted_events"] == 150
    assert stats["by_status"]["success"] == 100
    assert stats["by_status"]["pending"] == 30
    assert stats["by_status"]["failed"] == 20
    assert stats["by_service"]["ticketfairy"] == 150
    assert stats["success_rate"] == 66.67  # (100/150) * 100 rounded
    assert "last_updated" in stats
