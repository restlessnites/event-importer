"""Tests for statistics module."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.shared.statistics import StatisticsService
from app.shared.database.models import EventCache, Submission


def test_get_event_statistics(mocker):
    """Test getting event statistics."""
    # Mock database session
    mock_db = MagicMock()
    mock_query = MagicMock()
    
    # Setup count returns
    mock_query.count.side_effect = [
        100,  # total_events
        10,   # events_today
        25,   # events_this_week
        80,   # events_with_submissions
        5,    # future_events
        3,    # events_this_month
        7,    # recent_events
    ]
    
    # Setup filter returns
    mock_query.filter.return_value = mock_query
    mock_query.join.return_value = mock_query
    mock_query.distinct.return_value = mock_query
    
    # Mock the values() and group_by() for source stats
    mock_query.values.return_value.all.return_value = [
        ("ra.co", 40),
        ("dice.fm", 30),
        ("ticketmaster.com", 30)
    ]
    mock_query.group_by.return_value = mock_query
    
    mock_db.query.return_value = mock_query
    
    # Create service with mocked session
    service = StatisticsService(db_session=mock_db)
    stats = service.get_event_statistics()
    
    # Verify results
    assert stats["total_events"] == 100
    assert stats["events_today"] == 10
    assert stats["events_this_week"] == 25
    assert stats["unsubmitted_events"] == 20  # 100 - 80
    assert "events_by_source" in stats


def test_get_submission_statistics(mocker):
    """Test getting submission statistics."""
    mock_db = MagicMock()
    mock_query = MagicMock()
    
    # Mock the submission counts
    mock_query.count.side_effect = [
        150,  # total_submissions
        100,  # successful
        30,   # pending
        20,   # failed
    ]
    
    # Setup filter returns
    mock_query.filter.return_value = mock_query
    
    mock_db.query.return_value = mock_query
    
    # Create service with mocked session
    service = StatisticsService(db_session=mock_db)
    stats = service.get_submission_statistics()
    
    # Verify results
    assert stats["total_submissions"] == 150
    assert stats["status_breakdown"]["success"] == 100
    assert stats["status_breakdown"]["pending"] == 30
    assert stats["status_breakdown"]["failed"] == 20
