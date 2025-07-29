"""Main CLI application for installer."""

import sys

import clicycle

from config.settings import get_setting_info
from installer.cli.display.directories import display_directory_setup
from installer.cli.display.download import (
    create_progress_callback,
    display_download_progress,
)
from installer.cli.display.launch import launch_app
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


def _handle_migration():
    """Handle migration from a previous installation."""
    if clicycle.confirm("Do you have a previous installation to migrate from?"):
        migration_path = clicycle.prompt("Enter the path to your previous installation")
        if migration_path:
            success, message = migrate_from_path(migration_path)
            if success:
                clicycle.success(message)
            else:
                clicycle.warning(f"Migration failed: {message}")
                clicycle.info("Continuing with fresh setup")


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


async def _download_application(
    settings_manager: SettingsService, install_dir
) -> str | None:
    """Download the application."""
    set_download_url_if_missing(settings_manager)
    download_url = settings_manager.get("update_url")
    display_download_progress(download_url, install_dir / "event-importer")
    try:
        progress_callback = create_progress_callback()
        app_path = await download_app(settings_manager, progress_callback)
        if not app_path:
            clicycle.error("Download failed")
            return None
        clicycle.success("Download complete!")
        return app_path
    except Exception as e:
        clicycle.error(f"Download failed: {e}")
        return None


def _configure_claude_desktop():
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


def _validate_installation():
    """Validate the installation."""
    clicycle.section("Validating Installation")
    validator = InstallationValidator()
    is_valid, messages = validator.validate()
    if is_valid:
        clicycle.success("Installation validated successfully!")
    else:
        clicycle.warning("Installation completed with warnings:")
        for msg in messages:
            clicycle.warning(f"  - {msg}")


def _launch_application(app_path):
    """Launch the application if confirmed by the user."""
    clicycle.section("Ready to Launch")
    if clicycle.confirm("Would you like to launch Event Importer now?"):
        launch_app(app_path)
        clicycle.success("Event Importer is launching!")
    else:
        clicycle.info(f"You can launch Event Importer anytime from: {app_path}")


async def run_installer():
    """Run the installation process."""
    _initialize_cli()

    install_dir = _setup_directories()
    if not install_dir:
        sys.exit(1)

    _handle_migration()

    settings_manager = SettingsService()
    _configure_api_keys(settings_manager)

    app_path = await _download_application(settings_manager, install_dir)
    if not app_path:
        sys.exit(1)

    _configure_claude_desktop()
    display_shell_configuration(app_path)
    _validate_installation()
    _launch_application(app_path)

    clicycle.info("Setup complete! You can now close this window.")
