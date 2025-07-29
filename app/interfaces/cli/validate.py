"""Validation command implementation."""

import click
import clicycle

from app.validators import InstallationValidator


def run_validation():
    """Validate the installation."""
    try:
        validator = InstallationValidator()
        is_valid, messages = validator.validate()

        if is_valid:
            clicycle.success("Installation is valid")
        else:
            clicycle.error("Installation validation failed:")
            for msg in messages:
                clicycle.error(f"  - {msg}")
            raise click.ClickException("Installation validation failed")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Validation error: {e}") from e
