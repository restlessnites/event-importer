"""Import event command implementation."""

import asyncio
import logging

import click
import clicycle

from app.core.router import Router
from app.shared.http import close_http_service
from app.shared.service_errors import ServiceErrorFormatter


def _display_event_info(event_data: dict) -> None:
    """Display basic event information."""
    clicycle.info(f"Event: {event_data.get('title', 'N/A')}")
    clicycle.info(f"Date: {event_data.get('date', 'N/A')}")
    clicycle.info(f"Venue: {event_data.get('venue', 'N/A')}")


def _display_service_failures(service_failures: list) -> None:
    """Display service failure messages."""
    failure_msgs = ServiceErrorFormatter.format_for_cli(service_failures)
    if failure_msgs:
        clicycle.warning("\nSome optional services were not available:")
        for msg in failure_msgs:
            clicycle.list_item(msg)


async def _perform_import(url: str, method: str, timeout: int, ignore_cache: bool):
    """Perform the actual import operation."""
    try:
        router = Router()
        request_data = {
            "url": url,
            "timeout": timeout,
            "ignore_cache": ignore_cache,
        }
        if method:
            request_data["force_method"] = method

        result = await router.route_request(request_data)

        if not result:
            raise Exception("No result returned")

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            raise Exception(error_msg)

        return result

    finally:
        await close_http_service()


def run_import(url: str, method: str, timeout: int, ignore_cache: bool, verbose: bool):
    """Import an event from a URL."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Show a nice spinner while importing
    try:
        with clicycle.spinner("Importing event..."):
            result = asyncio.run(_perform_import(url, method, timeout, ignore_cache))

        clicycle.success("Event imported successfully!")

        # Display the imported event data
        if result.get("data"):
            _display_event_info(result["data"])

        # Display service failures if any
        if result.get("service_failures"):
            _display_service_failures(result["service_failures"])

    except Exception as e:
        clicycle.error(f"Import failed: {e}")
        raise click.ClickException(str(e)) from e
