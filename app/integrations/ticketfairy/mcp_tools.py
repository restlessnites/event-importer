"""TicketFairy MCP tools."""

from typing import Any

from mcp.types import Tool

from .submitter import TicketFairySubmitter

# Define MCP tools for TicketFairy
TOOLS: list[Tool] = [
    Tool(
        name="submit_to_ticketfairy",
        description="Submit events to TicketFairy service",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "enum": ["unsubmitted", "failed", "pending", "all"],
                    "default": "unsubmitted",
                    "description": "Filter events to submit",
                },
                "dry_run": {
                    "type": "boolean",
                    "default": False,
                    "description": "Show what would be submitted without actually submitting",
                },
            },
        },
    ),
    Tool(
        name="submit_url_to_ticketfairy",
        description="Submit a specific event URL to TicketFairy",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Event URL to submit"},
                "dry_run": {
                    "type": "boolean",
                    "default": False,
                    "description": "Show what would be submitted without actually submitting",
                },
            },
            "required": ["url"],
        },
    ),
    Tool(
        name="ticketfairy_status",
        description="Get TicketFairy submission status",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="retry_failed_ticketfairy",
        description="Retry failed TicketFairy submissions",
        inputSchema={
            "type": "object",
            "properties": {
                "dry_run": {
                    "type": "boolean",
                    "default": False,
                    "description": "Show what would be retried without actually submitting",
                },
            },
        },
    ),
]


# Tool handlers
async def handle_submit_to_ticketfairy(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle submission to TicketFairy"""
    selector = arguments.get("selector", "unsubmitted")
    dry_run = arguments.get("dry_run", False)

    submitter = TicketFairySubmitter()
    result = await submitter.submit_events(selector, dry_run=dry_run)

    return {"success": True, "data": result}


async def handle_submit_url_to_ticketfairy(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle URL submission to TicketFairy"""
    url = arguments["url"]
    dry_run = arguments.get("dry_run", False)

    submitter = TicketFairySubmitter()
    result = await submitter.submit_by_url(url, dry_run=dry_run)

    return {"success": True, "data": result}


async def handle_ticketfairy_status(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle status request"""
    from sqlalchemy import func

    from ...shared.database.connection import get_db_session
    from ...shared.database.models import EventCache, Submission

    with get_db_session() as db:
        # Get submission counts by status
        status_counts = (
            db.query(Submission.status, func.count(Submission.id))
            .filter(Submission.service_name == "ticketfairy")
            .group_by(Submission.status)
            .all()
        )

        # Get total cached events
        total_events = db.query(func.count(EventCache.id)).scalar()

        # Get unsubmitted count
        submitted_event_ids = (
            db.query(Submission.event_cache_id)
            .filter(Submission.service_name == "ticketfairy")
            .subquery()
        )
        unsubmitted_count = (
            db.query(func.count(EventCache.id))
            .filter(~EventCache.id.in_(submitted_event_ids))
            .scalar()
        )

        status_breakdown = {status: count for status, count in status_counts}

        return {
            "success": True,
            "data": {
                "service": "ticketfairy",
                "total_events": total_events,
                "unsubmitted": unsubmitted_count,
                "status_breakdown": status_breakdown,
            },
        }


async def handle_retry_failed_ticketfairy(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle retry failed submissions"""
    dry_run = arguments.get("dry_run", False)

    submitter = TicketFairySubmitter()
    result = await submitter.submit_events("failed", dry_run=dry_run)

    return {"success": True, "data": result}


# Tool handler mapping
TOOL_HANDLERS = {
    "submit_to_ticketfairy": handle_submit_to_ticketfairy,
    "submit_url_to_ticketfairy": handle_submit_url_to_ticketfairy,
    "ticketfairy_status": handle_ticketfairy_status,
    "retry_failed_ticketfairy": handle_retry_failed_ticketfairy,
}
