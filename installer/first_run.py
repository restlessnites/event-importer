"""First run detection and installer launch."""


from installer.paths import get_user_data_dir


def is_first_run() -> bool:
    """Check if this is the first run of the application."""
    config_path = get_user_data_dir() / "config.json"
    return not config_path.exists()


def should_run_installer() -> bool:
    """Determine if the installer should run."""
    return is_first_run()
