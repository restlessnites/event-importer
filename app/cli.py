"""Developer CLI for testing and debugging."""

from typing import Optional, Any
from datetime import datetime
from contextlib import contextmanager

try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
    )
    from rich.syntax import Syntax

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("WARNING: Rich not installed. Output will be basic.")


class CLI:
    """Developer-focused CLI for debugging."""

    def __init__(self):
        """Initialize CLI."""
        if RICH_AVAILABLE:
            # Wide console for development
            self.console = Console(width=160, force_terminal=True)
        else:
            self.console = None
        self._progress = None
        self._task_id = None

    def print(self, *args, **kwargs):
        """Print output."""
        if self.console:
            self.console.print(*args, **kwargs)
        else:
            print(*args)

    def header(self, title: str, subtitle: Optional[str] = None) -> None:
        """Show a header."""
        if self.console:
            self.console.rule(f"[bold cyan]{title}[/bold cyan]")
            if subtitle:
                self.console.print(f"[dim]{subtitle}[/dim]", justify="center")
        else:
            print(f"\n{'=' * 80}")
            print(title)
            if subtitle:
                print(subtitle)
            print("=" * 80)

    def section(self, title: str) -> None:
        """Show a section."""
        self.print(f"\n[bold]{title}[/bold]" if self.console else f"\n{title}")

    def info(self, message: str) -> None:
        """Info message."""
        self.print(message)

    def success(self, message: str) -> None:
        """Success message."""
        if self.console:
            self.console.print(f"[green]✓[/green] {message}")
        else:
            print(f"✓ {message}")

    def error(self, message: str) -> None:
        """Error message."""
        if self.console:
            self.console.print(f"[red]✗[/red] {message}", style="red")
        else:
            print(f"✗ {message}")

    def warning(self, message: str) -> None:
        """Warning message."""
        if self.console:
            self.console.print(f"[yellow]⚠[/yellow]  {message}", style="yellow")
        else:
            print(f"⚠ {message}")

    @contextmanager
    def progress(self, description: str = "Processing"):
        """Progress bar context manager."""
        if self.console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
                transient=True,
            ) as progress:
                self._progress = progress
                self._task_id = progress.add_task(description, total=100)
                yield self
                self._progress = None
                self._task_id = None
        else:
            print(f"{description}...")
            yield self

    def update_progress(self, percent: float, message: Optional[str] = None) -> None:
        """Update progress bar."""
        if self._progress and self._task_id is not None:
            self._progress.update(
                self._task_id,
                completed=percent,
                description=message or self._progress.tasks[self._task_id].description,
            )

    @contextmanager
    def spinner(self, message: str):
        """Show a spinner."""
        if self.console:
            with self.console.status(message):
                yield
        else:
            print(f"{message}...", end="", flush=True)
            yield
            print(" done")

    def json(self, data: dict, title: Optional[str] = None) -> None:
        """Show JSON data with syntax highlighting."""
        import json

        if title:
            self.section(title)

        json_str = json.dumps(data, indent=2, default=str)

        if self.console:
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
            self.console.print(syntax)
        else:
            print(json_str)

    def event_data(self, event: dict) -> None:
        """Display ALL event data for debugging."""
        self.section("Event Data")

        # Basic fields
        if event.get("title"):
            self.info(f"Title: {event['title']}")
        if event.get("venue"):
            self.info(f"Venue: {event['venue']}")
        if event.get("date"):
            self.info(f"Date: {event['date']}")
        if event.get("time"):
            time = event["time"]
            if isinstance(time, dict):
                self.info(f"Time: {time.get('start', '?')} - {time.get('end', '?')}")
        if event.get("cost"):
            self.info(f"Cost: {event['cost']}")
        if event.get("minimum_age"):
            self.info(f"Age: {event['minimum_age']}")

        # Lists
        if event.get("lineup"):
            self.info(f"\nLineup ({len(event['lineup'])}):")
            for artist in event["lineup"]:
                self.info(f"  - {artist}")

        if event.get("promoters"):
            self.info(f"\nPromoters: {', '.join(event['promoters'])}")

        if event.get("genres"):
            self.info(f"Genres: {', '.join(event['genres'])}")

        # Location - show ALL fields
        if event.get("location"):
            self.info("\nLocation:")
            loc = event["location"]
            for key, value in loc.items():
                if value:
                    self.info(f"  {key}: {value}")

        # Descriptions - FULL TEXT, NO TRUNCATION
        if event.get("short_description"):
            self.info(f"\nShort description ({len(event['short_description'])} chars):")
            self.info(event["short_description"])

        if event.get("long_description"):
            self.info(f"\nFull description ({len(event['long_description'])} chars):")
            self.info(event["long_description"])

        # URLs - FULL URLS, NO TRUNCATION
        if event.get("ticket_url"):
            self.info(f"\nTicket URL:")
            self.info(event["ticket_url"])

        if event.get("source_url"):
            self.info(f"\nSource URL:")
            self.info(event["source_url"])

        # Images - FULL URLS
        if event.get("images"):
            self.info("\nImages:")
            for key, url in event["images"].items():
                self.info(f"  {key}: {url}")

        # Image search results if present
        if event.get("image_search"):
            self.image_search_debug(event["image_search"])

        # Metadata
        if event.get("imported_at"):
            self.info(f"\nImported at: {event['imported_at']}")

    def import_summary(self, result: dict) -> None:
        """Show import result summary."""
        self.section("Import Summary")

        status = result.get("status", "UNKNOWN")
        if status == "SUCCESS":
            self.success("Import completed successfully")
        else:
            self.error(f"Import failed with status: {status}")

        # All details
        self.info(f"Method: {result.get('method_used', 'Unknown')}")
        self.info(f"Duration: {result.get('import_time', 0):.2f}s")
        self.info(f"Request ID: {result.get('request_id', 'None')}")

        if result.get("error"):
            self.error(f"Error: {result['error']}")

    def image_search_debug(self, search_data: dict) -> None:
        """Show detailed image search results for debugging."""
        self.section("Image Search Results")

        # Original
        if search_data.get("original"):
            orig = search_data["original"]
            self.info("\nOriginal image:")
            self.info(f"  Score: {orig['score']}")
            self.info(f"  Dimensions: {orig.get('dimensions', 'Unknown')}")
            self.info(f"  Reason: {orig.get('reason', 'N/A')}")
            self.info(f"  URL: {orig['url']}")

        # All candidates
        if search_data.get("candidates"):
            self.info(f"\nFound {len(search_data['candidates'])} candidates:")
            # Show ALL candidates for debugging
            for i, cand in enumerate(search_data["candidates"], 1):
                self.info(f"\nCandidate {i}:")
                self.info(f"  Score: {cand['score']}")
                self.info(f"  Source: {cand.get('source', 'unknown')}")
                self.info(f"  Dimensions: {cand.get('dimensions', 'Unknown')}")
                self.info(f"  URL: {cand['url']}")

        # Selected
        if search_data.get("selected"):
            sel = search_data["selected"]
            self.success(f"\nSelected image:")
            self.info(f"  Score: {sel['score']}")
            self.info(f"  Source: {sel.get('source', 'unknown')}")
            self.info(f"  URL: {sel['url']}")

    def progress_update(self, update: dict) -> None:
        """Show a single progress update."""
        timestamp = update.get("timestamp")
        if timestamp:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp)
            else:
                dt = timestamp
            time_str = dt.strftime("%H:%M:%S")
        else:
            time_str = "??:??:??"

        status = update.get("status", "unknown")
        progress = update.get("progress", 0) * 100
        message = update.get("message", "")

        # Color status
        if self.console:
            status_colors = {
                "running": "blue",
                "success": "green",
                "failed": "red",
                "pending": "yellow",
            }
            color = status_colors.get(status.lower(), "white")
            self.console.print(
                f"{time_str} [[{color}]{status.upper()}[/{color}]] {progress:3.0f}% - {message}"
            )
        else:
            print(f"{time_str} [{status.upper()}] {progress:3.0f}% - {message}")

    def debug_data(self, data: Any, title: str = "Debug Data") -> None:
        """Show any data structure for debugging."""
        self.section(title)

        if isinstance(data, dict):
            for key, value in data.items():
                self.info(f"{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self.info(f"[{i}] {item}")
        else:
            self.info(str(data))


# Global instance
_cli: Optional[CLI] = None


def get_cli() -> CLI:
    """Get CLI instance."""
    global _cli
    if _cli is None:
        _cli = CLI()
    return _cli
