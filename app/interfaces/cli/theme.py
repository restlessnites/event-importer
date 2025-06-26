"""Unified theme system with all visual configuration in one place."""

from __future__ import annotations

from dataclasses import dataclass, field

from rich import box


@dataclass
class Icons:
    """Icon set for CLI - clean text symbols instead of emojis."""

    # Core status icons
    success = "✓"
    error = "✗"
    warning = "!"
    info = "•"

    # Progress and activity
    running = "→"
    waiting = "⋯"
    spinner = "⋯"

    # Operations
    import_icon = "↓"
    export = "↑"
    sync = "⟳"

    # Objects
    event = "◆"
    artist = "♪"
    image = "▢"
    url = "⎘"
    time = "◷"
    location = "◉"

    # Status indicators
    cached = "⚡"
    fresh = "⟳"
    failed = "✗"

    # General
    bullet = "‣"


@dataclass
class Spacing:
    """Vertical spacing system (in newlines)."""

    # Specific contexts - adjust these to taste
    before_header: int = 0
    after_header: int = 1
    before_section: int = 1
    after_section: int = 1
    between_items: int = 1
    after_table: int = 1
    # Rule spacing
    before_rule: int = 1
    after_rule: int = 1


@dataclass
class Typography:
    """Typography styles for different text elements."""

    # Headers
    header_style: str = "bold bright_blue"
    header_transform: str = "upper"  # upper, lower, title, none

    subheader_style: str = "blue"
    subheader_transform: str = "none"

    # Sections
    section_style: str = "bold cyan"
    section_transform: str = "upper"
    section_underline: str = "─"  # Character to repeat for underline

    # Labels and values
    label_style: str = "bold"
    value_style: str = "default"

    # Status messages
    success_style: str = "bold green"
    error_style: str = "bold red"
    warning_style: str = "bold yellow"
    info_style: str = "cyan"

    # Other text
    muted_style: str = "bright_black"
    dim_style: str = "dim"


@dataclass
class Layout:
    """Layout configuration."""

    # Table
    table_box: box.Box = field(default_factory=lambda: box.ROUNDED)
    table_border_style: str = "bright_black"

    # URL display
    url_style: str = "full"  # "full", "domain", "compact"


@dataclass
class Theme:
    """Complete theme configuration."""

    icons: Icons = field(default_factory=Icons)
    spacing: Spacing = field(default_factory=Spacing)
    typography: Typography = field(default_factory=Typography)
    layout: Layout = field(default_factory=Layout)

    # Layout basics
    width: int = 100
    indent: str = "  "

    def transform_text(self: Theme, text: str, transform: str) -> str:
        """Apply text transformation."""
        if transform == "upper":
            return text.upper()
        if transform == "lower":
            return text.lower()
        if transform == "title":
            return text.title()
        return text
