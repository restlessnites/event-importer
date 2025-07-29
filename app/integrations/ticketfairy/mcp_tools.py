"""TicketFairy MCP tools."""

from __future__ import annotations

from typing import Any

from mcp import types

from app.integrations.ticketfairy.submitter import TicketFairySubmitter


async def handle_submit_ticketfairy(arguments: dict) -> dict[str, Any]:
    """Handle the call to submit an event to TicketFairy."""
    url = arguments.get("url")
    if not url:
        return {"success": False, "error": "URL is required"}

    dry_run = arguments.get("dry_run", False)
    submitter = TicketFairySubmitter()
    return await submitter.submit_by_url(url, dry_run=dry_run)


TOOLS = [
    types.Tool(
        name="submit_ticketfairy",
        description="Submit an event to TicketFairy from a URL",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the event page to submit",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If True, don't actually submit",
                    "default": False,
                },
            },
            "required": ["url"],
        },
    ),
]

TOOL_HANDLERS = {
    "submit_ticketfairy": handle_submit_ticketfairy,
}
