"""A script to synchronize the version from pyproject.toml to app/version.py."""

import re
from pathlib import Path


def sync_version():
    """Read the version from pyproject.toml and write it to app/version.py."""

    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    version_file_path = Path(__file__).parent.parent / "app" / "version.py"

    # Read version from pyproject.toml
    pyproject_content = pyproject_path.read_text()

    # A simple regex to find the version string
    match = re.search(r"version\s*=\s*\"(.*?)\"", pyproject_content)
    if not match:
        raise RuntimeError("Version not found in pyproject.toml")

    version = match.group(1)

    # Write version to app/version.py
    version_file_path.write_text(f'__version__ = "{version}"\n')

    print(f"Version {version} synchronized to {version_file_path}")


if __name__ == "__main__":
    sync_version()
