#!/usr/bin/env -S uv run python
"""Test the URL analyzer with various URLs using CLI."""

from app.shared.url_analyzer import URLAnalyzer
from app.interfaces.cli import get_cli


def test_url_analyzer():
    """Test URL analyzer with various URL types."""
    cli = get_cli()
    analyzer = URLAnalyzer()

    cli.header("URL Analyzer Test", "Testing URL type detection and routing")

    # Start capturing any potential errors
    cli.error_capture.start()

    try:
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
                    (i / len(test_urls)) * 100, f"Analyzing URL {i+1}/{len(test_urls)}"
                )

                analysis = analyzer.analyze(url)

                result = {
                    "URL": url if len(url) <= 40 else url[:37] + "...",
                    "Type": analysis["type"],
                    "Event ID": analysis.get("event_id", "-"),
                }

                results.append(result)

        cli.section("Analysis Results")
        cli.table(results, title="URL Analysis Summary")

        # Show detailed results for URLs with extracted IDs
        detailed = []
        for url in test_urls:
            analysis = analyzer.analyze(url)
            if analysis.get("event_id"):
                detailed.append(
                    {
                        "URL": url,
                        "Type": analysis["type"],
                        "Event ID": analysis.get("event_id"),
                    }
                )

        if detailed:
            cli.section("URLs with Extracted IDs")
            for item in detailed:
                cli.info(f"• {item['URL']}")
                cli.info(f"  Type: {item['Type']} | ID: {item['Event ID']}")
                cli.console.print()

        cli.success("URL analyzer test completed")

    except Exception as e:
        cli.error(f"Test failed: {e}")
        import traceback

        cli.code(traceback.format_exc(), "python", "Exception Traceback")
    finally:
        # Stop capturing and show any errors
        cli.error_capture.stop()

        if cli.error_capture.has_errors() or cli.error_capture.has_warnings():
            cli.show_captured_errors("Issues During Test")


if __name__ == "__main__":
    try:
        test_url_analyzer()
    except KeyboardInterrupt:
        cli = get_cli()
        cli.warning("\nTest interrupted by user")
