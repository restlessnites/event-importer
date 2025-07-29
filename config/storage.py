"""
SQLite-based settings storage.
Keeps settings in a separate table from events data.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from config.settings import get_all_settings
from installer.paths import get_user_data_dir


class SettingsStorage:
    """SQLite-based key-value storage for application settings."""

    def __init__(self, db_path: Path | None = None):
        """Initialize settings storage.

        Args:
            db_path: Path to SQLite database. If None, uses default location.
        """
        if db_path is None:
            # Use the same events.db but separate table
            db_path = get_user_data_dir() / "events.db"

        self.db_path = db_path
        self._ensure_table()

    def _ensure_table(self):
        """Ensure the settings table exists and is initialized with default values."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

        # Initialize with all settings from Pydantic model
        all_settings = get_all_settings()

        with sqlite3.connect(self.db_path) as conn:
            for key, info in all_settings.items():
                # Insert with default value (empty string) if not exists
                conn.execute("""
                    INSERT OR IGNORE INTO app_settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                """, (key, info.default or "", datetime.now().isoformat()))
            conn.commit()

    def get(self, key: str) -> str | None:
        """Get a setting value."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        """Set a setting value."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO app_settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now().isoformat()))
            conn.commit()

    def get_all(self) -> dict[str, str]:
        """Get all settings as a dictionary."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT key, value FROM app_settings")
            return dict(cursor.fetchall())

    def delete(self, key: str) -> None:
        """Delete a setting."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))
            conn.commit()

    def clear_all(self) -> None:
        """Clear all settings (use with caution)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM app_settings")
            conn.commit()

    def export_json(self) -> str:
        """Export all settings as JSON."""
        return json.dumps(self.get_all(), indent=2)

    def import_json(self, json_str: str) -> None:
        """Import settings from JSON."""
        data = json.loads(json_str)
        for key, value in data.items():
            self.set(key, value)

    def migrate_from_json_file(self, json_path: Path) -> bool:
        """Migrate settings from a JSON file."""
        if not json_path.exists():
            return False

        try:
            with json_path.open() as f:
                data = json.load(f)

            # Import all key-value pairs
            for key, value in data.items():
                if isinstance(value, str):
                    self.set(key, value)
                else:
                    # Convert non-string values to JSON
                    self.set(key, json.dumps(value))

            return True
        except Exception:
            return False
