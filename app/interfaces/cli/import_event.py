"""Import event command implementation."""

import asyncio
import logging

import click
import clicycle

from app.core.router import Router
from app.shared.http import close_http_service


def run_import(url: str, method: str, timeout: int, ignore_cache: bool, verbose: bool):
    """Import an event from a URL."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    async def do_import():
        """Async function to run the import."""
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

    # Show a nice spinner while importing
    with clicycle.spinner("Importing event...") as spinner:
        try:
            result = asyncio.run(do_import())
            spinner.succeed("Event imported successfully!")

            # Display the imported event data
            if result.get("data"):
                event_data = result["data"]
                clicycle.info(f"Event: {event_data.get('title', 'N/A')}")
                clicycle.info(f"Date: {event_data.get('start_datetime', 'N/A')}")
                clicycle.info(f"Venue: {event_data.get('venue_name', 'N/A')}")

        except Exception as e:
            spinner.fail(f"Import failed: {e}")
            raise click.ClickException(str(e)) from e
