"""Design system and theme configuration."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Icons:
    """Icon set for CLI display."""

    # Status
    running: str = "▸"
    success: str = "✓"
    error: str = "✗"
    warning: str = "⚠"
    info: str = "•"

    # Progress
    spinner: str = "◠"
    progress: str = "━"
    progress_fill: str = "━"
    progress_empty: str = "╺"

    # Structure
    bullet: str = "•"
    arrow: str = "→"
    branch: str = "├"
    corner: str = "└"
    pipe: str = "│"

    # UI elements
    check: str = "☑"
    uncheck: str = "☐"
    star: str = "★"

    def get_ascii_fallback(self) -> "Icons":
        """Return ASCII-only version of icons."""
        return Icons(
            running=">",
            success="[OK]",
            error="[X]",
            warning="[!]",
            info="-",
            spinner="*",
            progress="=",
            progress_fill="#",
            progress_empty="-",
            bullet="*",
            arrow="->",
            branch="+",
            corner="L",
            pipe="|",
            check="[x]",
            uncheck="[ ]",
            star="*",
        )


@dataclass
class Spacing:
    """Spacing system (in lines)."""

    none: int = 0
    xs: int = 1
    sm: int = 1
    md: int = 2
    lg: int = 3
    xl: int = 4


@dataclass
class Colors:
    """Color palette for Rich markup."""

    # Primary
    primary: str = "blue"
    primary_bright: str = "bright_blue"

    # Semantic
    success: str = "green"
    success_bright: str = "bright_green"
    error: str = "red"
    error_bright: str = "bright_red"
    warning: str = "yellow"
    warning_bright: str = "bright_yellow"
    info: str = "cyan"
    info_bright: str = "bright_cyan"

    # Neutral
    text: str = "default"
    text_muted: str = "bright_black"
    text_dim: str = "dim"

    # Special
    accent: str = "magenta"
    highlight: str = "on dark_blue"

    def style(self, style_name: str) -> str:
        """Get style string for Rich markup."""
        styles = {
            # Headers
            "header": f"bold {self.primary_bright}",
            "subheader": f"bold {self.primary}",
            "section": f"{self.primary}",
            # Status
            "success": f"{self.success_bright}",
            "error": f"{self.error_bright}",
            "warning": f"{self.warning_bright}",
            "info": f"{self.info}",
            "running": f"{self.primary}",
            # Text
            "muted": self.text_muted,
            "dim": self.text_dim,
            "code": f"{self.accent}",
            "highlight": self.highlight,
            # Data
            "label": "bold",
            "value": "default",
            "number": f"{self.accent}",
            "string": f"{self.success}",
            "none": self.text_dim,
        }
        return styles.get(style_name, "default")


@dataclass
class Theme:
    """Complete theme configuration."""

    icons: Icons
    spacing: Spacing
    colors: Colors

    # Layout
    width: int = 100
    indent: str = "  "

    # Features
    use_unicode: bool = True
    use_color: bool = True

    @classmethod
    def default(cls) -> "Theme":
        """Get default theme."""
        return cls(icons=Icons(), spacing=Spacing(), colors=Colors())

    @classmethod
    def minimal(cls) -> "Theme":
        """Get minimal ASCII theme."""
        return cls(
            icons=Icons().get_ascii_fallback(),
            spacing=Spacing(),
            colors=Colors(),
            use_unicode=False,
        )

    def format_status(self, status: str) -> str:
        """Format a status string (remove enum cruft)."""
        # Handle "ImportStatus.RUNNING" -> "Running"
        if "." in status:
            status = status.split(".")[-1]
        return status.replace("_", " ").title()
