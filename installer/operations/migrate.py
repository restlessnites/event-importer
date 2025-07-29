"""Migration operation."""

from pathlib import Path

from installer.services.migration_service import MigrationManager


def migrate_from_path(migration_path: str) -> tuple[bool, str]:
    """Migrate from previous installation."""
    migration_manager = MigrationManager()
    return migration_manager.migrate_from_path(Path(migration_path))
