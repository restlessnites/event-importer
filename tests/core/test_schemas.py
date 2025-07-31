"""Tests for the data schemas."""

import pytest

from app.schemas import EventData, EventTime


@pytest.mark.parametrize(
    "start_time, end_time, start_date_str, expected_end_date_str",
    [
        # Test case 1: Event ends on the same day
        ("20:00", "23:00", "2024-01-01", "2024-01-01"),
        # Test case 2: Event crosses midnight
        ("22:00", "02:00", "2024-01-01", "2024-01-02"),
        # Test case 3: Event ends exactly at midnight (still same day)
        ("20:00", "00:00", "2024-01-01", "2024-01-01"),
        # Test case 4: 12-hour format
        ("10:00 PM", "2:00 AM", "2024-03-10", "2024-03-11"),
        # Test case 5: Descriptive times
        ("Doors at 7pm", "Ends at 1am", "2024-07-04", "2024-07-05"),
        # Edge Case 6: New Year's Eve rollover
        ("23:00", "01:00", "2023-12-31", "2024-01-01"),
        # Edge Case 7: Leap day rollover
        ("22:00", "02:00", "2024-02-29", "2024-03-01"),
    ],
)
def test_end_date_calculation(
    start_time, end_time, start_date_str, expected_end_date_str
):
    """Verify that end_date is calculated correctly."""
    event = EventData(
        title="Test Event",
        date=start_date_str,
        time=EventTime(start=start_time, end=end_time),
    )
    assert event.end_date == expected_end_date_str


def test_end_date_not_overwritten():
    """Verify that an existing end_date is not overwritten."""
    start_date = "2024-01-01"
    predefined_end_date = "2024-01-05"  # An arbitrary, different end date
    event = EventData(
        title="Test Event",
        date=start_date,
        end_date=predefined_end_date,
        time=EventTime(start="22:00", end="02:00"),
    )
    assert event.end_date == predefined_end_date


def test_end_date_insufficient_info():
    """Verify that end_date is not calculated if info is missing."""
    # Case 1: Missing end time
    event_no_end_time = EventData(
        title="Test Event",
        date="2024-01-01",
        time=EventTime(start="22:00"),
    )
    assert event_no_end_time.end_date is None

    # Case 2: Missing start time
    event_no_start_time = EventData(
        title="Test Event",
        date="2024-01-01",
        time=EventTime(end="02:00"),
    )
    assert event_no_start_time.end_date is None

    # Case 3: Missing date
    event_no_date = EventData(
        title="Test Event",
        time=EventTime(start="22:00", end="02:00"),
    )
    assert event_no_date.end_date is None

    # Case 4: Missing time object entirely
    event_no_time_obj = EventData(
        title="Test Event",
        date="2024-01-01",
    )
    assert event_no_time_obj.end_date is None
