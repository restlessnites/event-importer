"""Statistics command implementation."""

import click
import clicycle

from app.shared.statistics import StatisticsService, get_statistics


def show_stats(detailed: bool, combined: bool = False) -> None:
    """Show database statistics."""
    del combined  # Unused after refactoring
    try:
        stats_service = get_statistics()
        if detailed:
            _display_detailed_statistics(stats_service)
        else:
            _display_combined_statistics(stats_service)
    except Exception as e:
        raise click.ClickException(f"Failed to get statistics: {e}") from e


def _display_detailed_statistics(stats_service: StatisticsService) -> None:
    """Display detailed statistics."""
    stats_data = stats_service.get_detailed_statistics()
    clicycle.header("Detailed Statistics")
    for category, data in stats_data.items():
        if isinstance(data, dict):
            clicycle.info(f"{category}:")
            for key, value in data.items():
                clicycle.info(f"  {key}: {value}")
        else:
            clicycle.info(f"{category}: {data}")


def _display_combined_statistics(stats_service: StatisticsService) -> None:
    """Display combined statistics."""
    stats_data = stats_service.get_combined_statistics()
    clicycle.header("Event Statistics")

    event_stats = stats_data.get("events", {})
    clicycle.info(f"Total Events: {event_stats.get('total_events', 0)}")
    clicycle.info(f"Events Today: {event_stats.get('events_today', 0)}")
    clicycle.info(f"Events This Week: {event_stats.get('events_this_week', 0)}")
    clicycle.info(f"Unsubmitted Events: {event_stats.get('unsubmitted_events', 0)}")

    submission_stats = stats_data.get("submissions", {})
    if submission_stats.get("total_submitted_events", 0) > 0:
        clicycle.info("Submissions:")
        clicycle.info(
            f"  Total Submitted: {submission_stats.get('total_submitted_events', 0)}"
        )
        clicycle.info(f"  Success Rate: {submission_stats.get('success_rate', 0)}%")
        if by_service := submission_stats.get("by_service", {}):
            clicycle.info("Submissions by Service:")
            for service, count in by_service.items():
                clicycle.info(f"  {service}: {count}")
