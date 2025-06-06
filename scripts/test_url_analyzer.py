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

    # Prepare results for table display
    results = []

    with cli.progress("Analyzing URLs") as progress:
        for i, url in enumerate(test_urls):
            progress.update_progress(
                (i / len(test_urls)) * 100, f"Analyzing {url[:50]}..."
            )

            analysis = analyzer.analyze(url)

            result = {
                "URL": url[:40] + "..." if len(url) > 40 else url,
                "Type": analysis.type.name,
                "Agent": analysis.agent_name,
                "ID": analysis.extracted_id or "-",
            }

            results.append(result)

    cli.section("Analysis Results")
    cli.table(results, title="URL Analysis Summary")

    # Show detailed results for URLs with extracted IDs
    cli.section("Detailed Results")

    for url in test_urls:
        analysis = analyzer.analyze(url)
        if analysis.extracted_id or analysis.query_params:
            cli.info(f"\nURL: {url}")
            details = {
                "Type": analysis.type.name,
                "Agent": analysis.agent_name,
                "Domain": analysis.domain,
                "Path": analysis.path,
                "Is Image": str(analysis.is_image),
            }
            if analysis.extracted_id:
                details["Extracted ID"] = analysis.extracted_id
            if analysis.query_params:
                details["Query Params"] = str(analysis.query_params)

            for key, value in details.items():
                cli.info(f"  {key}: {value}")

    cli.success("\nURL analyzer test completed")


if __name__ == "__main__":
    test_url_analyzer()
