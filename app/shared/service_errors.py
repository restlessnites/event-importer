"""Shared utilities for formatting service errors for user-friendly display."""

import re
from typing import Any


class ServiceErrorFormatter:
    """Formats service errors into user-friendly messages."""

    # Service descriptions for non-technical users
    SERVICE_DESCRIPTIONS = {
        "GenreService": "genre enhancement",
        "GoogleImageSearch": "image search",
        "ZyteService": "advanced web scraping",
        "OpenAIService": "AI text analysis",
        "ClaudeService": "AI text analysis",
        "ImageService": "image processing",
        "LLMService": "AI processing",
        "TicketmasterAgent": "Ticketmaster API",
        "ResidentAdvisorAgent": "Resident Advisor",
        "DiceAgent": "Dice.fm",
    }

    # Common error patterns and their user-friendly messages
    ERROR_PATTERNS = {
        r"GoogleImageSearch[\s\S]*Request contains an invalid argument": "Google API is not configured correctly",
        r"Config.*has no attribute.*extraction": "configuration error - missing settings",
        r"API key.*not.*found|No API key": "API key is missing",
        r"timeout|timed out": "service took too long to respond",
        r"connection.*refused|network": "could not connect to the service",
        r"rate.*limit": "too many requests - please try again later",
        r"403.*forbidden": "access denied - check API permissions",
        r"404.*not found": "requested resource was not found",
        r"500.*internal.*error": "service is experiencing issues",
        r"SSL|certificate": "secure connection failed",
        r"invalid.*response|parse.*error": "received invalid data from service",
    }

    @classmethod
    def format_failure(cls, service: str, error: str) -> str:
        """Format a single service failure into a user-friendly message."""
        # Get user-friendly service name
        service_name = cls.SERVICE_DESCRIPTIONS.get(
            service, service.replace("Service", "").replace("Agent", "").lower()
        )

        # Try to match error patterns for better messages
        for pattern, friendly_msg in cls.ERROR_PATTERNS.items():
            if re.search(pattern, error, re.IGNORECASE):
                return f"Could not use {service_name}: {friendly_msg}"

        # Generic but still friendly
        return f"Could not use {service_name} (technical error occurred)"

    @classmethod
    def format_failures(cls, failures: list[dict[str, Any]]) -> tuple[list[str], str]:
        """Format multiple service failures.

        Returns:
            tuple of (list of individual messages, summary message)
        """
        if not failures:
            return [], ""

        failure_msgs = []
        seen_messages = set()

        for failure in failures:
            service = failure.get("service", "Unknown service")
            error = failure.get("error", "Unknown error")
            msg = cls.format_failure(service, error)

            # Deduplicate messages
            if msg not in seen_messages:
                failure_msgs.append(msg)
                seen_messages.add(msg)

        # Create summary
        summary = ""
        if failure_msgs:
            if len(failure_msgs) == 1:
                summary = f"Note: {failure_msgs[0]}"
            else:
                summary = (
                    "The event was imported successfully, but some optional enhancements were not available:\n• "
                    + "\n• ".join(failure_msgs)
                )

        return failure_msgs, summary

    @classmethod
    def format_for_cli(cls, failures: list[dict[str, Any]]) -> list[str]:
        """Format failures for CLI display (returns list of messages)."""
        failure_msgs, _ = cls.format_failures(failures)
        return failure_msgs

    @classmethod
    def format_for_api(cls, failures: list[dict[str, Any]]) -> dict[str, Any]:
        """Format failures for API response."""
        failure_msgs, summary = cls.format_failures(failures)
        return (
            {
                "service_failures": failures,
                "service_failure_messages": failure_msgs,
                "service_failure_summary": summary,
            }
            if failures
            else {}
        )

    @classmethod
    def format_for_mcp(cls, result: dict[str, Any]) -> dict[str, Any]:
        """Format failures for MCP response (modifies result in place)."""
        if failures := result.get("service_failures"):
            _, summary = cls.format_failures(failures)
            if summary:
                result["service_failure_summary"] = summary
        return result
