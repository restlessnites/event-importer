"""Centralized prompt templates for Claude interactions."""

from __future__ import annotations

from typing import Any

from app.schemas import EventData


class EventPrompts:
    """Modular prompt builder for event extraction and generation."""

    # Core extraction rules that apply to all extractions
    BASE_EXTRACTION_RULES = """
EXTRACTION RULES:

- **TIME EXTRACTION**:
   - Look for "Show time", "Event time", "Start time", "Doors at", "Doors open at", or similar phrases
   - If you see both "Doors: 7pm" and "Show: 8pm", use 7pm as the event time
   - Ignore venue opening hours, business hours, or box office hours
   - Only extract actual event performance times
   - Common patterns: "7:00 PM", "19:00", "8pm", "Show at 8:30pm"
   - An end time is optional, but if present, it should be extracted
   - "End time" is not "show time"
   - If you can't find an end time, leave it blank

- **DATE EXTRACTION**:
    - If the year is not present, do not fill it in, provide the date without the year.

- **REMOVE TRAILING "..." FROM ALL FIELDS**:
   - If any text ends with "..." remove those dots completely and make it a complete sentence.

- Extract all available event information:
   - Title, venue, date, time (start/end), lineup, promoters
   - Location details (address, city, state, country, coordinates)
   - Cost, age restrictions, ticket URLs, image URLs
   - At least one genre is required (multiple preferred over single)

- Look for the venue name in the content:
   - Use the most prominent venu found in the content

- Be thorough - extract every piece of information available. Pay attention to the city and venue name, as they are often mentioned in the content."""

    # Rules for generating long descriptions when missing
    LONG_DESCRIPTION_GENERATION = """
- **LONG DESCRIPTION** (only if NO description exists in the source):
   - Generate a comprehensive description using ALL extracted information
   - Include: lineup/artists, venue, date, genres, promoters, location
   - Make it natural and informative, 2-4 sentences
   - Example: "Electronic music showcase featuring DJ Shadow and Cut Chemist at The Fillmore. This special event brings together two legendary turntablists for an evening of experimental hip-hop and breaks. Presented by Goldenvoice, the show features opening sets from local DJs."
   - If a description DOES exist in the source, use it as-is (just clean it up)"""

    # Rules for generating short descriptions when missing
    SHORT_DESCRIPTION_GENERATION = """
- **SHORT DESCRIPTION** (only if NO short description exists in the source):
   - Generate a factual summary under 100 characters
   - NO adjectives, NO marketing language, just facts
   - Format: "[Genre] with [Artist]" or "[Type] featuring [Artists]" or "[Genre] at [Venue]"
   - Good examples:
     * "Electronic music with DJ Shadow"
     * "Jazz quartet at Blue Note"
     * "Rock concert featuring local bands"
     * "Hip-hop showcase with 5 artists"
   - Bad examples (too marketing-y):
     * "Amazing night of electronic music!"
     * "Legendary DJ Shadow performance"
     * "Don't miss this incredible show"
   - If a short description exists in the source, extract it as-is"""

    # Rules for genre enhancement
    GENRE_ENHANCEMENT = """
Review and enhance the event genres.
- Consider:
- - Primary music or event style
- - Sub-genres and related styles
- - Cultural or regional influences
- - Event format or type

Genre Guidelines:
- Use specific but established genre names
- Include both primary and sub-genres when relevant
- For hip-hop/rap events, consider: Alternative Hip-Hop, Conscious Hip-Hop, Gangsta Rap
- For electronic events, consider: House, Techno, Drum & Bass
- For rock events, consider: Alternative Rock, Indie Rock, Progressive Rock
- Avoid overly broad terms like just "Rock" or "Hip-Hop"
- Maximum 4 genres to avoid clutter"""

    @classmethod
    def build_extraction_prompt(
        cls: type[EventPrompts],
        content: str,
        url: str,
        content_type: str = "html",
        context: str | None = None,
        needs_long_description: bool = True,
        needs_short_description: bool = True,
    ) -> str:
        """Build prompt for event extraction from any content type.

        Args:
            content: The content to extract from
            url: Source URL
            content_type: Type of content (html, screenshot, image, text)
            context: Additional context if needed
            needs_long_description: Whether to include long description generation rules
            needs_short_description: Whether to include short description generation rules

        """
        # Content wrappers for different types
        content_wrapper = {
            "html": ("HTML Content:", "```html", "```"),
            "screenshot": ("Looking at this event page screenshot.", "", ""),
            "image": ("Looking at this event flyer/poster.", "", ""),
            "text": ("Content:", "```", "```"),
        }.get(content_type, ("Content:", "```", "```"))

        # Build the prompt
        prompt_parts = [
            f"Extract event information from this {'webpage' if content_type == 'html' else 'event ' + content_type}.",
            f"\\nSource URL: {url}",
        ]

        if context:
            prompt_parts.append(f"Additional Context: {context}")

        prompt_parts.extend(
            [
                f"\\n{content_wrapper[0]}",
                content_wrapper[1],
                content if content_type not in ["screenshot", "image"] else "",
                content_wrapper[2],
                f"\\n{cls.BASE_EXTRACTION_RULES}",
            ],
        )

        # Add description generation rules only if needed
        if needs_long_description:
            prompt_parts.append(cls.LONG_DESCRIPTION_GENERATION)

        if needs_short_description:
            prompt_parts.append(cls.SHORT_DESCRIPTION_GENERATION)

        return "\\n".join(prompt_parts)

    @staticmethod
    def _build_event_context(event_data: dict[str, Any]) -> str:
        """Builds the event context string from event data."""
        context_parts = [f"Event: {event_data.get('title', 'Unknown Event')}"]
        field_map = {
            "venue": "Venue",
            "date": "Date",
            "cost": "Cost",
            "minimum_age": "Age",
        }
        for field, label in field_map.items():
            if value := event_data.get(field):
                context_parts.append(f"{label}: {value}")

        for list_field in ["lineup", "genres", "promoters"]:
            if items := event_data.get(list_field):
                context_parts.append(f"{list_field.capitalize()}: {', '.join(items)}")

        if (
            (time := event_data.get("time"))
            and isinstance(time, dict)
            and (start := time.get("start"))
        ):
            context_parts.append(f"Time: {start}")

        if loc := event_data.get("location"):
            loc_str = ", ".join(
                filter(
                    None,
                    [
                        loc.get("address"),
                        loc.get("city"),
                        loc.get("state"),
                        loc.get("country"),
                    ],
                ),
            )
            if loc_str:
                context_parts.append(f"Location: {loc_str}")

        return "\\n".join(context_parts)

    @classmethod
    def build_description_generation_prompt(
        cls: type[EventPrompts],
        event_data: EventData,
        needs_long: bool = True,
        needs_short: bool = True,
        supplementary_context: str | None = None,
    ) -> str:
        """Build prompt for generating missing descriptions.

        Args:
            event_data: The event data to generate descriptions for
            needs_long: Whether to include long description generation rules
            needs_short: Whether to include short description generation rules
            supplementary_context: Additional context to help generate descriptions
        """
        context = cls._build_event_context(event_data.model_dump())

        prompt_parts = [
            "Generate missing descriptions for this event.",
            f"\\n{context}",
        ]

        if supplementary_context:
            prompt_parts.append(f"\\nAdditional Context: {supplementary_context}")

        prompt_parts.append("\\nRequirements:")

        # Add description generation rules based on what's needed
        if needs_long:
            prompt_parts.append(cls.LONG_DESCRIPTION_GENERATION)
        if needs_short:
            prompt_parts.append(cls.SHORT_DESCRIPTION_GENERATION)

        return "\\n".join(prompt_parts)

    @classmethod
    def build_genre_enhancement_prompt(
        cls: type[EventPrompts],
        event_data: dict[str, Any],
    ) -> str:
        """Build prompt for genre enhancement."""
        return f"""
        Enhance the genres for the following event:

        Title: {event_data.get("title", "N/A")}
        Current Genres: {", ".join(event_data.get("genres", []) or ["N/A"])}
        Venue: {event_data.get("venue", "N/A")}
        Lineup: {", ".join(event_data.get("lineup", []) or ["N/A"])}

        {cls.GENRE_ENHANCEMENT}
        """


class GenrePrompts:
    """Prompts for genre identification and enhancement."""

    @classmethod
    def build_artist_verification_prompt(
        cls: type[GenrePrompts],
        artist_name: str,
        search_results: str,
        event_context: dict,
    ) -> str:
        """Build prompt to verify artist identity and extract genres."""
        context_info = []
        if event_context.get("venue"):
            context_info.append(f"Venue: {event_context['venue']}")
        if event_context.get("date"):
            context_info.append(f"Date: {event_context['date']}")
        if event_context.get("title"):
            context_info.append(f"Event: {event_context['title']}")

        other_artists = event_context.get("lineup", [])
        if len(other_artists) > 1:
            others = [a for a in other_artists if a != artist_name]
            if others:
                context_info.append(f"Other artists: {', '.join(others[:3])}")

        context_text = (
            "\n".join(context_info) if context_info else "No additional context"
        )

        return f"""Analyze these search results to identify if this is the correct artist and extract their music genres.

ARTIST TO VERIFY: "{artist_name}"

EVENT CONTEXT:
{context_text}

SEARCH RESULTS:
{search_results}

TASK:
1. Determine if the search results are about the correct artist (use event context to help)
2. If correct, extract the artist's PRIMARY music genres (2-4 genres max)
3. Use standard genre names only (Rock, Electronic, Hip Hop, Jazz, etc.)

VERIFICATION GUIDELINES:
- Consider if the artist matches the event type/venue
- Look for biographical details that align with context
- Be conservative - if unsure, return empty list

GENRE GUIDELINES:
- Return established genre names, not descriptive phrases
- Prefer broader categories over micro-genres
- Examples: "Rock" not "Post-Hardcore Math Rock"
- Maximum 4 genres to avoid clutter"""

    @classmethod
    def build_genre_extraction_prompt(
        cls: type[GenrePrompts],
        search_query: str,
        search_results: str,
        event_context: dict,
    ) -> str:
        """Build prompt to extract genres from search results when query is genre-related."""
        return f"""Based on the search results below, identify the most relevant music genres.

SEARCH QUERY: "{search_query}"
EVENT: {event_context.get('title', 'Unknown')}
VENUE: {event_context.get('venue', 'Unknown')}

SEARCH RESULTS:
{search_results}

Extract 1-4 relevant music genres from the search results. Return ONLY a JSON array of genre names.
Examples: ["Indie Rock"], ["Electronic", "House"], ["Jazz", "Fusion"]

If the search results don't contain clear genre information, return an empty array: []"""
