"""Main CLI application for installer."""

import sys
from pathlib import Path

import clicycle

from config.paths import get_install_dir
from config.settings import get_setting_info
from installer.cli.display.directories import display_directory_setup
from installer.cli.display.download import display_download_progress
from installer.cli.display.shell import display_shell_configuration
from installer.cli.display.utils import clear_terminal
from installer.cli.themes import get_universal_theme
from installer.components.claude_desktop import ClaudeDesktopConfig
from installer.operations.configure import (
    get_missing_api_keys,
    set_download_url_if_missing,
)
from installer.operations.download import download_app
from installer.operations.migrate import migrate_from_path
from installer.services.directory_service import (
    cleanup_download_location,
    create_data_directory,
    create_installation_directory,
    move_installer_to_install_dir,
)
from installer.services.settings_service import SettingsService
from installer.services.validation_service import InstallationValidator


def _initialize_cli():
    """Clear terminal and configure theme."""
    clear_terminal()
    clicycle.configure(
        app_name="event-importer-installer", width=80, theme=get_universal_theme()
    )
    clicycle.header("SETUP", "Set up Restless Event Importer on your system.")


def _setup_directories():
    """Set up installation and data directories."""
    try:
        install_dir = create_installation_directory()
        new_installer_path = move_installer_to_install_dir(install_dir)
        if new_installer_path:
            cleanup_download_location(new_installer_path)
        data_dir = create_data_directory()
        display_directory_setup(install_dir, data_dir, new_installer_path)
        return install_dir
    except PermissionError as e:
        clicycle.error(str(e))
        clicycle.info("Please check directory permissions and try again")
        return None
    except Exception as e:
        clicycle.error(f"Failed to create directories: {e}")
        return None


def _check_existing_installation():
    """Check for existing installation and handle accordingly.

    Returns:
        bool | None: True to keep settings, False to replace, None for new install
    """
    install_dir = get_install_dir()

    if not install_dir.exists():
        # No existing installation, check for migration
        _handle_migration()
        return None

    # Existing installation detected
    clicycle.section("Existing Installation Detected")
    clicycle.info("Event Importer is already installed:")
    clicycle.code(f"{install_dir}", language="text", line_numbers=False)

    with clicycle.block():
        try:
            choices = [
                "Reinstall (replace current installation)",
                "Update (preserve settings and data)",
                "Migrate (from another local installation)",
                "Quit",
            ]

            selected_choice = clicycle.select_from_list("option", choices)

            # Map choice text to action
            action_map = {
                "Reinstall (replace current installation)": "reinstall",
                "Update (preserve settings and data)": "update",
                "Migrate (from another local installation)": "migrate",
                "Quit": "quit",
            }
            choice = action_map[selected_choice]

            if choice == "quit":
                clicycle.info("Installation cancelled")
                sys.exit(0)
            elif choice == "migrate":
                _handle_migration()
                return True  # Keep settings after migration
            elif choice == "reinstall":
                clicycle.warning("This will replace your current installation")
                if clicycle.confirm("Are you sure you want to continue?"):
                    # Ask about settings
                    keep_settings = clicycle.confirm(
                        "Do you want to keep your existing settings and API keys?"
                    )
                    if keep_settings:
                        clicycle.info(
                            "Proceeding with reinstallation (keeping settings)"
                        )
                    else:
                        clicycle.info(
                            "Proceeding with reinstallation (replacing settings)"
                        )
                    return keep_settings
                clicycle.info("Installation cancelled")
                sys.exit(0)
            elif choice == "update":
                clicycle.info(
                    "Proceeding with update (settings and data will be preserved)"
                )
                return True

        except (KeyboardInterrupt, EOFError):
            clicycle.info("Installation cancelled")
            sys.exit(0)

    # Default for non-reinstall paths
    return None


def _handle_migration():
    """Handle migration from a previous installation."""
    try:
        if clicycle.confirm("Do you have a previous installation to migrate from?"):
            migration_path = clicycle.prompt(
                "Enter the path to your previous installation"
            )
            if migration_path:
                success, message = migrate_from_path(migration_path)
                if success:
                    clicycle.success(message)
                else:
                    clicycle.warning(f"Migration failed: {message}")
                    clicycle.info("Continuing with fresh setup")
    except (KeyboardInterrupt, EOFError):
        clicycle.info("Skipping migration")


def _configure_api_keys(settings_manager: SettingsService):
    """Configure API keys if needed."""
    missing_keys = get_missing_api_keys(settings_manager)
    if not missing_keys:
        return

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


def _prompt_for_alternate_url() -> str | None:
    """Prompt user for an alternate download URL."""
    try:
        if clicycle.confirm("Would you like to try a different download URL?"):
            return clicycle.prompt("Enter the download URL")
    except (KeyboardInterrupt, EOFError):
        clicycle.info("Installation cancelled by user")
        sys.exit(0)
    return None


async def _attempt_download(
    settings_manager: SettingsService, install_dir: Path
) -> tuple[bool, Path | None]:
    """Attempt to download the application.

    Returns:
        (success, app_path)
    """
    download_url = settings_manager.get("update_url")
    display_download_progress(download_url, install_dir / "event-importer")

    clicycle.info("Starting download...")

    try:
        # Use progress bar properly
        with clicycle.progress("Downloading") as p:
            # Create a callback that updates progress
            def progress_callback(downloaded: int, total: int):
                if total > 0:
                    percent = min(int((downloaded / total) * 100), 100)
                    p.update_progress(percent, f"{downloaded:,} / {total:,} bytes")

            app_path = await download_app(settings_manager, progress_callback)

        if app_path:
            clicycle.success("Download complete")
            return True, app_path
        clicycle.error("Download failed")
        return False, None
    except Exception as e:
        # Show clean error message without traceback
        error_msg = str(e)
        if "RetryError" in error_msg:
            clicycle.error("Download failed after multiple attempts")
        else:
            clicycle.error(f"Download failed: {error_msg}")
        return False, None


async def _download_application(
    settings_manager: SettingsService, install_dir: Path
) -> str | None:
    """Download the application with retry support."""
    set_download_url_if_missing(settings_manager)

    # First attempt
    success, app_path = await _attempt_download(settings_manager, install_dir)
    if success:
        return app_path

    # Offer alternate URL
    new_url = _prompt_for_alternate_url()
    if new_url:
        settings_manager.set("update_url", new_url)
        success, app_path = await _attempt_download(settings_manager, install_dir)
        if success:
            # Ask if they want to keep this URL
            if not clicycle.confirm("Save this URL for future updates?"):
                # Restore original URL
                set_download_url_if_missing(settings_manager)
            return app_path

    clicycle.info("Please check your internet connection and try again")
    return None


def _configure_claude_desktop():
    """Configure Claude Desktop integration."""
    clicycle.section("Claude Desktop Integration")
    claude_config = ClaudeDesktopConfig(is_packaged=True)
    if claude_config.is_claude_desktop_installed():
        clicycle.info("Claude Desktop detected!")
        try:
            if clicycle.confirm(
                "Would you like to configure Claude Desktop integration?"
            ):
                if claude_config.configure_for_packaged():
                    clicycle.success("Claude Desktop configured successfully")
                else:
                    clicycle.warning("Failed to configure Claude Desktop")
        except (KeyboardInterrupt, EOFError):
            clicycle.info("Skipping Claude Desktop configuration")
    else:
        clicycle.info("Claude Desktop not found")


def _validate_installation():
    """Validate the installation."""
    clicycle.section("Validating Installation")
    validator = InstallationValidator()
    is_valid, messages = validator.validate()
    if is_valid:
        clicycle.success("Installation validated successfully")
    else:
        clicycle.warning("Installation completed with warnings:")
        for msg in messages:
            clicycle.warning(f"  - {msg}")


async def run_installer():
    """Run the installation process."""
    _initialize_cli()

    # Check for existing installation first
    keep_settings = _check_existing_installation()

    install_dir = _setup_directories()
    if not install_dir:
        sys.exit(1)

    settings_manager = SettingsService()

    # Handle settings based on user choice
    if keep_settings is False:
        # User chose to replace settings
        clicycle.info("Clearing existing settings...")
        settings_manager.clear_all()
        _configure_api_keys(settings_manager)
    elif keep_settings is None:
        # New install, configure API keys
        _configure_api_keys(settings_manager)
    # else: keep_settings is True, so we skip API key configuration

    app_path = await _download_application(settings_manager, install_dir)
    if not app_path:
        sys.exit(1)

    _configure_claude_desktop()
    display_shell_configuration(app_path)
    _validate_installation()

    clicycle.success("Setup complete")
    clicycle.info(f"Event Importer installed at: {app_path}")
