"""Error capture system for clean CLI output."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.interfaces.cli.core import CLI


@dataclass
class CapturedError:
    """A captured error/warning message."""

    timestamp: datetime
    level: int
    level_name: str
    logger_name: str
    message: str
    exc_info: str | None = None

    def is_error(self: CapturedError) -> bool:
        """Check if this is an error level message."""
        return self.level >= logging.ERROR

    def is_warning(self: CapturedError) -> bool:
        """Check if this is a warning level message."""
        return self.level == logging.WARNING


class ErrorCapture:
    """Captures log messages for later display."""

    def __init__(self: ErrorCapture) -> None:
        self.captured: list[CapturedError] = []
        self._handler: CaptureHandler | None = None
        self._original_levels: dict[str, int] = {}
        self._loggers_modified: list[logging.Logger] = []

    def start(self: ErrorCapture, min_level: int = logging.WARNING) -> None:
        """Start capturing log messages."""
        if self._handler is not None:
            return  # Already capturing

        # Create and configure handler
        self._handler = CaptureHandler(self)
        self._handler.setLevel(min_level)

        # Key loggers to capture from - ONLY CAPTURE FROM THE TOP-LEVEL 'app' LOGGER
        # to avoid duplicate messages from propagation.
        logger_names = [
            "app",
        ]

        # Add handler and temporarily set appropriate levels
        for logger_name in logger_names:
            logger = logging.getLogger(logger_name)

            # Store original level
            self._original_levels[logger_name] = logger.level

            # Set level to allow warnings/errors to be captured
            # But only if the current level is higher than WARNING
            if logger.level > logging.WARNING:
                logger.setLevel(logging.WARNING)

            # Add our handler
            logger.addHandler(self._handler)
            self._loggers_modified.append(logger)

    def stop(self: ErrorCapture) -> None:
        """Stop capturing and restore original state."""
        if self._handler is None:
            return

        # Remove handler and restore original levels
        for logger in self._loggers_modified:
            logger.removeHandler(self._handler)

            # Restore original level
            original_level = self._original_levels.get(logger.name)
            if original_level is not None:
                logger.setLevel(original_level)

        self._handler = None
        self._loggers_modified = []
        self._original_levels = {}

    def clear(self: ErrorCapture) -> None:
        """Clear captured errors."""
        self.captured.clear()

    def get_errors(self: ErrorCapture) -> list[CapturedError]:
        """Get only error-level messages."""
        return [e for e in self.captured if e.is_error()]

    def get_warnings(self: ErrorCapture) -> list[CapturedError]:
        """Get only warning-level messages."""
        return [e for e in self.captured if e.is_warning()]

    def has_errors(self: ErrorCapture) -> bool:
        """Check if any errors were captured."""
        return any(e.is_error() for e in self.captured)

    def has_warnings(self: ErrorCapture) -> bool:
        """Check if any warnings were captured."""
        return any(e.is_warning() for e in self.captured)

    @contextmanager
    def capture(self: ErrorCapture, min_level: int = logging.WARNING) -> Iterator[None]:
        """Context manager for capturing errors."""
        self.start(min_level)
        try:
            yield
        finally:
            self.stop()

    def async_capture(
        self: ErrorCapture, min_level: int = logging.WARNING
    ) -> Iterator[None]:
        """Async context manager wrapper (just uses sync version)."""
        # Since logging is sync, we can just use the sync context manager
        yield from self.capture(min_level)


class CaptureHandler(logging.Handler):
    """Logging handler that captures messages."""

    def __init__(self: CaptureHandler, capture: ErrorCapture) -> None:
        super().__init__()
        self.capture = capture

    def emit(self: CaptureHandler, record: logging.LogRecord) -> None:
        """Capture a log record."""
        # Format the message
        try:
            message = self.format(record)
        except (ValueError, TypeError, KeyError):
            message = record.getMessage()

        # Extract exception info if present
        exc_info = None
        if record.exc_info:
            import traceback

            exc_info = "".join(traceback.format_exception(*record.exc_info))

        # Create captured error
        error = CapturedError(
            timestamp=datetime.fromtimestamp(record.created),
            level=record.levelno,
            level_name=record.levelname,
            logger_name=record.name,
            message=message,
            exc_info=exc_info,
        )

        self.capture.captured.append(error)


class CLIErrorDisplay:
    """Display captured errors in the CLI."""

    def __init__(self: CLIErrorDisplay, cli: CLI) -> None:
        """Initialize with CLI instance."""
        self.cli = cli

    def show_captured_errors(
        self: CLIErrorDisplay, capture: ErrorCapture, title: str = "Captured Errors"
    ) -> None:
        """Display captured errors in a nice format."""
        errors = capture.get_errors()
        warnings = capture.get_warnings()

        if not errors and not warnings:
            return

        # Section header
        self.cli.console.print()
        self.cli.section(title)

        # Show warnings first
        if warnings:
            self._show_messages(warnings, "Warnings", "warning")

        # Show errors
        if errors:
            if warnings:
                self.cli.console.print()  # Space between sections
            self._show_messages(errors, "Errors", "error")

    def _show_messages(
        self: CLIErrorDisplay, messages: list[CapturedError], label: str, style: str
    ) -> None:
        """Show a group of messages."""
        self.cli.console.print(
            f"[{self.cli.theme.typography.label_style}]{label}:[/] {len(messages)} found"
        )
        self.cli.console.print()

        for i, error in enumerate(messages, 1):
            # Clean up the message
            msg = self._clean_message(error.message)

            # Show timestamp and logger
            meta = f"[{self.cli.theme.typography.dim_style}]{error.timestamp.strftime('%H:%M:%S')} | {error.logger_name}[/]"

            # Main message
            icon = (
                self.cli.theme.icons.warning
                if style == "warning"
                else self.cli.theme.icons.error
            )
            style_name = (
                self.cli.theme.typography.warning_style
                if style == "warning"
                else self.cli.theme.typography.error_style
            )
            self.cli.console.print(f"{icon} [{style_name}]{msg}[/]")
            self.cli.console.print(f"  {meta}")

            # Exception details if present
            if error.exc_info:
                self.cli.console.print()
                self.cli.code(error.exc_info, "python", "Exception Details")

            if i < len(messages):
                self.cli.console.print()  # Space between errors

    def _clean_message(self: CLIErrorDisplay, message: str) -> str:
        """Clean up error messages for display."""
        import re

        # Remove timestamps that might be in the message
        message = re.sub(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ - ", "", message)
        message = re.sub(r"^\[\d{2}:\d{2}:\d{2}\] ", "", message)

        # Remove logger names and level prefixes
        message = re.sub(r"^[\w\.]+\s+-\s+\w+\s+-\s+", "", message)
        message = re.sub(r"^[\w\.]+ - \w+ - ", "", message)

        # Clean up common patterns
        message = message.replace("ERROR - ", "").replace("WARNING - ", "")
        message = message.replace("INFO - ", "").replace("DEBUG - ", "")

        # Remove redundant error indicators
        message = re.sub(r"^(Error|Warning|Info):\s*", "", message, flags=re.IGNORECASE)

        # Clean up security page messages
        message = re.sub(r"Security page blocking import for [^:]+: ", "", message)
        message = re.sub(r"Security page detected for [^:]+: ", "", message)

        # Make first letter uppercase if it's not already
        message = message.strip()
        if message and message[0].islower():
            message = message[0].upper() + message[1:]

        return message


# Global instance for CLI use
_error_capture: ErrorCapture | None = None


def get_error_capture() -> ErrorCapture:
    """Get the global error capture instance."""
    global _error_capture
    if _error_capture is None:
        _error_capture = ErrorCapture()
    return _error_capture
