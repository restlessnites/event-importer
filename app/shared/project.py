"""
Provides access to project metadata from pyproject.toml.
"""

import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path


@dataclass
class Project:
    """Container for project metadata."""

    name: str
    version: str


@cache
def get_project() -> Project:
    """
    Get project metadata by parsing pyproject.toml.
    The result is cached for performance.
    """
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    project_name = data.get("project", {}).get("name", "UnknownProject")
    version = data.get("tool", {}).get("poetry", {}).get("version", "0.0.0")

    return Project(name=project_name, version=version)
