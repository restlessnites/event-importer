"""Centralized prompt templates for Claude interactions."""

from typing import Optional, Dict, Any


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

- **REMOVE TRAILING "..." FROM ALL FIELDS**:
   - If any text ends with "..." remove those dots completely and make it a complete sentence.

- Extract all available event information:
   - Title, venue, date, time (start/end), lineup, promoters
   - Location details (address, city, state, country, coordinates)
   - Cost, age restrictions, ticket URLs, image URLs
   - Genres (multiple preferred over single)

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

    @classmethod
    def build_extraction_prompt(
        cls,
        content: str,
        url: str,
        content_type: str = "html",
        context: Optional[str] = None,
        needs_long_description: bool = True,
        needs_short_description: bool = True,
    ) -> str:
        """
        Build prompt for event extraction from any content type.

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
            f"\nSource URL: {url}",
        ]

        if context:
            prompt_parts.append(f"Additional Context: {context}")

        prompt_parts.extend(
            [
                f"\n{content_wrapper[0]}",
                content_wrapper[1],
                content if content_type not in ["screenshot", "image"] else "",
                content_wrapper[2],
                f"\n{cls.BASE_EXTRACTION_RULES}",
            ]
        )

        # Add description generation rules only if needed
        if needs_long_description:
            prompt_parts.append(cls.LONG_DESCRIPTION_GENERATION)

        if needs_short_description:
            prompt_parts.append(cls.SHORT_DESCRIPTION_GENERATION)

        return "\n".join(prompt_parts)

    @classmethod
    def build_description_only_prompt(
        cls,
        event_data: Dict[str, Any],
        needs_long: bool = False,
        needs_short: bool = False,
    ) -> str:
        """
        Build prompt for ONLY generating missing descriptions.
        Used when we already have event data but need to fill in descriptions.
        """
        # Build context from event data
        context_parts = [f"Event: {event_data.get('title', 'Unknown Event')}"]

        if event_data.get("venue"):
            context_parts.append(f"Venue: {event_data['venue']}")

        if event_data.get("date"):
            context_parts.append(f"Date: {event_data['date']}")

        if event_data.get("time"):
            time = event_data["time"]
            if isinstance(time, dict) and time.get("start"):
                context_parts.append(f"Time: {time['start']}")

        if event_data.get("lineup"):
            context_parts.append(f"Artists: {', '.join(event_data['lineup'])}")

        if event_data.get("genres"):
            context_parts.append(f"Genres: {', '.join(event_data['genres'])}")

        if event_data.get("promoters"):
            context_parts.append(f"Promoters: {', '.join(event_data['promoters'])}")

        if event_data.get("location"):
            loc = event_data["location"]
            loc_str = ", ".join(
                filter(
                    None,
                    [
                        loc.get("address"),
                        loc.get("city"),
                        loc.get("state"),
                        loc.get("country"),
                    ],
                )
            )
            if loc_str:
                context_parts.append(f"Location: {loc_str}")

        if event_data.get("cost"):
            context_parts.append(f"Cost: {event_data['cost']}")

        if event_data.get("minimum_age"):
            context_parts.append(f"Age: {event_data['minimum_age']}")

        # Build the prompt
        prompt_parts = [
            "Generate ONLY the missing descriptions for this event based on the available information:",
            "\n" + "\n".join(context_parts),
            "\nCurrent descriptions:",
        ]

        if event_data.get("long_description"):
            prompt_parts.append(f"- long_description: Already exists (keep as-is)")
        else:
            prompt_parts.append(f"- long_description: MISSING - please generate")

        if event_data.get("short_description"):
            prompt_parts.append(f"- short_description: Already exists (keep as-is)")
        else:
            prompt_parts.append(f"- short_description: MISSING - please generate")

        prompt_parts.append("\nRequirements:")

        if needs_long and not event_data.get("long_description"):
            prompt_parts.append(
                """
**LONG DESCRIPTION**:
- Create a natural, engaging description incorporating all available information
- Should be 2-4 sentences, informative and complete
- Include lineup, venue, date, genres, and any unique aspects"""
            )

        if needs_short and not event_data.get("short_description"):
            prompt_parts.append(
                """
**SHORT DESCRIPTION**:
- Must be under 100 characters
- Factual only - NO adjectives or marketing language
- Format: "[Genre] with [Artist]" or similar
- Examples: "Electronic music with DJ Shadow", "Jazz quartet at Blue Note" """
            )

        return "\n".join(prompt_parts)
