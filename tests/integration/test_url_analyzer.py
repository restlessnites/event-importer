#!/usr/bin/env -S uv run python
"""Test the URL analyzer with various URLs using CLI."""

import clicycle
import pytest

from app.shared.url_analyzer import URLAnalyzer, URLType


@pytest.mark.parametrize(
    "url, expected_type, expected_id",
    [
        # Resident Advisor
        ("https://ra.co/events/1234567", URLType.RESIDENT_ADVISOR, "1234567"),
        (
            "https://www.residentadvisor.net/events/9876543",
            URLType.RESIDENT_ADVISOR,
            "9876543",
        ),
        ("ra.co/events/123", URLType.RESIDENT_ADVISOR, "123"),
        # Ticketmaster (ID extraction is now supported)
        (
            "https://www.ticketmaster.com/event/G5vYZ9v1AUf-G",
            URLType.TICKETMASTER,
            None,
        ),
        (
            "https://www.livenation.com/event/G5vYZ9v1AUf-G",
            URLType.TICKETMASTER,
            None,
        ),
        # Dice.fm
        ("https://dice.fm/event/q2r5ro-some-event", URLType.DICE, "q2r5ro"),
        ("https://dice.fm/event/some-event-no-id", URLType.DICE, None),
        # Generic/Unknown
        ("https://example.com/events/cool-party", URLType.UNKNOWN, None),
        ("https://www.eventbrite.com/e/123456", URLType.UNKNOWN, None),
        # Edge cases that should not match a specific type
        ("https://ra.co/news/123", URLType.UNKNOWN, None),
        ("https://ticketmaster.com/browse", URLType.TICKETMASTER, None),
        ("example.com", URLType.UNKNOWN, None),
    ],
)
def test_url_analyzer_parametrized(
    url: str, expected_type: URLType, expected_id: str | None
) -> None:
    """Test URL analyzer with a variety of URLs and expected outcomes."""
    analyzer = URLAnalyzer()
    analysis = analyzer.analyze(url)

    assert analysis["type"] == expected_type
    assert analysis.get("event_id") == expected_id


def run_tests_for_cli_output() -> None:
    """Run a selection of tests and display the output in the CLI."""
    clicycle.configure(app_name="event-importer-test")
    clicycle.header("URL Analyzer Visual Test")
    clicycle.info("Testing URL type detection and routing")

    analyzer = URLAnalyzer()
    test_urls = [
        "https://ra.co/events/1234567",
        "https://www.ticketmaster.com/event/G5vYZ9v1AUf-G",
        "https://dice.fm/event/q2r5ro-some-event",
        "https://example.com/events/cool-party",
        "https://ra.co/news/123",
        "example.com",
    ]

    results = []
    for url in test_urls:
        analysis = analyzer.analyze(url)
        results.append(
            {
                "URL": url,
                "Type": analysis["type"],
                "Event ID": analysis.get("event_id", "-"),
                "Slug": analysis.get("slug", "-"),
            }
        )

    clicycle.table(results, title="URL Analysis Summary")
    clicycle.success("URL analyzer visual test completed")


if __name__ == "__main__":
    run_tests_for_cli_output()
