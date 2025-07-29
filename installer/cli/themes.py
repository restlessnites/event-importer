"""Terminal themes for installer."""

from clicycle import Theme, Typography


def get_universal_theme():
    """Get a theme that works on both light and dark backgrounds."""
    return Theme(
        typography=Typography(
            header_style="bold",
            section_style="bold",
            info_style="default",
            success_style="bold",
            error_style="bold",
            warning_style="bold",
            muted_style="dim",
            value_style="default",
        ),
        width=80,
    )
