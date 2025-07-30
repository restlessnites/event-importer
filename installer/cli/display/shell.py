"""Shell configuration display functions."""

from pathlib import Path

import clicycle

from installer.constants import CONFIG
from installer.services import shell_service


def display_shell_configuration(app_path: Path):
    """Display shell PATH configuration."""
    clicycle.section("Shell Configuration")

    if clicycle.confirm("Make 'event-importer' accessible from anywhere?"):
        try:
            if shell_service.is_path_configured():
                clicycle.info("PATH already configured in your shell profile.")
                return

            shell_service.add_to_path()
            profile_file = shell_service.get_shell_profile_path()

            clicycle.success(f"Added Event Importer to your PATH in {profile_file}")
            clicycle.info("Restart your terminal or run:")
            clicycle.code(f"source {profile_file}", language="bash", line_numbers=False)
            clicycle.info("Then you can use 'event-importer' from anywhere!")

        except Exception as e:
            clicycle.warning(f"Could not automatically configure PATH: {e}")
            clicycle.info("You can manually add this to your shell profile:")
            clicycle.code(CONFIG.path_export_line, language="bash", line_numbers=False)
    else:
        clicycle.info(f"You can run Event Importer from: {app_path}")
