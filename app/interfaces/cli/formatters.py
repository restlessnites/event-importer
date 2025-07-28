"""Complex data formatters for event data display."""

from __future__ import annotations

import html
import json
from typing import Any

from rich.console import Console
from rich.text import Text

from app.interfaces.cli.components import CodeBlock, Message, Spacer
from app.interfaces.cli.theme import Theme
from app.interfaces.cli.utils import (
    format_status,
    format_timestamp,
    format_url_for_display,
    pluralize,
    truncate,
)
from app.schemas import EventData, EventTime, ImportResult, ImportStatus


def format_event_time(time: EventTime | None) -> str:
    """Format time for display."""
    if not time:
        return ""
    if hasattr(time, "start"):
        result = time.start or ""
        if time.end:
            result += f" – {time.end}"
        return result
    return str(time)


class EventCardFormatter:
    """Format event data for display with enhanced image and link support."""

    def __init__(self: EventCardFormatter, console: Console, theme: Theme) -> None:
        self.console = console
        self.theme = theme
        self.message = Message(console, theme)
        self.spacer = Spacer(console, theme)

    def render(self: EventCardFormatter, event_data: dict[str, Any]) -> None:
        """Render event data in a clean format."""
        # Title
        title = event_data.get("title", "Untitled Event")
        self.console.print()
        self.console.print(Text(title, style=self.theme.typography.header_style))
        self.console.print()

        # Key details in a compact format
        self._render_details(event_data)

        # Lineup
        if event_data.get("lineup"):
            self._render_lineup(event_data["lineup"])

        # Descriptions
        self._render_descriptions(event_data)

        # Images (NEW)
        self._render_images(event_data)

        # Additional info
        self._render_additional_info(event_data)

        # Links section (enhanced)
        self._render_links(event_data)

    def _format_time_detail(
        self: EventCardFormatter, event_data: dict[str, Any]
    ) -> str | None:
        """Formats the event time for display in the details section."""
        time = event_data.get("time")
        if not isinstance(time, dict) or not time.get("start"):
            return None

        time_str = time["start"]
        if end_time := time.get("end"):
            end_date = event_data.get("end_date")
            start_date = event_data.get("date")
            if end_date and start_date != end_date:
                time_str += f" – {end_time} (+1)"
            else:
                time_str += f" – {end_time}"
        return time_str

    def _get_event_details(
        self: EventCardFormatter, event_data: dict[str, Any]
    ) -> list[tuple[str, Any]]:
        """Get key event details as a list of tuples."""
        details = []
        if venue := event_data.get("venue"):
            details.append(("Venue", venue))
        if date := event_data.get("date"):
            details.append(("Date", date))
        if time_str := self._format_time_detail(event_data):
            details.append(("Time", time_str))
        if cost := event_data.get("cost"):
            cost_str = "Free" if str(cost) == "0" else str(cost)
            details.append(("Cost", cost_str))
        if minimum_age := event_data.get("minimum_age"):
            details.append(("Age", minimum_age))
        return details

    def _render_details(self: EventCardFormatter, event_data: dict[str, Any]) -> None:
        """Render key event details."""
        details = self._get_event_details(event_data)

        # Render as aligned pairs
        for label, value in details:
            self.console.print(
                f"[{self.theme.typography.label_style}]{label:12}[/] {value}",
            )

        if details:
            self.console.print()

    def _render_lineup(self: EventCardFormatter, lineup: list[str]) -> None:
        """Render artist lineup."""
        self.console.print(
            f"[{self.theme.typography.label_style}]LINEUP[/] ({len(lineup)} artists)",
            style=self.theme.typography.muted_style,
        )

        # Show all artists in a clean list
        for artist in lineup:
            self.console.print(f"{self.theme.icons.artist} {artist}")
        self.console.print()

    def _render_descriptions(
        self: EventCardFormatter,
        event_data: dict[str, Any],
    ) -> None:
        """Render event descriptions."""
        if event_data.get("short_description"):
            self.console.print(
                f"[{self.theme.typography.label_style}]SUMMARY[/]",
                style=self.theme.typography.muted_style,
            )
            self.console.print(event_data["short_description"])
            self.console.print()

        if event_data.get("long_description"):
            desc = event_data["long_description"]
            # Clean up HTML entities
            desc = html.unescape(desc)

            self.console.print(
                f"[{self.theme.typography.label_style}]DESCRIPTION[/]",
                style=self.theme.typography.muted_style,
            )
            # Wrap long descriptions
            self.console.print(desc, width=self.theme.width - 4)
            self.console.print()

    def _render_images(self: EventCardFormatter, event_data: dict[str, Any]) -> None:
        """Render image information (NEW)."""
        images = event_data.get("images")
        image_search = event_data.get("image_search")

        if images or image_search:
            self.console.print(
                f"[{self.theme.typography.label_style}]IMAGES[/]",
                style=self.theme.typography.muted_style,
            )

            # Current image
            if images:
                if images.get("full"):
                    full_url = format_url_for_display(images["full"], "full")
                    self.console.print(f"{self.theme.icons.image} Full: {full_url}")

                if images.get("thumbnail") and images["thumbnail"] != images.get(
                    "full",
                ):
                    thumb_url = format_url_for_display(images["thumbnail"], "full")
                    self.console.print(
                        f"{self.theme.icons.image} Thumbnail: {thumb_url}",
                    )

            # Image search info (if available)
            if image_search:
                selected = image_search.get("selected")
                if selected:
                    score = selected.get("score", 0)
                    source = selected.get("source", "unknown")
                    self.console.print(
                        f"{self.theme.icons.bullet} Quality Score: {score} (from {source})",
                    )

            self.console.print()

    def _render_additional_info(
        self: EventCardFormatter,
        event_data: dict[str, Any],
    ) -> None:
        """Render additional event information."""
        # Genres
        if event_data.get("genres"):
            genres = ", ".join(event_data["genres"])
            self.console.print(
                f"[{self.theme.typography.label_style}]Genres:[/] {genres}",
            )

        # Promoters
        if event_data.get("promoters"):
            promoters = ", ".join(event_data["promoters"])
            self.console.print(
                f"[{self.theme.typography.label_style}]Promoters:[/] {promoters}",
            )

        # Location
        if event_data.get("location"):
            loc = event_data["location"]
            loc_parts = [loc.get("city"), loc.get("state"), loc.get("country")]
            location = ", ".join(filter(None, loc_parts))
            if location:
                self.console.print(
                    f"[{self.theme.typography.label_style}]Location:[/] {location}",
                )

    def _render_links(self: EventCardFormatter, event_data: dict[str, Any]) -> None:
        """Render links section (enhanced)."""
        links = []

        # Ticket URL
        if event_data.get("ticket_url"):
            url = str(event_data["ticket_url"])
            display_url = format_url_for_display(url, self.theme.layout.url_style)
            links.append(("Tickets", display_url))

        # Source URL
        if event_data.get("source_url"):
            url = str(event_data["source_url"])
            display_url = format_url_for_display(url, self.theme.layout.url_style)
            links.append(("Source", display_url))

        # Render links section if we have any
        if links:
            self.console.print()
            self.console.print(
                f"[{self.theme.typography.label_style}]LINKS[/]",
                style=self.theme.typography.muted_style,
            )

            for label, url in links:
                self.console.print(f"{self.theme.icons.url} {label}: {url}")


class ImportResultFormatter:
    """Format import results."""

    def __init__(self: ImportResultFormatter, console: Console, theme: Theme) -> None:
        self.console = console
        self.theme = theme
        self.event_formatter = EventCardFormatter(console, theme)
        self.message = Message(console, theme)
        self.spacer = Spacer(console, theme)

    def render(
        self: ImportResultFormatter,
        result: ImportResult,
        show_raw: bool = False,
    ) -> None:
        """Render import result."""
        # Import status
        self.console.print()
        self.console.print(
            Text("IMPORT RESULT", style=self.theme.typography.section_style),
        )
        self.console.print("─" * 13, style=self.theme.typography.muted_style)
        self.console.print()

        # Check if successful
        if result.status == ImportStatus.SUCCESS and result.event_data:
            self._render_success(result)

            # Event data
            self.console.print()
            self.console.print(
                Text("EVENT DATA", style=self.theme.typography.section_style),
            )
            self.console.print("─" * 10, style=self.theme.typography.muted_style)
            self.event_formatter.render(result.event_data.model_dump())

            # Image search results
            if result.event_data.image_search:
                self._render_image_results(result.event_data.image_search.model_dump())

            # Data quality
            self._render_data_quality(result.event_data)

        else:
            self._render_failure(result)

        # Show raw JSON if requested (useful for debugging)
        if show_raw and result.event_data:
            self.console.print()
            self.console.print(
                Text("RAW EVENT DATA", style=self.theme.typography.section_style),
            )
            self.console.print("─" * 14, style=self.theme.typography.muted_style)
            self.console.print()

            # Use the existing CodeBlock component
            code_block = CodeBlock(self.console, self.theme)
            raw_json = json.dumps(result.event_data.model_dump(), indent=2, default=str)
            code_block.render(raw_json, language="json")

    def _render_success(self: ImportResultFormatter, result: ImportResult) -> None:
        """Render successful import summary."""
        self.message.success(f"Import completed in {result.import_time:.2f}s")
        if result.method_used:
            self.console.print(
                f"[{self.theme.typography.label_style}]Method:[/] {result.method_used.value}",
            )

    def _render_failure(self: ImportResultFormatter, result: ImportResult) -> None:
        """Render failed import summary."""
        self.message.error(f"Import failed: {result.error}")
        if result.method_used:
            self.console.print(
                f"[{self.theme.typography.label_style}]Method attempted:[/] {result.method_used.value}",
            )
        self.console.print(
            f"[{self.theme.typography.label_style}]Duration:[/] {result.import_time:.2f}s",
        )

    def _render_data_quality(
        self: ImportResultFormatter,
        event_data: EventData,
    ) -> None:
        """Render data completeness check."""
        self.console.print()
        self.console.print(
            Text("DATA QUALITY", style=self.theme.typography.section_style),
        )
        self.console.print("─" * 12, style=self.theme.typography.muted_style)
        self.console.print()

        # Check fields
        fields = [
            ("Title", bool(event_data.title), event_data.title),
            ("Venue", bool(event_data.venue), event_data.venue),
            ("Date", bool(event_data.date), event_data.date),
            ("Time", bool(event_data.time), format_event_time(event_data.time)),
            (
                "Lineup",
                bool(event_data.lineup),
                pluralize(len(event_data.lineup or []), "artist"),
            ),
            (
                "Description",
                bool(event_data.long_description),
                "Present" if event_data.long_description else None,
            ),
            (
                "Images",
                bool(event_data.images),
                "Present" if event_data.images else None,
            ),
        ]

        for field, present, value in fields:
            icon = self.theme.icons.success if present else self.theme.icons.error
            style = (
                self.theme.typography.success_style
                if present
                else self.theme.typography.error_style
            )
            display_value = truncate(str(value), 50) if value else "Missing"

            self.console.print(
                f"[{style}]{icon}[/] "
                f"[{self.theme.typography.label_style}]{field:12}[/] "
                f"{display_value}",
            )

    def _format_time(self: ImportResultFormatter, time: EventTime | None) -> str:
        """Format time for display."""
        return format_event_time(time)

    def _render_image_results(
        self: ImportResultFormatter,
        search_data: dict[str, Any],
    ) -> None:
        """Render image search results."""
        if not search_data:
            return

        self.console.print()
        self.console.print(
            Text("IMAGE SEARCH", style=self.theme.typography.section_style),
        )
        self.console.print("─" * 12, style=self.theme.typography.muted_style)
        self.console.print()

        # Original
        if search_data.get("original"):
            self._render_image_candidate("Original", search_data["original"])

        # Candidates summary
        if search_data.get("candidates"):
            count = len(search_data["candidates"])
            self.console.print(
                f"[{self.theme.typography.label_style}]Search Results:[/] {count} images found",
            )

            # Show top 3
            for i, candidate in enumerate(search_data["candidates"][:3], 1):
                self._render_image_candidate(f"Result {i}", candidate, compact=True)

        # Selected
        if search_data.get("selected"):
            self.console.print()
            self.message.success("Selected image:")
            self._render_image_candidate(None, search_data["selected"])

    def _render_image_candidate(
        self: ImportResultFormatter,
        label: str | None,
        candidate: dict[str, Any],
        compact: bool = False,
    ) -> None:
        """Render a single image candidate."""
        score = candidate.get("score", 0)
        score_style = (
            self.theme.typography.success_style
            if score > 200
            else (
                self.theme.typography.warning_style
                if score > 100
                else self.theme.typography.error_style
            )
        )

        if label:
            self.console.print(f"\n[{self.theme.typography.label_style}]{label}[/]")

        details = []
        details.append(f"Score: [{score_style}]{score}[/]")

        if candidate.get("dimensions"):
            details.append(f"Size: {candidate['dimensions']}")

        if candidate.get("source"):
            details.append(f"From: {candidate['source']}")

        self.console.print(f"{self.theme.indent}{' • '.join(details)}")

        # URLs - now unified!
        if not compact and candidate.get("url"):
            url = candidate["url"]
            display_url = format_url_for_display(url, self.theme.layout.url_style)
            self.console.print(f"{self.theme.indent}URL: {display_url}")


class ProgressUpdateFormatter:
    """Format and display progress updates."""

    def __init__(self: ProgressUpdateFormatter, console: Console, theme: Theme) -> None:
        self.console = console
        self.theme = theme
        self._last_progress = 0

    def render(self: ProgressUpdateFormatter, update: dict[str, Any]) -> None:
        """Render a progress update."""
        status = format_status(update.get("status", "unknown"))
        message = update.get("message", "")
        progress = update.get("progress", 0) * 100
        timestamp = format_timestamp(update.get("timestamp"))

        # Store last progress for error messages
        if progress > 0:
            self._last_progress = progress

        # Get appropriate icon and style
        status_lower = status.lower()
        if "success" in status_lower:
            icon = self.theme.icons.success
            style = self.theme.typography.success_style
        elif "fail" in status_lower or "error" in status_lower:
            icon = self.theme.icons.error
            style = self.theme.typography.error_style
        elif "cancel" in status_lower:
            icon = self.theme.icons.warning
            style = self.theme.typography.warning_style
        else:
            icon = self.theme.icons.running
            style = self.theme.typography.info_style

        # Build status line
        parts = []
        if timestamp:
            parts.append(f"[{self.theme.typography.dim_style}][{timestamp}][/]")
        parts.append(f"[{style}]{icon}[/]")
        parts.append(f"[{style}]{status:<10}[/]")
        parts.append(f"[{self.theme.typography.muted_style}]{progress:3.0f}%[/]")
        parts.append(message)

        self.console.print(" ".join(parts))


class ValidationFormatter:
    """Format and display validation results."""

    def __init__(self: ValidationFormatter, console: Console, theme: Theme) -> None:
        """Initialize with console and theme."""
        self.console = console
        self.theme = theme

    def render(self: ValidationFormatter, results: dict[str, Any]) -> None:
        """Render the validation report."""
        if results["errors"]:
            self.console.print("[bold red]Validation Failed[/bold red]")
            for error in results["errors"]:
                self.console.print(f"  [red]✗[/red] {error}")
        else:
            self.console.print("[bold green]Validation Succeeded[/bold green]")

        if results["warnings"]:
            self.console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for warning in results["warnings"]:
                self.console.print(f"  [yellow]⚠[/yellow] {warning}")

        self.console.print("\n[bold]Details:[/bold]")
        for check, result in results["checks"].items():
            if isinstance(result, bool):
                status = "[green]✓[/green]" if result else "[red]✗[/red]"
                self.console.print(f"  {status} {check}")
            else:
                self.console.print(f"  [cyan]ℹ[/cyan] {check}: {result}")
