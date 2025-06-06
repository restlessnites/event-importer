"""CLI interface components for test scripts and debugging."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box
from rich.columns import Columns
from rich.tree import Tree
from rich.text import Text


class CLI:
    """CLI interface for event importer using Rich."""

    def __init__(self, width: int = 120):
        """Initialize CLI with Rich console."""
        self.width = width
        self.console = Console(width=width)
        self._progress = None
        self._task_id = None

    def _safe_str(self, value: Any) -> str:
        """Convert any value to string safely."""
        if hasattr(value, "__str__"):
            return str(value)
        return repr(value)

    def header(self, title: str, subtitle: Optional[str] = None) -> None:
        """Display a prominent header."""
        header_text = Text(title, style="bold white")
        if subtitle:
            header_text.append(f"\n{subtitle}", style="dim")
        self.console.print("\n")
        self.console.print(Panel(header_text, box=box.DOUBLE_EDGE, style="cyan"))
        self.console.print()

    def section(self, title: str) -> None:
        """Display a section header."""
        self.console.print()
        self.console.rule(f"[bold blue]{title}[/bold blue]", style="blue")
        self.console.print()

    def info(self, message: str) -> None:
        """Display an info message."""
        self.console.print(f"[dim]ℹ[/dim]  {message}")

    def success(self, message: str) -> None:
        """Display a success message."""
        self.console.print(f"[bold green]✓[/bold green]  {message}")

    def error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(f"[bold red]✗[/bold red]  [red]{message}[/red]")

    def warning(self, message: str) -> None:
        """Display a warning message."""
        self.console.print(f"[bold yellow]⚠[/bold yellow]  [yellow]{message}[/yellow]")

    @contextmanager
    def progress(self, description: str = "Processing"):
        """Context manager for progress tracking."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
            transient=True,
        ) as progress:
            self._progress = progress
            self._task_id = progress.add_task(description, total=100)
            yield self
            self._progress = None
            self._task_id = None

    def update_progress(self, percent: float, message: Optional[str] = None) -> None:
        """Update progress bar."""
        if self._progress and self._task_id is not None:
            if message:
                self._progress.update(self._task_id, description=message)
            self._progress.update(self._task_id, completed=percent)

    @contextmanager
    def spinner(self, message: str):
        """Show a spinner for indeterminate progress."""
        with self.console.status(message, spinner="dots"):
            yield

    def table(self, data: List[Dict[str, Any]], title: Optional[str] = None) -> None:
        """Display data in a table."""
        if not data:
            return

        table = Table(
            title=title, box=box.ROUNDED, show_header=True, title_style="bold"
        )

        # Add columns
        for key in data[0].keys():
            table.add_column(key, style="cyan")

        # Add rows
        for row in data:
            table.add_row(*[self._safe_str(v) for v in row.values()])

        self.console.print(table)

    def json(self, data: dict, title: Optional[str] = None) -> None:
        """Display JSON data with syntax highlighting."""
        import json

        if title:
            self.console.print(f"\n[bold]{title}[/bold]\n")

        json_str = json.dumps(data, indent=2, default=str)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
        self.console.print(syntax)

    def code(
        self, code: str, language: str = "python", title: Optional[str] = None
    ) -> None:
        """Display code with syntax highlighting."""
        if title:
            self.console.print(f"\n[bold]{title}[/bold]\n")

        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self.console.print(syntax)

    def event_card(self, event_data: dict) -> None:
        """Display event data in a nice card format."""
        # Title
        title = event_data.get("title", "Untitled Event")
        self.console.print(
            Panel(Text(title, style="bold white"), box=box.ROUNDED, style="cyan")
        )

        # Basic info in columns
        left_col = []
        right_col = []

        # Left column
        if event_data.get("venue"):
            left_col.append(f"[bold]Venue:[/bold] {event_data['venue']}")
        if event_data.get("date"):
            left_col.append(f"[bold]Date:[/bold] {event_data['date']}")
        if event_data.get("time"):
            time = event_data["time"]
            if isinstance(time, dict):
                time_str = f"{time.get('start', 'TBD')}"
                if time.get("end"):
                    time_str += f" - {time['end']}"
                left_col.append(f"[bold]Time:[/bold] {time_str}")
        if event_data.get("minimum_age"):
            left_col.append(f"[bold]Age:[/bold] {event_data['minimum_age']}")

        # Right column
        if event_data.get("cost"):
            right_col.append(f"[bold]Cost:[/bold] {event_data['cost']}")
        if event_data.get("promoters"):
            right_col.append(
                f"[bold]Promoters:[/bold] {', '.join(event_data['promoters'])}"
            )

        # Display columns
        if left_col or right_col:
            self.console.print(
                Columns(["\n".join(left_col), "\n".join(right_col)], padding=(1, 4))
            )
            self.console.print()

        # Lineup - show all artists
        if event_data.get("lineup"):
            lineup = event_data["lineup"]
            self.console.print(f"[bold]Lineup ({len(lineup)}):[/bold]")
            for artist in lineup:
                self.console.print(f"  • {artist}")
            self.console.print()

        # Genres
        if event_data.get("genres"):
            self.console.print(
                f"[bold]Genres:[/bold] {', '.join(event_data['genres'])}"
            )
            self.console.print()

        # Location
        if event_data.get("location"):
            loc = event_data["location"]
            loc_parts = []
            if loc.get("city"):
                loc_parts.append(loc["city"])
            if loc.get("state"):
                loc_parts.append(loc["state"])
            if loc.get("country"):
                loc_parts.append(loc["country"])
            if loc_parts:
                self.console.print(f"[bold]Location:[/bold] {', '.join(loc_parts)}")
                self.console.print()

        # Descriptions - show full text
        if event_data.get("short_description"):
            desc_len = len(event_data["short_description"])
            self.console.print(f"[bold]Short description ({desc_len} chars):[/bold]")
            self.console.print(event_data["short_description"], style="italic")
            self.console.print()

        if event_data.get("long_description"):
            desc = event_data["long_description"]
            desc_len = len(desc)
            self.console.print(f"[bold]Full description ({desc_len} chars):[/bold]")
            self.console.print(desc, style="dim", width=self.width - 4, overflow="fold")
            self.console.print()

        # URLs - show full URLs
        if event_data.get("ticket_url"):
            self.console.print(f"[bold]Ticket URL:[/bold]")
            self.console.print(self._safe_str(event_data["ticket_url"]))
            self.console.print()

        if event_data.get("source_url"):
            self.console.print(f"[bold]Source URL:[/bold]")
            self.console.print(self._safe_str(event_data["source_url"]))
            self.console.print()

        # Images - show full URLs
        if event_data.get("images"):
            imgs = event_data["images"]
            self.console.print(f"[bold]Images:[/bold]")
            if imgs.get("full"):
                self.console.print(f"  [dim]full:[/dim] {self._safe_str(imgs['full'])}")
            if imgs.get("thumbnail"):
                self.console.print(
                    f"  [dim]thumbnail:[/dim] {self._safe_str(imgs['thumbnail'])}"
                )
            self.console.print()

        # Metadata
        if event_data.get("imported_at"):
            self.console.print(f"[dim]Imported at: {event_data['imported_at']}[/dim]")
            self.console.print()

    def progress_update(self, update: dict) -> None:
        """Display a progress update from the import system."""
        status = update.get("status", "unknown")
        message = update.get("message", "")
        progress = update.get("progress", 0) * 100

        # Handle timestamp - could be string or datetime
        timestamp_val = update.get("timestamp")
        if isinstance(timestamp_val, str):
            timestamp = datetime.fromisoformat(timestamp_val).strftime("%H:%M:%S")
        elif hasattr(timestamp_val, "strftime"):
            timestamp = timestamp_val.strftime("%H:%M:%S")
        else:
            timestamp = "??:??:??"

        # Status styling
        status_styles = {
            "RUNNING": ("cyan", "⟳"),
            "SUCCESS": ("green", "✓"),
            "FAILED": ("red", "✗"),
            "PENDING": ("yellow", "○"),
            "CANCELLED": ("dim", "⊘"),
        }

        style, symbol = status_styles.get(status, ("white", "?"))

        # Format progress message
        self.console.print(
            f"[dim]{timestamp}[/dim] [{style}]{symbol} {status:8} {progress:3.0f}%[/{style}] {message}"
        )

    def import_result(self, result, show_raw: bool = False) -> None:
        """Display import result with all details."""
        from app.schemas import ImportStatus

        self.section("Import Summary")

        if result.status == ImportStatus.SUCCESS and result.event_data:
            self.success(f"Import successful!")
            self.info(f"Method: {result.method_used.value}")
            self.info(f"Duration: {result.import_time:.2f}s")
            self.console.print()

            # Show the full event data
            self.section("Event Data")
            self.event_card(result.event_data.model_dump())

            # Show image search results if available
            if result.event_data.image_search:
                self.image_search_results(result.event_data.image_search.model_dump())

            # Data completeness check
            self.data_quality_check(result.event_data)

            # Show raw data if requested
            if show_raw and result.raw_data:
                self.section("Raw Extracted Data")
                self.raw_data(result.raw_data)

        else:
            self.error(f"Import failed: {result.error}")
            if result.method_used:
                self.info(f"Method attempted: {result.method_used.value}")
            self.info(f"Duration: {result.import_time:.2f}s")

    def data_quality_check(self, event_data) -> None:
        """Display data quality/completeness check."""
        self.section("Data Quality")

        checks = []

        # Required fields
        checks.append(
            {
                "Field": "Title",
                "Status": "✓" if event_data.title else "✗",
                "Value": event_data.title or "Missing",
            }
        )
        checks.append(
            {
                "Field": "Venue",
                "Status": "✓" if event_data.venue else "✗",
                "Value": event_data.venue or "Missing",
            }
        )
        checks.append(
            {
                "Field": "Date",
                "Status": "✓" if event_data.date else "✗",
                "Value": event_data.date or "Missing",
            }
        )

        # Optional but important fields
        time_val = (
            f"{event_data.time.start} - {event_data.time.end}"
            if event_data.time and event_data.time.start
            else "Missing"
        )
        checks.append(
            {
                "Field": "Time",
                "Status": "✓" if event_data.time else "✗",
                "Value": time_val,
            }
        )

        lineup_val = (
            f"{len(event_data.lineup)} artists" if event_data.lineup else "Missing"
        )
        checks.append(
            {
                "Field": "Lineup",
                "Status": "✓" if event_data.lineup else "✗",
                "Value": lineup_val,
            }
        )

        desc_val = "Present" if event_data.long_description else "Missing"
        checks.append(
            {
                "Field": "Description",
                "Status": "✓" if event_data.long_description else "✗",
                "Value": desc_val,
            }
        )

        img_val = "Present" if event_data.images else "Missing"
        checks.append(
            {
                "Field": "Images",
                "Status": "✓" if event_data.images else "✗",
                "Value": img_val,
            }
        )

        self.table(checks, title="Field Completeness")
        self.console.print()

    def raw_data(self, data: dict, title: str = "Raw Data") -> None:
        """Display raw data in a tree structure."""
        tree = Tree(f"[bold]{title}[/bold]")

        def add_to_tree(parent, key, value):
            """Recursively add data to tree."""
            if isinstance(value, dict):
                branch = parent.add(f"[bold cyan]{key}[/bold cyan]")
                for k, v in value.items():
                    add_to_tree(branch, k, v)
            elif isinstance(value, list):
                branch = parent.add(
                    f"[bold cyan]{key}[/bold cyan] [{len(value)} items]"
                )
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        item_branch = branch.add(f"[{i}]")
                        for k, v in item.items():
                            add_to_tree(item_branch, k, v)
                    else:
                        branch.add(f"[{i}] {self._safe_str(item)}")
            else:
                # Format the value
                if value is None:
                    formatted = "[dim]null[/dim]"
                elif isinstance(value, bool):
                    formatted = f"[yellow]{str(value).lower()}[/yellow]"
                elif isinstance(value, (int, float)):
                    formatted = f"[magenta]{value}[/magenta]"
                else:
                    formatted = f"[green]{self._safe_str(value)}[/green]"
                parent.add(f"[bold]{key}:[/bold] {formatted}")

        for key, value in data.items():
            add_to_tree(tree, key, value)

        self.console.print(tree)
        self.console.print()

    def image_search_results(self, search_data: dict) -> None:
        """Display image search results in a nice format."""
        if not search_data:
            return

        self.section("Image Enhancement Results")

        # Original image
        if search_data.get("original"):
            orig = search_data["original"]
            color = (
                "green"
                if orig["score"] > 100
                else "yellow" if orig["score"] > 0 else "red"
            )

            self.console.print(f"[bold]Original image:[/bold]")
            self.console.print(f"  Score: [{color}]{orig['score']}[/{color}]")
            if orig.get("dimensions"):
                self.console.print(f"  Dimensions: {orig['dimensions']}")
            if orig.get("reason"):
                self.console.print(f"  Reason: [red]{orig['reason']}[/red]")
            self.console.print(f"  URL: {orig['url']}")
            self.console.print()

        # Search results summary
        if search_data.get("candidates"):
            self.console.print(
                f"[bold]Found {len(search_data['candidates'])} candidates:[/bold]"
            )

            # Show all candidates
            for i, cand in enumerate(search_data["candidates"], 1):
                score = cand.get("score", 0)
                color = "green" if score > 200 else "yellow" if score > 100 else "red"

                self.console.print(f"\n[bold]Candidate {i}:[/bold]")
                self.console.print(f"  Score: [{color}]{score}[/{color}]")
                self.console.print(f"  Source: {cand.get('source', 'unknown')}")
                if cand.get("dimensions"):
                    self.console.print(f"  Dimensions: {cand['dimensions']}")
                self.console.print(f"  URL: {cand['url']}")

        # Selected image
        if search_data.get("selected"):
            sel = search_data["selected"]
            self.console.print("\n[bold green]✓ Selected image:[/bold green]")
            self.console.print(f"  Score: [green]{sel['score']}[/green]")
            self.console.print(f"  Source: {sel.get('source', 'unknown')}")
            self.console.print(f"  URL: {sel['url']}")

        self.console.print()

    def rule(self, title: Optional[str] = None, style: str = "dim") -> None:
        """Draw a horizontal rule."""
        self.console.rule(title or "", style=style)

    def clear(self) -> None:
        """Clear the terminal."""
        self.console.clear()


# Global CLI instance
_cli: Optional[CLI] = None


def get_cli() -> CLI:
    """Get the global CLI instance."""
    global _cli
    if _cli is None:
        _cli = CLI()
    return _cli
