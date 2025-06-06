"""Complex data formatters for event data display."""

from typing import Dict, Any, Optional, List
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
from rich import box

from app.cli.theme import Theme
from app.cli.styles import format_timestamp, truncate, pluralize
from app.cli.components import DataTable, Message


class EventCardFormatter:
    """Format event data for display."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme
        self.message = Message(console, theme)

    def render(self, event_data: Dict[str, Any]) -> None:
        """Render event data in a clean format."""
        # Title
        title = event_data.get("title", "Untitled Event")
        self.console.print()
        self.console.print(Text(title, style=self.theme.colors.style("header")))
        self.console.print()

        # Key details in a compact format
        self._render_details(event_data)

        # Lineup
        if event_data.get("lineup"):
            self._render_lineup(event_data["lineup"])

        # Descriptions
        self._render_descriptions(event_data)

        # Additional info
        self._render_additional_info(event_data)

    def _render_details(self, event_data: Dict[str, Any]) -> None:
        """Render key event details."""
        details = []

        # Venue & Date on same line
        if event_data.get("venue"):
            details.append(("Venue", event_data["venue"]))
        if event_data.get("date"):
            details.append(("Date", event_data["date"]))

        # Time
        if event_data.get("time"):
            time = event_data["time"]
            if isinstance(time, dict) and time.get("start"):
                time_str = time["start"]
                if time.get("end"):
                    time_str += f" – {time['end']}"
                details.append(("Time", time_str))

        # Cost & Age
        if event_data.get("cost"):
            details.append(("Cost", event_data["cost"]))
        if event_data.get("minimum_age"):
            details.append(("Age", event_data["minimum_age"]))

        # Render as aligned pairs
        for label, value in details:
            self.console.print(
                f"[{self.theme.colors.style('label')}]{label:12}[/] {value}"
            )

        if details:
            self.console.print()

    def _render_lineup(self, lineup: List[str]) -> None:
        """Render artist lineup."""
        self.console.print(
            f"[{self.theme.colors.style('label')}]LINEUP[/] ({len(lineup)} artists)",
            style=self.theme.colors.text_muted,
        )

        # Show all artists in a clean list
        for artist in lineup:
            self.console.print(f"{self.theme.icons.bullet} {artist}")
        self.console.print()

    def _render_descriptions(self, event_data: Dict[str, Any]) -> None:
        """Render event descriptions."""
        if event_data.get("short_description"):
            self.console.print(
                f"[{self.theme.colors.style('label')}]SUMMARY[/]",
                style=self.theme.colors.text_muted,
            )
            self.console.print(event_data["short_description"])
            self.console.print()

        if event_data.get("long_description"):
            desc = event_data["long_description"]
            self.console.print(
                f"[{self.theme.colors.style('label')}]DESCRIPTION[/]",
                style=self.theme.colors.text_muted,
            )
            # Wrap long descriptions
            self.console.print(desc, width=self.theme.width - 4)
            self.console.print()

    def _render_additional_info(self, event_data: Dict[str, Any]) -> None:
        """Render additional event information."""
        # Genres
        if event_data.get("genres"):
            genres = ", ".join(event_data["genres"])
            self.console.print(
                f"[{self.theme.colors.style('label')}]Genres:[/] {genres}"
            )

        # Promoters
        if event_data.get("promoters"):
            promoters = ", ".join(event_data["promoters"])
            self.console.print(
                f"[{self.theme.colors.style('label')}]Promoters:[/] {promoters}"
            )

        # Location
        if event_data.get("location"):
            loc = event_data["location"]
            loc_parts = [loc.get("city"), loc.get("state"), loc.get("country")]
            location = ", ".join(filter(None, loc_parts))
            if location:
                self.console.print(
                    f"[{self.theme.colors.style('label')}]Location:[/] {location}"
                )

        # URLs (truncated for display)
        if event_data.get("ticket_url"):
            url = str(event_data["ticket_url"])
            self.console.print(
                f"[{self.theme.colors.style('label')}]Tickets:[/] {truncate(url, 60)}"
            )


class ImportResultFormatter:
    """Format import results."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme
        self.event_formatter = EventCardFormatter(console, theme)
        self.message = Message(console, theme)

    def render(self, result: Any, show_raw: bool = False) -> None:
        """Render import result."""
        # Import status
        self.console.print()
        self.console.print(
            Text("IMPORT RESULT", style=self.theme.colors.style("section"))
        )
        self.console.print("─" * 13, style=self.theme.colors.text_muted)
        self.console.print()

        # Check if successful
        from app.schemas import ImportStatus

        if result.status == ImportStatus.SUCCESS and result.event_data:
            self._render_success(result)

            # Event data
            self.console.print()
            self.console.print(
                Text("EVENT DATA", style=self.theme.colors.style("section"))
            )
            self.console.print("─" * 10, style=self.theme.colors.text_muted)
            self.event_formatter.render(result.event_data.model_dump())

            # Image search results
            if result.event_data.image_search:
                self._render_image_results(result.event_data.image_search.model_dump())

            # Data quality
            self._render_data_quality(result.event_data)

        else:
            self._render_failure(result)

    def _render_success(self, result: Any) -> None:
        """Render successful import summary."""
        self.message.success(f"Import completed in {result.import_time:.2f}s")
        self.console.print(
            f"[{self.theme.colors.style('label')}]Method:[/] {result.method_used.value}"
        )

    def _render_failure(self, result: Any) -> None:
        """Render failed import summary."""
        self.message.error(f"Import failed: {result.error}")
        if result.method_used:
            self.console.print(
                f"[{self.theme.colors.style('label')}]Method attempted:[/] {result.method_used.value}"
            )
        self.console.print(
            f"[{self.theme.colors.style('label')}]Duration:[/] {result.import_time:.2f}s"
        )

    def _render_data_quality(self, event_data: Any) -> None:
        """Render data completeness check."""
        self.console.print()
        self.console.print(
            Text("DATA QUALITY", style=self.theme.colors.style("section"))
        )
        self.console.print("─" * 12, style=self.theme.colors.text_muted)
        self.console.print()

        # Check fields
        fields = [
            ("Title", bool(event_data.title), event_data.title),
            ("Venue", bool(event_data.venue), event_data.venue),
            ("Date", bool(event_data.date), event_data.date),
            ("Time", bool(event_data.time), self._format_time(event_data.time)),
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
            color = "success" if present else "error"
            display_value = truncate(str(value), 50) if value else "Missing"

            self.console.print(
                f"[{self.theme.colors.style(color)}]{icon}[/] "
                f"[{self.theme.colors.style('label')}]{field:12}[/] "
                f"{display_value}"
            )

    def _format_time(self, time: Any) -> str:
        """Format time for display."""
        if not time:
            return ""
        if hasattr(time, "start"):
            result = time.start or ""
            if time.end:
                result += f" – {time.end}"
            return result
        return str(time)

    def _render_image_results(self, search_data: Dict[str, Any]) -> None:
        """Render image search results."""
        if not search_data:
            return

        self.console.print()
        self.console.print(
            Text("IMAGE SEARCH", style=self.theme.colors.style("section"))
        )
        self.console.print("─" * 12, style=self.theme.colors.text_muted)
        self.console.print()

        # Original
        if search_data.get("original"):
            self._render_image_candidate("Original", search_data["original"])

        # Candidates summary
        if search_data.get("candidates"):
            count = len(search_data["candidates"])
            self.console.print(
                f"[{self.theme.colors.style('label')}]Search Results:[/] {count} images found"
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
        self, label: Optional[str], candidate: Dict[str, Any], compact: bool = False
    ) -> None:
        """Render a single image candidate."""
        score = candidate.get("score", 0)
        score_color = (
            "success" if score > 200 else "warning" if score > 100 else "error"
        )

        if label:
            self.console.print(f"\n[{self.theme.colors.style('label')}]{label}[/]")

        details = []
        details.append(f"Score: [{self.theme.colors.style(score_color)}]{score}[/]")

        if candidate.get("dimensions"):
            details.append(f"Size: {candidate['dimensions']}")

        if candidate.get("source"):
            details.append(f"From: {candidate['source']}")

        self.console.print(f"{self.theme.indent}{' • '.join(details)}")

        if not compact and candidate.get("url"):
            self.console.print(
                f"{self.theme.indent}URL: {truncate(candidate['url'], 70)}"
            )


class ProgressUpdateFormatter:
    """Format progress updates."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme
        self.status_line = StatusLine(console, theme)

    def render(self, update: Dict[str, Any]) -> None:
        """Render a progress update."""
        status = update.get("status", "unknown")
        message = update.get("message", "")
        progress = update.get("progress", 0) * 100
        timestamp = format_timestamp(update.get("timestamp"))

        # Clean up status
        status = self.theme.format_status(status)

        # Get icon and style based on status
        status_lower = status.lower()
        if "success" in status_lower:
            icon = self.theme.icons.success
            style = "success"
        elif "fail" in status_lower or "error" in status_lower:
            icon = self.theme.icons.error
            style = "error"
        elif "cancel" in status_lower:
            icon = self.theme.icons.warning
            style = "warning"
        else:
            icon = self.theme.icons.running
            style = "running"

        self.status_line.render(
            icon=icon,
            status=status,
            message=message,
            timestamp=timestamp,
            progress=progress,
            style=style,
        )


class StatusLine:
    """Format a single status line."""

    def __init__(self, console: Console, theme: Theme):
        self.console = console
        self.theme = theme

    def render(self, **kwargs) -> None:
        """Render status line with proper formatting."""
        icon = kwargs.get("icon", self.theme.icons.info)
        status = kwargs.get("status", "")
        message = kwargs.get("message", "")
        timestamp = kwargs.get("timestamp")
        progress = kwargs.get("progress")
        style = kwargs.get("style", "default")

        parts = []

        # Timestamp in brackets
        if timestamp:
            parts.append(f"[{self.theme.colors.text_dim}][{timestamp}][/]")

        # Icon
        parts.append(f"[{self.theme.colors.style(style)}]{icon}[/]")

        # Status (fixed width for alignment)
        if status:
            parts.append(f"[{self.theme.colors.style(style)}]{status:<10}[/]")

        # Progress percentage
        if progress is not None:
            parts.append(f"[{self.theme.colors.text_muted}]{progress:3.0f}%[/]")

        # Message
        parts.append(message)

        self.console.print(" ".join(parts))
