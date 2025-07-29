"""Installer for Event Importer."""

import asyncio
import os
import shutil
import subprocess  # noqa: S404
import sys
from pathlib import Path

import clicycle
from clicycle import Theme, Typography

from config.settings import get_api_keys, get_setting_info
from installer.components.claude_desktop import ClaudeDesktopConfig
from installer.components.migration import MigrationManager
from installer.components.settings_manager import SettingsManager
from installer.downloader import AppDownloader
from installer.paths import get_install_dir, get_user_data_dir


def cleanup_original_location(installer_path: Path):
    """Clean up the original download location."""
    try:
        parent_dir = installer_path.parent
        # Look for zip files in the parent directory
        for zip_file in parent_dir.glob("*.zip"):
            if "event-importer" in zip_file.name.lower():
                zip_file.unlink()
                clicycle.info(f"Cleaned up: {zip_file.name}")

        # If the parent directory is now empty and in Downloads, remove it
        if (
            parent_dir.name.startswith("restless-event-importer")
            and "Downloads" in str(parent_dir)
            and not any(parent_dir.iterdir())
        ):
            parent_dir.rmdir()
            clicycle.info(f"Removed empty directory: {parent_dir}")
    except Exception as e:
        clicycle.warning(f"Could not clean up original location: {e}")


async def download_app(settings_manager: SettingsManager) -> Path | None:
    """Download the Event Importer app."""
    # Get download URL from config
    download_url = settings_manager.get("update_url")
    if not download_url:
        clicycle.error("No download URL configured")
        return None

    # Use centralized install directory
    install_dir = get_install_dir()
    app_name = "event-importer"
    app_path = install_dir / app_name

    clicycle.section("Downloading Event Importer")
    clicycle.info(f"Downloading from: {download_url}")
    clicycle.info(f"Installing to: {app_path}")

    try:
        downloader = AppDownloader(download_url)
        await downloader.download(app_path)
        clicycle.success("Download complete!")
        return app_path
    except Exception as e:
        clicycle.error(f"Download failed: {e}")
        return None


def launch_app(app_path: Path):
    """Launch the downloaded app."""
    clicycle.info("Launching Event Importer...")
    try:
        # Launch in background and exit
        subprocess.Popen(
            [str(app_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception as e:
        clicycle.error(f"Failed to launch app: {e}")
        clicycle.info(f"You can manually run: {app_path}")


def setup_directories():
    """Create and validate installation directories."""
    install_dir = get_install_dir()

    # First ensure ~/Applications exists
    apps_dir = install_dir.parent
    if not apps_dir.exists():
        try:
            apps_dir.mkdir(parents=True, exist_ok=True)
            clicycle.info("Created Applications directory:")
            clicycle.code(str(apps_dir), language="text", line_numbers=False)
        except Exception as e:
            clicycle.error(f"Failed to create Applications directory: {e}")
            sys.exit(1)

    # Now create the restless-event-importer directory
    if not install_dir.exists():
        try:
            install_dir.mkdir(parents=True, exist_ok=True)
            clicycle.success("Created installation directory:")
            clicycle.code(str(install_dir), language="text", line_numbers=False)
        except Exception as e:
            clicycle.error(f"Failed to create installation directory: {e}")
            clicycle.info("Please check your permissions and try again")
            sys.exit(1)
    else:
        clicycle.info("Using installation directory:")
        clicycle.code(str(install_dir), language="text", line_numbers=False)

    # Check if we have write permissions
    if not os.access(install_dir, os.W_OK):
        clicycle.error("No write permission to:")
        clicycle.code(str(install_dir), language="text", line_numbers=False)
        clicycle.info("Please check directory permissions and try again")
        sys.exit(1)

    return install_dir


def setup_installer_location(install_dir: Path):
    """Move installer to installation directory if needed."""
    current_path = Path(sys.argv[0]).resolve()
    if current_path.parent != install_dir:
        new_installer_path = install_dir / current_path.name
        try:
            shutil.copy2(current_path, new_installer_path)
            clicycle.info("Copied installer to:")
            clicycle.code(str(new_installer_path), language="text", line_numbers=False)
            cleanup_original_location(current_path)
        except Exception as e:
            clicycle.warning(f"Could not move installer: {e}")


def setup_data_directory():
    """Create data directory if needed."""
    data_dir = get_user_data_dir()
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        clicycle.success("Created data directory:")
        clicycle.code(str(data_dir), language="text", line_numbers=False)
    else:
        clicycle.info("Using data directory:")
        clicycle.code(str(data_dir), language="text", line_numbers=False)


def handle_migration():
    """Handle migration from previous installation."""
    if clicycle.confirm("Do you have a previous installation to migrate from?"):
        migration_path = clicycle.prompt("Enter the path to your previous installation")
        if migration_path:
            migration_manager = MigrationManager()
            if migration_manager.migrate_from_path(Path(migration_path)):
                clicycle.success("Migration completed successfully!")
            else:
                clicycle.warning("Migration failed, continuing with fresh setup")


def configure_api_keys(settings_manager: SettingsManager):
    """Configure missing API keys."""
    missing_keys = []
    for key in get_api_keys():
        if not settings_manager.get(key):
            missing_keys.append(key)

    if missing_keys:
        clicycle.section("API Keys")
        clicycle.info("Let's configure your API keys.")

        for key in missing_keys:
            info = get_setting_info(key)
            if info:
                with clicycle.block():
                    clicycle.info(f"{info.display_name}: {info.description}")
                    if info.instructions:
                        clicycle.info(f"Get your key at: {info.instructions}")

                value = clicycle.prompt(f"Enter {info.display_name}")
                if value:
                    settings_manager.set(key, value)

        clicycle.success("API keys configured!")


def configure_download_url(settings_manager: SettingsManager):
    """Configure download URL if not set."""
    if not settings_manager.get("update_url"):
        default_url = "https://github.com/yourusername/event-importer/releases/latest/download/event-importer-macos"
        url = clicycle.prompt(
            "Enter the download URL for Event Importer", default=default_url
        )
        settings_manager.set("update_url", url)


def configure_claude_desktop():
    """Configure Claude Desktop integration."""
    clicycle.section("Claude Desktop Integration")
    claude_config = ClaudeDesktopConfig(is_packaged=True)

    if claude_config.is_claude_desktop_installed():
        clicycle.info("Claude Desktop detected!")
        if clicycle.confirm("Would you like to configure Claude Desktop integration?"):
            if claude_config.configure_for_packaged():
                clicycle.success("Claude Desktop configured successfully!")
            else:
                clicycle.warning("Failed to configure Claude Desktop")
    else:
        clicycle.info("Claude Desktop not found. You can configure it later if needed.")


def configure_shell_path(app_path: Path):
    """Configure shell PATH to make event-importer globally accessible."""
    clicycle.section("Shell Configuration")

    if clicycle.confirm(
        "Would you like to make 'event-importer' accessible from anywhere in your terminal?"
    ):
        # Detect shell
        shell = os.environ.get("SHELL", "/bin/bash")
        if "zsh" in shell:
            profile_file = Path.home() / ".zshrc"
        elif "bash" in shell:
            profile_file = Path.home() / ".bash_profile"
        else:
            profile_file = Path.home() / ".profile"

        # PATH export line
        path_line = 'export PATH="$HOME/Applications/restless-event-importer:$PATH"'

        try:
            # Check if already configured
            if profile_file.exists():
                content = profile_file.read_text()
                if "restless-event-importer" in content:
                    clicycle.info("PATH already configured in your shell profile.")
                    return

            # Add to shell profile
            with profile_file.open("a") as f:
                f.write(f"\n# Event Importer PATH\n{path_line}\n")

            clicycle.success(f"Added Event Importer to your PATH in {profile_file}")
            clicycle.info("Restart your terminal or run:")
            clicycle.code(f"source {profile_file}", language="bash", line_numbers=False)
            clicycle.info("Then you can use 'event-importer' from anywhere!")

        except Exception as e:
            clicycle.warning(f"Could not automatically configure PATH: {e}")
            clicycle.info("You can manually add this to your shell profile:")
            clicycle.code(f"{path_line}", language="bash", line_numbers=False)
    else:
        clicycle.info(f"You can run Event Importer from: {app_path}")


async def run_installer():
    """Run the installation process."""
    # Clear the terminal to remove the login/command info
    os.system("clear" if os.name != "nt" else "cls")  # noqa: S605

    # Create a theme that works on both light and dark backgrounds
    universal_theme = Theme(
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
    clicycle.configure(
        app_name="event-importer-installer", width=80, theme=universal_theme
    )

    # Welcome
    clicycle.header("SETUP", "Set up Restless Event Importer on your system.")

    # Setup directories and locations
    install_dir = setup_directories()
    setup_installer_location(install_dir)
    setup_data_directory()

    # Initialize settings
    settings_manager = SettingsManager()

    # Handle migration, configuration
    handle_migration()
    configure_api_keys(settings_manager)
    configure_download_url(settings_manager)
    configure_claude_desktop()

    # Save final config
    settings_manager.set("version", "3RR0R")
    settings_manager.set("first_run_complete", "true")

    # Download and launch
    app_path = await download_app(settings_manager)
    if not app_path:
        clicycle.error("Installation failed. Please try again.")
        sys.exit(1)

    clicycle.success("Installation complete!")

    # Configure shell PATH
    configure_shell_path(app_path)

    if clicycle.confirm("Launch Event Importer now?"):
        launch_app(app_path)
    else:
        clicycle.info(f"You can run Event Importer from: {app_path}")


def main():
    """Main entry point."""
    try:
        asyncio.run(run_installer())
    except KeyboardInterrupt:
        print()
        clicycle.warning("Installation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        clicycle.error(f"Installation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
