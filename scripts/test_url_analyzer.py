#!/usr/bin/env -S uv run python
"""Test the URL analyzer with various URLs."""

from app.url_analyzer import URLAnalyzer


def test_url_analyzer():
    """Test URL analyzer with various URL types."""
    analyzer = URLAnalyzer()

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

    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"URL: {url}")

        analysis = analyzer.analyze(url)

        print(f"Type: {analysis.type.name}")
        print(f"Agent: {analysis.agent_name}")
        print(f"Domain: {analysis.domain}")
        print(f"Path: {analysis.path}")
        print(f"Is Image: {analysis.is_image}")
        if analysis.extracted_id:
            print(f"Extracted ID: {analysis.extracted_id}")
        if analysis.query_params:
            print(f"Query Params: {analysis.query_params}")


if __name__ == "__main__":
    test_url_analyzer()
