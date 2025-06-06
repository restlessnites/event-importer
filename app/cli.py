"""CLI interface components for test scripts and debugging."""

import sys
import time
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from contextlib import contextmanager
from enum import Enum

# Try to import Rich for output, fallback to basic if not available
try:
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
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class Style(Enum):
    """Terminal styles for fallback mode."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


class CLI:
    """CLI interface for event importer."""

    def __init__(self, use_color: bool = True):
        """Initialize CLI with optional color support."""
        self.use_color = use_color and sys.stdout.isatty()

        if RICH_AVAILABLE:
            self.console = Console(force_terminal=self.use_color)
        else:
            self.console = None

        self._progress = None
        self._task_id = None

    def _style(self, text: str, *styles: Style) -> str:
        """Apply styles to text in fallback mode."""
        if not self.use_color or RICH_AVAILABLE:
            return text

        styled = text
        for style in styles:
            styled = f"{style.value}{styled}"
        return f"{styled}{Style.RESET.value}"

    # Header and sections

    def header(self, title: str, subtitle: Optional[str] = None) -> None:
        """Display a prominent header."""
        if RICH_AVAILABLE and self.console:
            header_text = Text(title, style="bold cyan")
            if subtitle:
                header_text.append(f"\n{subtitle}", style="dim")
            self.console.print(Panel(header_text, box=box.DOUBLE))
        else:
            print(f"\n{self._style('═' * 60, Style.CYAN)}")
            print(self._style(title.upper(), Style.BOLD, Style.CYAN))
            if subtitle:
                print(self._style(subtitle, Style.DIM))
            print(f"{self._style('═' * 60, Style.CYAN)}\n")

    def section(self, title: str) -> None:
        """Display a section header."""
        if RICH_AVAILABLE and self.console:
            self.console.print(f"\n[bold blue]▸ {title}[/bold blue]")
        else:
            print(f"\n{self._style('▸ ' + title, Style.BOLD, Style.BLUE)}")

    # Status messages

    def info(self, message: str) -> None:
        """Display an info message."""
        if RICH_AVAILABLE and self.console:
            self.console.print(f"[dim]→[/dim] {message}")
        else:
            print(f"{self._style('→', Style.DIM)} {message}")

    def success(self, message: str) -> None:
        """Display a success message."""
        if RICH_AVAILABLE and self.console:
            self.console.print(f"[green]✓[/green] {message}")
        else:
            print(f"{self._style('✓', Style.GREEN)} {message}")

    def error(self, message: str) -> None:
        """Display an error message."""
        if RICH_AVAILABLE and self.console:
            self.console.print(f"[red]✗[/red] {message}", style="red")
        else:
            print(f"{self._style('✗', Style.RED)} {self._style(message, Style.RED)}")

    def warning(self, message: str) -> None:
        """Display a warning message."""
        if RICH_AVAILABLE and self.console:
            self.console.print(f"[yellow]⚠[/yellow] {message}", style="yellow")
        else:
            print(
                f"{self._style('⚠', Style.YELLOW)} {self._style(message, Style.YELLOW)}"
            )

    # Progress tracking

    @contextmanager
    def progress(self, description: str = "Processing"):
        """Context manager for progress tracking."""
        if RICH_AVAILABLE and self.console:
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
        else:
            # Fallback progress
            print(
                f"{self._style('⟳', Style.BLUE)} {description}...", end="", flush=True
            )
            start_time = time.time()
            yield self
            elapsed = time.time() - start_time
            print(f" {self._style('done', Style.GREEN)} ({elapsed:.1f}s)")

    def update_progress(self, percent: float, message: Optional[str] = None) -> None:
        """Update progress bar."""
        if RICH_AVAILABLE and self._progress and self._task_id is not None:
            if message:
                self._progress.update(self._task_id, description=message)
            self._progress.update(self._task_id, completed=percent)
        else:
            # Simple dots for fallback
            if int(percent) % 20 == 0:
                print(".", end="", flush=True)

    @contextmanager
    def spinner(self, message: str):
        """Show a spinner for indeterminate progress."""
        if RICH_AVAILABLE and self.console:
            with self.console.status(message, spinner="dots"):
                yield
        else:
            print(f"{self._style('⟳', Style.BLUE)} {message}...", end="", flush=True)
            yield
            print(f" {self._style('done', Style.GREEN)}")

    # Data display

    def table(self, data: List[Dict[str, Any]], title: Optional[str] = None) -> None:
        """Display data in a table."""
        if not data:
            return

        if RICH_AVAILABLE and self.console:
            table = Table(title=title, box=box.SIMPLE)

            # Add columns
            for key in data[0].keys():
                table.add_column(key.replace("_", " ").title(), style="cyan")

            # Add rows
            for row in data:
                table.add_row(*[str(v) for v in row.values()])

            self.console.print(table)
        else:
            # Fallback table
            if title:
                print(f"\n{self._style(title, Style.BOLD)}")

            if data:
                # Calculate column widths
                keys = list(data[0].keys())
                widths = {
                    k: max(len(k), max(len(str(row.get(k, ""))) for row in data))
                    for k in keys
                }

                # Header
                header = " │ ".join(k.ljust(widths[k]) for k in keys)
                print(self._style(header, Style.BOLD))
                print(self._style("─" * len(header), Style.DIM))

                # Rows
                for row in data:
                    print(
                        " │ ".join(str(row.get(k, "")).ljust(widths[k]) for k in keys)
                    )

    def json(self, data: dict, title: Optional[str] = None) -> None:
        """Display JSON data with syntax highlighting."""
        import json

        json_str = json.dumps(data, indent=2)

        if RICH_AVAILABLE and self.console:
            if title:
                self.console.print(f"\n[bold]{title}[/bold]")
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
            self.console.print(syntax)
        else:
            if title:
                print(f"\n{self._style(title, Style.BOLD)}")
            print(json_str)

    def code(
        self, code: str, language: str = "python", title: Optional[str] = None
    ) -> None:
        """Display code with syntax highlighting."""
        if RICH_AVAILABLE and self.console:
            if title:
                self.console.print(f"\n[bold]{title}[/bold]")
            syntax = Syntax(code, language, theme="monokai", line_numbers=True)
            self.console.print(syntax)
        else:
            if title:
                print(f"\n{self._style(title, Style.BOLD)}")
            print(code)

    # Event display helpers

    def event_card(self, event_data: dict) -> None:
        """Display event data in a nice card format."""
        if RICH_AVAILABLE and self.console:
            from rich.columns import Columns
            from rich.tree import Tree

            # Title panel
            title_text = Text(
                event_data.get("title", "Untitled Event"), style="bold cyan"
            )
            self.console.print(Panel(title_text, box=box.DOUBLE))

            # Create two columns for basic info
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
                    Columns(["\n".join(left_col), "\n".join(right_col)], padding=(0, 2))
                )

            # Lineup
            if event_data.get("lineup"):
                self.console.print(
                    f"\n[bold]Lineup:[/bold] {', '.join(event_data['lineup'])}"
                )

            # Genres
            if event_data.get("genres"):
                self.console.print(
                    f"[bold]Genres:[/bold] {', '.join(event_data['genres'])}"
                )

            # Location details
            if event_data.get("location"):
                loc = event_data["location"]
                loc_parts = []
                if loc.get("address"):
                    loc_parts.append(loc["address"])
                if loc.get("city"):
                    loc_parts.append(loc["city"])
                if loc.get("state"):
                    loc_parts.append(loc["state"])
                if loc.get("country"):
                    loc_parts.append(loc["country"])
                if loc_parts:
                    self.console.print(
                        f"\n[bold]Location:[/bold] {', '.join(loc_parts)}"
                    )
                if loc.get("coordinates"):
                    coords = loc["coordinates"]
                    self.console.print(
                        f"[bold]Coordinates:[/bold] {coords['lat']}, {coords['lng']}"
                    )

            # Descriptions
            if event_data.get("short_description"):
                self.console.print(
                    f"\n[bold]Summary:[/bold] {event_data['short_description']}"
                )

            if event_data.get("long_description"):
                self.console.print(f"\n[bold]Description:[/bold]")
                # Wrap long description nicely
                desc = event_data["long_description"]
                if len(desc) > 300:
                    desc = desc[:300] + "..."
                self.console.print(Text(desc, style="dim"))

            # URLs
            urls_to_show = []
            if event_data.get("ticket_url"):
                urls_to_show.append(
                    f"[bold]Tickets:[/bold] [link]{event_data['ticket_url']}[/link]"
                )
            if event_data.get("source_url"):
                urls_to_show.append(
                    f"[bold]Source:[/bold] [link]{event_data['source_url']}[/link]"
                )
            if urls_to_show:
                self.console.print("\n" + "\n".join(urls_to_show))

            # Images
            if event_data.get("images"):
                imgs = event_data["images"]
                img_info = []
                if imgs.get("full"):
                    img_info.append(
                        "[bold]Full:[/bold] "
                        + (
                            imgs["full"][:60] + "..."
                            if len(imgs["full"]) > 60
                            else imgs["full"]
                        )
                    )
                if imgs.get("thumbnail") and imgs.get("thumbnail") != imgs.get("full"):
                    img_info.append(
                        "[bold]Thumb:[/bold] "
                        + (
                            imgs["thumbnail"][:60] + "..."
                            if len(imgs["thumbnail"]) > 60
                            else imgs["thumbnail"]
                        )
                    )
                if img_info:
                    self.console.print(f"\n[bold]Images:[/bold]")
                    for info in img_info:
                        self.console.print(f"  {info}")

            # Metadata
            if event_data.get("imported_at"):
                self.console.print(
                    f"\n[dim]Imported: {event_data['imported_at']}[/dim]"
                )

        else:
            # Fallback display - comprehensive
            print(f"\n{self._style('═' * 80, Style.CYAN)}")
            print(
                self._style(
                    event_data.get("title", "Untitled Event"), Style.BOLD, Style.CYAN
                )
            )
            print(f"{self._style('═' * 80, Style.CYAN)}")

            # Basic info
            print(f"\n{self._style('Basic Information:', Style.BOLD, Style.BLUE)}")
            if event_data.get("venue"):
                print(f"  {self._style('Venue:', Style.BOLD)} {event_data['venue']}")
            if event_data.get("date"):
                print(f"  {self._style('Date:', Style.BOLD)} {event_data['date']}")
            if event_data.get("time"):
                time = event_data["time"]
                if isinstance(time, dict):
                    time_str = f"{time.get('start', 'TBD')}"
                    if time.get("end"):
                        time_str += f" - {time['end']}"
                    print(f"  {self._style('Time:', Style.BOLD)} {time_str}")
            if event_data.get("cost"):
                print(f"  {self._style('Cost:', Style.BOLD)} {event_data['cost']}")
            if event_data.get("minimum_age"):
                print(
                    f"  {self._style('Age:', Style.BOLD)} {event_data['minimum_age']}"
                )

            # People
            if event_data.get("lineup") or event_data.get("promoters"):
                print(f"\n{self._style('People:', Style.BOLD, Style.BLUE)}")
                if event_data.get("lineup"):
                    print(
                        f"  {self._style('Lineup:', Style.BOLD)} {', '.join(event_data['lineup'])}"
                    )
                if event_data.get("promoters"):
                    print(
                        f"  {self._style('Promoters:', Style.BOLD)} {', '.join(event_data['promoters'])}"
                    )

            # Categories
            if event_data.get("genres"):
                print(f"\n{self._style('Categories:', Style.BOLD, Style.BLUE)}")
                print(
                    f"  {self._style('Genres:', Style.BOLD)} {', '.join(event_data['genres'])}"
                )

            # Location
            if event_data.get("location"):
                print(f"\n{self._style('Location:', Style.BOLD, Style.BLUE)}")
                loc = event_data["location"]
                loc_parts = []
                if loc.get("address"):
                    loc_parts.append(loc["address"])
                if loc.get("city"):
                    loc_parts.append(loc["city"])
                if loc.get("state"):
                    loc_parts.append(loc["state"])
                if loc.get("country"):
                    loc_parts.append(loc["country"])
                if loc_parts:
                    print(
                        f"  {self._style('Address:', Style.BOLD)} {', '.join(loc_parts)}"
                    )
                if loc.get("coordinates"):
                    coords = loc["coordinates"]
                    print(
                        f"  {self._style('Coordinates:', Style.BOLD)} {coords['lat']}, {coords['lng']}"
                    )

            # Descriptions
            if event_data.get("short_description") or event_data.get(
                "long_description"
            ):
                print(f"\n{self._style('Description:', Style.BOLD, Style.BLUE)}")
                if event_data.get("short_description"):
                    print(
                        f"  {self._style('Summary:', Style.BOLD)} {event_data['short_description']}"
                    )
                if event_data.get("long_description"):
                    desc = event_data["long_description"]
                    if len(desc) > 300:
                        desc = desc[:300] + "..."
                    print(
                        f"  {self._style('Full:', Style.BOLD)} {self._style(desc, Style.DIM)}"
                    )

            # Links
            if event_data.get("ticket_url") or event_data.get("source_url"):
                print(f"\n{self._style('Links:', Style.BOLD, Style.BLUE)}")
                if event_data.get("ticket_url"):
                    print(
                        f"  {self._style('Tickets:', Style.BOLD)} {event_data['ticket_url']}"
                    )
                if event_data.get("source_url"):
                    print(
                        f"  {self._style('Source:', Style.BOLD)} {event_data['source_url']}"
                    )

            # Images
            if event_data.get("images"):
                print(f"\n{self._style('Images:', Style.BOLD, Style.BLUE)}")
                imgs = event_data["images"]
                if imgs.get("full"):
                    print(
                        f"  {self._style('Full:', Style.BOLD)} {imgs['full'][:60]}..."
                        if len(imgs["full"]) > 60
                        else imgs["full"]
                    )
                if imgs.get("thumbnail") and imgs.get("thumbnail") != imgs.get("full"):
                    print(
                        f"  {self._style('Thumb:', Style.BOLD)} {imgs['thumbnail'][:60]}..."
                        if len(imgs["thumbnail"]) > 60
                        else imgs["thumbnail"]
                    )

            # Metadata
            if event_data.get("imported_at"):
                print(
                    f"\n{self._style('Imported:', Style.DIM)} {event_data['imported_at']}"
                )

    def progress_update(self, update: dict) -> None:
        """Display a progress update from the import system."""
        status = update.get("status", "unknown")
        message = update.get("message", "")
        progress = update.get("progress", 0) * 100

        # Status emoji/symbol mapping
        status_symbols = {
            "running": "⟳",
            "success": "✓",
            "failed": "✗",
            "pending": "○",
            "cancelled": "⊘",
        }

        # Status color mapping
        status_colors = {
            "running": Style.BLUE,
            "success": Style.GREEN,
            "failed": Style.RED,
            "pending": Style.YELLOW,
            "cancelled": Style.DIM,
        }

        symbol = status_symbols.get(status, "?")
        color = status_colors.get(status, Style.WHITE)

        if RICH_AVAILABLE and self.console:
            color_map = {
                "running": "blue",
                "success": "green",
                "failed": "red",
                "pending": "yellow",
                "cancelled": "dim",
            }
            rich_color = color_map.get(status, "white")
            self.console.print(
                f"[{rich_color}]{symbol}[/{rich_color}] [{rich_color}][{progress:3.0f}%][/{rich_color}] {message}"
            )
        else:
            print(
                f"{self._style(symbol, color)} {self._style(f'[{progress:3.0f}%]', color)} {message}"
            )

    # Utility methods

    def clear(self) -> None:
        """Clear the terminal."""
        if RICH_AVAILABLE and self.console:
            self.console.clear()
        else:
            print("\033[2J\033[H", end="")

    def raw_data(self, data: dict, title: str = "Raw Data") -> None:
        """Display raw data in a structured, readable format."""
        if RICH_AVAILABLE and self.console:
            from rich.tree import Tree

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
                            branch.add(f"[{i}] {item}")
                else:
                    # Format the value nicely
                    if value is None:
                        formatted = "[dim]null[/dim]"
                    elif isinstance(value, bool):
                        formatted = f"[yellow]{str(value).lower()}[/yellow]"
                    elif isinstance(value, (int, float)):
                        formatted = f"[magenta]{value}[/magenta]"
                    else:
                        formatted = f"[green]{value}[/green]"
                    parent.add(f"[bold]{key}:[/bold] {formatted}")

            for key, value in data.items():
                add_to_tree(tree, key, value)

            self.console.print(tree)
        else:
            # Fallback display
            print(f"\n{self._style(title, Style.BOLD, Style.BLUE)}")
            self._print_dict(data, indent=2)

    def _print_dict(self, data: dict, indent: int = 0) -> None:
        """Print dictionary in a structured way (fallback mode)."""
        prefix = " " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"{prefix}{self._style(key + ':', Style.BOLD)}")
                self._print_dict(value, indent + 2)
            elif isinstance(value, list):
                print(
                    f"{prefix}{self._style(key + ':', Style.BOLD)} [{len(value)} items]"
                )
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        print(f"{prefix}  [{i}]")
                        self._print_dict(item, indent + 4)
                    else:
                        print(f"{prefix}  [{i}] {item}")
            else:
                print(f"{prefix}{self._style(key + ':', Style.BOLD)} {value}")

    def image_search_results(self, search_data: dict) -> None:
        """Display image search results in a nice format."""
        if not search_data:
            return

        if RICH_AVAILABLE and self.console:
            from rich.columns import Columns

            # Original image
            if search_data.get("original"):
                orig = search_data["original"]
                self.console.print("\n[bold]Original Image:[/bold]")
                self.console.print(
                    f"  Score: [{'green' if orig['score'] > 100 else 'yellow'}]{orig['score']}[/]"
                )
                if orig.get("dimensions"):
                    self.console.print(f"  Dimensions: {orig['dimensions']}")
                if orig.get("reason"):
                    self.console.print(f"  Issue: [red]{orig['reason']}[/red]")
                self.console.print(
                    f"  URL: [dim]{orig['url'][:80]}...[/dim]"
                    if len(orig["url"]) > 80
                    else f"  URL: [dim]{orig['url']}[/dim]"
                )

            # Search candidates
            if search_data.get("candidates"):
                self.console.print(
                    f"\n[bold]Search Results:[/bold] {len(search_data['candidates'])} candidates found"
                )

                # Show top 3 candidates
                top_candidates = sorted(
                    search_data["candidates"],
                    key=lambda x: x.get("score", 0),
                    reverse=True,
                )[:3]
                for i, cand in enumerate(top_candidates, 1):
                    color = (
                        "green"
                        if cand["score"] > 200
                        else "yellow" if cand["score"] > 100 else "red"
                    )
                    self.console.print(
                        f"\n  [{i}] Score: [{color}]{cand['score']}[/] | Source: {cand.get('source', 'unknown')}"
                    )
                    if cand.get("dimensions"):
                        self.console.print(f"      Dimensions: {cand['dimensions']}")
                    url_display = (
                        cand["url"][:70] + "..."
                        if len(cand["url"]) > 70
                        else cand["url"]
                    )
                    self.console.print(f"      URL: [dim]{url_display}[/dim]")

            # Selected image
            if search_data.get("selected"):
                sel = search_data["selected"]
                self.console.print(f"\n[bold green]✓ Selected Image:[/bold green]")
                self.console.print(
                    f"  Score: [green]{sel['score']}[/green] | Source: {sel.get('source', 'unknown')}"
                )
                if sel.get("dimensions"):
                    self.console.print(f"  Dimensions: {sel['dimensions']}")
        else:
            # Fallback display
            print(f"\n{self._style('Image Search Results:', Style.BOLD, Style.BLUE)}")

            if search_data.get("original"):
                orig = search_data["original"]
                print(f"\n  {self._style('Original Image:', Style.BOLD)}")
                print(f"    Score: {orig['score']}")
                if orig.get("dimensions"):
                    print(f"    Dimensions: {orig['dimensions']}")
                if orig.get("reason"):
                    print(f"    Issue: {self._style(orig['reason'], Style.RED)}")

            if search_data.get("candidates"):
                print(
                    f"\n  {self._style('Candidates:', Style.BOLD)} {len(search_data['candidates'])} found"
                )

            if search_data.get("selected"):
                sel = search_data["selected"]
                print(f"\n  {self._style('✓ Selected:', Style.BOLD, Style.GREEN)}")
                print(
                    f"    Score: {sel['score']} | Source: {sel.get('source', 'unknown')}"
                )

    def rule(self, title: Optional[str] = None) -> None:
        """Draw a horizontal rule."""
        if RICH_AVAILABLE and self.console:
            self.console.rule(title or "")
        else:
            if title:
                padding = (60 - len(title) - 2) // 2
                line = f"{self._style('─' * padding, Style.DIM)} {title} {self._style('─' * padding, Style.DIM)}"
            else:
                line = self._style("─" * 60, Style.DIM)
            print(f"\n{line}\n")


# Global CLI instance
_cli: Optional[CLI] = None


def get_cli() -> CLI:
    """Get the global CLI instance."""
    global _cli
    if _cli is None:
        _cli = CLI()
    return _cli
