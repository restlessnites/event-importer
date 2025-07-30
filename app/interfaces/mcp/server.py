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
from app.services.integration_discovery import get_available_integrations
from app.shared.database.connection import get_db_session, init_db
from app.shared.database.models import EventCache
from app.shared.http import close_http_service
from app.shared.service_errors import ServiceErrorFormatter
from app.shared.statistics import StatisticsService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
        types.Tool(
            name="rebuild_event_description",
            description="Rebuild a specific description for an event (preview only - does not save). The regenerated description will be returned for review. Use the update_event tool to save changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to rebuild description for",
                    },
                    "description_type": {
                        "type": "string",
                        "enum": ["short", "long"],
                        "description": "Which description to regenerate: 'short' or 'long'",
                    },
                    "supplementary_context": {
                        "type": "string",
                        "description": "Additional context to help regenerate the description (e.g., 'focus on the venue' or 'emphasize the artists')",
                        "maxLength": 1000,
                    },
                },
                "required": ["event_id", "description_type"],
            },
        ),
        types.Tool(
            name="update_event",
            description="Update specific fields of an event. Use this after previewing changes with rebuild_event_description. IMPORTANT: Dates use YYYY-MM-DD format. Times use 24-hour HH:MM format. For multi-day events, set both date and end_date. The time object must include start, end, and timezone (IANA format like 'America/Los_Angeles'). Short descriptions should be concise summaries under 100 characters (max 200). Arrays like genres and lineup replace the entire list.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to update",
                    },
                    "title": {
                        "type": "string",
                        "description": "Event title",
                    },
                    "venue": {
                        "type": "string",
                        "description": "Venue name",
                    },
                    "date": {
                        "type": "string",
                        "description": "Event start date in YYYY-MM-DD format",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Event end date for multi-day events in YYYY-MM-DD format",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "time": {
                        "type": "object",
                        "description": "Event time information",
                        "properties": {
                            "start": {
                                "type": "string",
                                "description": "Start time in HH:MM format (e.g., '19:00')",
                                "pattern": "^\\d{2}:\\d{2}$",
                            },
                            "end": {
                                "type": "string",
                                "description": "End time in HH:MM format (e.g., '23:00')",
                                "pattern": "^\\d{2}:\\d{2}$",
                            },
                            "timezone": {
                                "type": "string",
                                "description": "IANA timezone identifier (e.g., 'America/Los_Angeles', 'America/New_York', 'Europe/London', 'Asia/Tokyo'). Must be a valid timezone from the IANA Time Zone Database. Use the exact format with continent/city.",
                            },
                        },
                    },
                    "short_description": {
                        "type": "string",
                        "description": "Short event description (aim for under 100 characters, max 200)",
                        "maxLength": 200,
                    },
                    "long_description": {
                        "type": "string",
                        "description": "Detailed event description",
                    },
                    "genres": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of music genres",
                    },
                    "lineup": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of artists/performers",
                    },
                    "minimum_age": {
                        "type": "string",
                        "description": "Minimum age requirement (e.g., '18+', '21+', 'All Ages')",
                    },
                    "cost": {
                        "type": "string",
                        "description": "Ticket cost information (e.g., '$20', 'Free', '$15-30')",
                    },
                },
                "required": ["event_id"],
            },
        ),
    ]

    @staticmethod
    def format_event_data(event_data: dict) -> dict:
        """Format event data for display"""
        return {
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

    @staticmethod
    async def handle_import_event(arguments: dict, router: Router) -> dict:
        """Handle import_event tool call"""
        try:
            result = await router.route_request(arguments)

            # Format service failures for user-friendly display
            ServiceErrorFormatter.format_for_mcp(result)

            # Ensure we have a proper error response if import failed
            if not result.get("success", False):
                return {
                    "success": False,
                    "error": result.get("error", "Import failed"),
                    "method_used": result.get("method_used"),
                    "service_failures": result.get("service_failures", []),
                    "service_failure_summary": result.get("service_failure_summary"),
                }
            return result
        except Exception as e:
            logger.exception("Error in handle_import_event")
            return {
                "success": False,
                "error": f"{e.__class__.__name__}: {str(e)}",
            }

    @staticmethod
    async def handle_rebuild_event_description(arguments: dict, router: Router) -> dict:
        """Handle rebuild_event_description tool call"""
        event_id = arguments.get("event_id")
        if not event_id:
            return {"success": False, "error": "Event ID is required"}

        description_type = arguments.get("description_type")
        if not description_type or description_type not in ["short", "long"]:
            return {
                "success": False,
                "error": "description_type must be 'short' or 'long'",
            }

        try:
            # Get supplementary context if provided
            supplementary_context = arguments.get("supplementary_context")
            updated_event = await router.importer.rebuild_description(
                event_id,
                description_type=description_type,
                supplementary_context=supplementary_context,
            )

            if updated_event:
                return {
                    "success": True,
                    "event_id": event_id,
                    "message": f"{description_type.capitalize()} description regenerated (preview only)",
                    "updated_data": updated_event.model_dump(mode="json"),
                }
            return {
                "success": False,
                "event_id": event_id,
                "error": f"Event with ID {event_id} not found in cache",
            }
        except Exception as e:
            logger.exception(f"Error rebuilding description for event {event_id}")
            return {
                "success": False,
                "event_id": event_id,
                "error": f"{e.__class__.__name__}: {str(e)}",
            }

    @staticmethod
    async def handle_update_event(arguments: dict, router: Router) -> dict:
        """Handle update_event tool call"""
        event_id = arguments.get("event_id")
        if not event_id:
            return {"success": False, "error": "Event ID is required"}

        # Extract updateable fields
        allowed_fields = {
            "title",
            "venue",
            "date",
            "end_date",
            "time",
            "short_description",
            "long_description",
            "genres",
            "lineup",
            "minimum_age",
            "cost",
        }

        updates = {
            k: v for k, v in arguments.items() if k in allowed_fields and v is not None
        }

        if not updates:
            return {"success": False, "error": "No valid fields provided to update"}

        try:
            updated_event = await router.importer.update_event(event_id, updates)

            if updated_event:
                return {
                    "success": True,
                    "event_id": event_id,
                    "message": f"Successfully updated {len(updates)} field(s)",
                    "updated_fields": list(updates.keys()),
                    "updated_data": updated_event.model_dump(mode="json"),
                }
            return {
                "success": False,
                "event_id": event_id,
                "error": f"Event with ID {event_id} not found in cache",
            }
        except Exception as e:
            logger.exception(f"Error updating event {event_id}")
            return {
                "success": False,
                "event_id": event_id,
                "error": f"{e.__class__.__name__}: {str(e)}",
            }

    @staticmethod
    def _build_list_events_query(db_session, arguments: dict):
        """Build the query for listing events based on arguments."""
        query = db_session.query(EventCache)

        if search := arguments.get("search"):
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    EventCache.source_url.like(search_term),
                    EventCache.scraped_data.like(search_term),
                ),
            )

        sort_map = {
            "date": EventCache.scraped_at,
            "url": EventCache.source_url,
        }
        sort_field = arguments.get("sort", "date")
        sort_order = arguments.get("order", "desc")
        order_direction = desc if sort_order == "desc" else asc

        if sort_column := sort_map.get(sort_field):
            query = query.order_by(order_direction(sort_column))

        if limit := arguments.get("limit"):
            query = query.limit(limit)

        return query

    @staticmethod
    def _format_list_event(event: EventCache, summary_only: bool) -> dict:
        """Format a single event for the list view."""
        event_info = {
            "id": event.id,
            "source_url": event.source_url,
            "scraped_at": event.scraped_at.isoformat() if event.scraped_at else None,
            "updated_at": event.updated_at.isoformat() if event.updated_at else None,
            "data_hash": event.data_hash,
        }

        if summary_only:
            event_info.update(CoreMCPTools.format_event_data(event.scraped_data))
        else:
            event_info["event_data"] = event.scraped_data

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
        return event_info

    @staticmethod
    async def handle_list_events(arguments: dict) -> dict:
        """Handle list_events tool call"""
        with get_db_session() as db:
            query = CoreMCPTools._build_list_events_query(db, arguments)
            events = query.all()

            if not events:
                return {"success": True, "events": [], "message": "No events found"}

            summary_only = arguments.get("summary_only", False)
            formatted_events = [
                CoreMCPTools._format_list_event(event, summary_only) for event in events
            ]

            result = {
                "success": True,
                "events": formatted_events,
                "total": len(formatted_events),
            }

            if limit := arguments.get("limit"):
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
        "rebuild_event_description": handle_rebuild_event_description.__func__,
        "update_event": handle_update_event.__func__,
    }


def get_all_tools() -> list[types.Tool]:
    """Get all available tools including integration tools"""
    logger.info("Getting all tools...")
    # Start with core tools
    tools = CoreMCPTools.TOOLS.copy()
    logger.info(f"Core tools: {[tool.name for tool in tools]}")

    # Add integration tools
    integrations = get_available_integrations()
    logger.info(f"Discovered integrations: {list(integrations.keys())}")
    for name, integration_class in integrations.items():
        logger.info(f"Loading tools for integration: {name}")
        integration = integration_class()
        mcp_tools = integration.get_mcp_tools()
        if mcp_tools and hasattr(mcp_tools, "TOOLS"):
            logger.info(f"Adding MCP tools for integration: {name}")
            tools.extend(mcp_tools.TOOLS)
        else:
            logger.warning(f"No MCP tools found for integration: {name}")

    logger.info(f"All tools: {[tool.name for tool in tools]}")
    return tools


def get_all_tool_handlers() -> dict:
    """Get all tool handlers including integration handlers"""
    # Start with core handlers
    handlers = CoreMCPTools.TOOL_HANDLERS.copy()

    # Add integration tool handlers
    integrations = get_available_integrations()
    for _name, integration_class in integrations.items():
        integration = integration_class()
        mcp_tools = integration.get_mcp_tools()
        if mcp_tools and hasattr(mcp_tools, "TOOL_HANDLERS"):
            handlers.update(mcp_tools.TOOL_HANDLERS)

    return handlers


async def handle_call_tool(
    name: str,
    arguments: dict[str, Any],
    router: Router,
    all_handlers: dict[str, Any],
) -> list[types.TextContent]:
    """Handle tool calls."""
    try:
        # Special case for import_event (needs router)
        if name == "import_event":
            result = await CoreMCPTools.handle_import_event(arguments, router)
        # Handle rebuild separately as it needs the router instance
        elif name == "rebuild_event_description":
            result = await CoreMCPTools.handle_rebuild_event_description(
                arguments, router
            )
        # Handle update_event which also needs router
        elif name == "update_event":
            result = await CoreMCPTools.handle_update_event(arguments, router)
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


async def main() -> None:
    """Main entry point for the MCP server."""
    logger.info(f"Starting Event Importer MCP Server v{__version__}")

    # Initialize database
    init_db()

    # Validate configuration
    try:
        config = get_config()
        features = config.get_enabled_features()
        integrations = config.get_enabled_integrations()
        logger.info(f"Enabled features: {features}")
        if integrations:
            logger.info(f"Enabled integrations: {integrations}")
    except (ValueError, TypeError, KeyError):
        logger.exception(CommonMessages.CONFIGURATION_ERROR)
        sys.exit(1)

    # Create server and router
    server = Server("event-importer")
    router = Router()

    # Get all tools and handlers
    tools = get_all_tools()
    all_handlers = get_all_tool_handlers()

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        """Return the list of available tools."""
        return tools

    @server.call_tool()
    async def call_tool_wrapper(
        name: str,
        arguments: dict[str, Any],
    ) -> list[types.TextContent]:
        """Wrapper to call the tool handler with necessary context."""
        return await handle_call_tool(name, arguments, router, all_handlers)

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
