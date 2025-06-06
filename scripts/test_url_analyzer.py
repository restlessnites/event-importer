#!/usr/bin/env -S uv run python
"""Test the URL analyzer with various URLs using CLI."""

from app.url_analyzer import URLAnalyzer
from app.cli import get_cli


def test_url_analyzer():
    """Test URL analyzer with various URL types."""
    cli = get_cli()
    analyzer = URLAnalyzer()

    cli.header("URL Analyzer Test", "Testing URL type detection and routing")

    test_urls = [
        # Resident Advisor
        "https://ra.co/events/1234567",
        "https://www.residentadvisor.net/events/9876543",
        "ra.co/events/123",  # Without scheme
        # Ticketmaster
        "https://www.ticketmaster.com/event/123?id=ABC123",
        "https://www.ticketmaster.ca/event/456?id=DEF456",
        # Direct images
        "https://example.com/event-poster.jpg",
        "https://cdn.example.com/images/party.png",
        "https://example.com/image.JPEG",  # Uppercase extension
        # Generic web pages
        "https://example.com/events/cool-party",
        "https://dice.fm/event/xyz",
        "https://www.eventbrite.com/e/123456",
        # Edge cases
        "https://ra.co/news/123",  # RA but not an event
        "https://ticketmaster.com/browse",  # TM but not an event
        "example.com",  # No scheme
    ]

    cli.section("URL Analysis Results")

    # Show all results
    for url in test_urls:
        analysis = analyzer.analyze(url)
        cli.info(f"\n{url}")
        cli.info(f"  Type: {analysis['type']}")
        if analysis.get("event_id"):
            cli.info(f"  Event ID: {analysis['event_id']}")

    cli.success("\nURL analyzer test completed")


if __name__ == "__main__":
    test_url_analyzer()
