"""MCP server implementation for the event importer."""

import asyncio
import json
import logging
import sys
from typing import Any

import mcp.server.stdio
from mcp import types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from sqlalchemy import asc, desc, or_

from app import __version__
from app.config import get_config
from app.core.router import Router
from app.error_messages import CommonMessages, InterfaceMessages
from app.integrations import get_available_integrations
from app.shared.database.connection import get_db_session, init_db
from app.shared.database.models import EventCache
from app.shared.http import close_http_service
from app.shared.statistics import StatisticsService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)




# Core MCP Tools and Handlers
class CoreMCPTools:
    """Core MCP tools for event management"""

    TOOLS = [
        types.Tool(
            name="import_event",
            description="Import structured event information from a URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the event page to import",
                    },
                    "force_method": {
                        "type": "string",
                        "enum": ["api", "web", "image"],
                        "description": "Force a specific import method",
                    },
                    "include_raw_data": {
                        "type": "boolean",
                        "description": "Include raw extracted data in response",
                        "default": False,
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 60)",
                        "default": 60,
                        "minimum": 1,
                        "maximum": 300,
                    },
                    "ignore_cache": {
                        "type": "boolean",
                        "description": "Skip cache and force fresh import",
                        "default": False,
                    },
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="list_events",
            description="List imported events with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results (optional - shows all by default)",
                    },
                    "search": {
                        "type": "string",
                        "description": "Search term for URL or event data",
                    },
                    "sort": {
                        "type": "string",
                        "enum": ["date", "url"],
                        "default": "date",
                        "description": "Sort by field",
                    },
                    "order": {
                        "type": "string",
                        "enum": ["asc", "desc"],
                        "default": "desc",
                        "description": "Sort order",
                    },
                    "summary_only": {
                        "type": "boolean",
                        "default": False,
                        "description": "Show only summary data instead of full event details",
                    },
                },
            },
        ),
        types.Tool(
            name="show_event",
            description="Show detailed information for a specific event",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Event ID to show"},
                },
                "required": ["event_id"],
            },
        ),
        types.Tool(
            name="get_statistics",
            description="Get database statistics and analytics",
            inputSchema={
                "type": "object",
                "properties": {
                    "detailed": {
                        "type": "boolean",
                        "default": False,
                        "description": "Include detailed breakdown",
                    },
                },
            },
        ),
    ]

    @staticmethod
    def format_event_data(event_data: dict) -> dict:
        """Format event data for display"""
        formatted = {
            "title": event_data.get("title", "N/A"),
            "venue": event_data.get("venue", "N/A"),
            "date": event_data.get("date", "N/A"),
            "time": event_data.get("time", {}).get("start", "N/A")
            if isinstance(event_data.get("time"), dict)
            else "N/A",
            "city": event_data.get("location", {}).get("city", "N/A")
            if isinstance(event_data.get("location"), dict)
            else "N/A",
            "genres": ", ".join(event_data.get("genres", []))
            if event_data.get("genres")
            else "N/A",
            "cost": event_data.get("cost", "N/A"),
        }
        return formatted

    @staticmethod
    async def handle_import_event(arguments: dict, router: Router) -> dict:
        """Handle import_event tool call"""
        return await router.route_request(arguments)

    @staticmethod
    async def handle_list_events(arguments: dict) -> dict:
        """Handle list_events tool call"""
        with get_db_session() as db:
            # Build query
            query = db.query(EventCache)

            # Apply search filter
            if arguments.get("search"):
                search_term = f"%{arguments['search']}%"
                query = query.filter(
                    or_(
                        EventCache.source_url.like(search_term),
                        EventCache.scraped_data.like(search_term),
                    ),
                )

            # Apply sorting
            sort_field = arguments.get("sort", "date")
            sort_order = arguments.get("order", "desc")

            if sort_field == "date":
                if sort_order == "desc":
                    query = query.order_by(desc(EventCache.scraped_at))
                else:
                    query = query.order_by(asc(EventCache.scraped_at))
            elif sort_field == "url":
                if sort_order == "desc":
                    query = query.order_by(desc(EventCache.source_url))
                else:
                    query = query.order_by(asc(EventCache.source_url))

            # Apply limit only if specified
            limit = arguments.get("limit")
            if limit:
                query = query.limit(limit)

            events = query.all()

            if not events:
                return {"success": True, "events": [], "message": "No events found"}

            # Format events
            formatted_events = []
            summary_only = arguments.get("summary_only", False)

            for event in events:
                event_info = {
                    "id": event.id,
                    "source_url": event.source_url,
                    "scraped_at": event.scraped_at.isoformat()
                    if event.scraped_at
                    else None,
                    "updated_at": event.updated_at.isoformat()
                    if event.updated_at
                    else None,
                    "data_hash": event.data_hash,
                }

                if summary_only:
                    # Show only formatted summary
                    event_info.update(
                        CoreMCPTools.format_event_data(event.scraped_data),
                    )
                else:
                    # Include full event data by default
                    event_info["event_data"] = event.scraped_data

                # Always include submission info
                if event.submissions:
                    event_info["submissions"] = [
                        {
                            "id": sub.id,
                            "service": sub.service_name,
                            "status": sub.status,
                            "submitted_at": sub.submitted_at.isoformat()
                            if sub.submitted_at
                            else None,
                            "retry_count": sub.retry_count,
                            "error_message": sub.error_message,
                        }
                        for sub in event.submissions
                    ]
                else:
                    event_info["submissions"] = []

                formatted_events.append(event_info)

            result = {
                "success": True,
                "events": formatted_events,
                "total": len(formatted_events),
            }

            # Only include limit info if it was applied
            if limit:
                result["limit_applied"] = limit

            return result

    @staticmethod
    async def handle_show_event(arguments: dict) -> dict:
        """Handle show_event tool call"""
        event_id = arguments["event_id"]

        with get_db_session() as db:
            event = db.query(EventCache).filter(EventCache.id == event_id).first()

            if not event:
                return {
                    "success": False,
                    "error": f"Event with ID {event_id} not found",
                }

            event_info = {
                "id": event.id,
                "source_url": event.source_url,
                "scraped_at": event.scraped_at.isoformat()
                if event.scraped_at
                else None,
                "updated_at": event.updated_at.isoformat()
                if event.updated_at
                else None,
                "data_hash": event.data_hash,
                "event_data": event.scraped_data,
            }

            # Add submission info
            if event.submissions:
                event_info["submissions"] = [
                    {
                        "id": sub.id,
                        "service": sub.service_name,
                        "status": sub.status,
                        "submitted_at": sub.submitted_at.isoformat()
                        if sub.submitted_at
                        else None,
                        "retry_count": sub.retry_count,
                        "error_message": sub.error_message,
                    }
                    for sub in event.submissions
                ]
            else:
                event_info["submissions"] = []

            return {"success": True, "event": event_info}

    @staticmethod
    async def handle_get_statistics(arguments: dict) -> dict:
        """Handle get_statistics tool call"""
        try:
            stats_service = StatisticsService()

            if arguments.get("detailed", False):
                # Get detailed statistics with trends
                stats = stats_service.get_detailed_statistics()
            else:
                # Get combined statistics
                stats = stats_service.get_combined_statistics()

            return {"success": True, "statistics": stats}

        except (ValueError, TypeError, KeyError) as e:
            error_msg = f"{InterfaceMessages.STATISTICS_ERROR}: {e!s}"
            return {"success": False, "error": error_msg}

    # Tool handlers mapping
    TOOL_HANDLERS = {
        "list_events": handle_list_events.__func__,
        "show_event": handle_show_event.__func__,
        "get_statistics": handle_get_statistics.__func__,
    }


def get_all_tools() -> list[types.Tool]:
    """Get all available tools including integration tools"""
    # Start with core tools
    tools = CoreMCPTools.TOOLS.copy()

    # Add integration tools
    integrations = get_available_integrations()
    for name, integration in integrations.items():
        if hasattr(integration, "mcp_tools") and hasattr(
            integration.mcp_tools, "TOOLS",
        ):
            logger.info(f"Adding MCP tools for integration: {name}")
            tools.extend(integration.mcp_tools.TOOLS)

    return tools


def get_all_tool_handlers() -> dict:
    """Get all tool handlers including integration handlers"""
    # Start with core handlers
    handlers = CoreMCPTools.TOOL_HANDLERS.copy()

    # Add integration tool handlers
    integrations = get_available_integrations()
    for _name, integration in integrations.items():
        if hasattr(integration, "mcp_tools") and hasattr(
            integration.mcp_tools, "TOOL_HANDLERS",
        ):
            handlers.update(integration.mcp_tools.TOOL_HANDLERS)

    return handlers


async def main() -> None:
    """Main entry point for the MCP server."""
    logger.info(f"Starting Event Importer MCP Server v{__version__}")

    # Initialize database
    init_db()

    # Validate configuration
    try:
        config = get_config()
        features = config.get_enabled_features()
        logger.info(f"Enabled features: {features}")
    except (ValueError, TypeError, KeyError):
        logger.exception(CommonMessages.CONFIGURATION_ERROR)
        sys.exit(1)

    # Create server and router
    server = Server("event-importer")
    router = Router()

    # Get all tools and handlers
    all_tools = get_all_tools()
    all_handlers = get_all_tool_handlers()

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available tools."""
        return all_tools

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any],
    ) -> list[types.TextContent]:
        """Handle tool calls."""
        try:
            # Special case for import_event (needs router)
            if name == "import_event":
                result = await CoreMCPTools.handle_import_event(arguments, router)
            # Check if it's in our handlers (core + integration)
            elif name in all_handlers:
                result = await all_handlers[name](arguments)
            else:
                error_msg = f"Unknown tool: {name}"
                raise ValueError(error_msg)

            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except (ValueError, TypeError, KeyError) as e:
            logger.exception(InterfaceMessages.TOOL_CALL_ERROR)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": str(e)}, indent=2),
                ),
            ]

    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        try:
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="event-importer",
                    server_version=__version__,
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
        finally:
            # Cleanup
            await close_http_service()


def run() -> None:
    """Entry point for the MCP server script."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
