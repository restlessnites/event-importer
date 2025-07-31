from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp import types

from app.interfaces.mcp.server import (
    CoreMCPTools,
    get_all_tool_handlers,
    get_all_tools,
    handle_call_tool,
)


@pytest.fixture
def mock_db_session():
    """Fixture for a mock database session."""
    with patch("app.interfaces.mcp.server.get_db_session") as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        yield mock_session


def test_format_event_data_full():
    """Test format_event_data with a full data set."""
    event_data = {
        "title": "Test Event",
        "venue": "Test Venue",
        "date": "2024-01-01",
        "time": {"start": "20:00"},
        "location": {"city": "Test City"},
        "genres": ["Rock", "Pop"],
        "cost": "25.00",
    }
    formatted = CoreMCPTools.format_event_data(event_data)
    assert formatted == {
        "title": "Test Event",
        "venue": "Test Venue",
        "date": "2024-01-01",
        "time": "20:00",
        "city": "Test City",
        "genres": "Rock, Pop",
        "cost": "25.00",
    }


def test_format_event_data_partial():
    """Test format_event_data with partial data."""
    event_data = {"title": "Test Event", "venue": "Test Venue"}
    formatted = CoreMCPTools.format_event_data(event_data)
    assert formatted == {
        "title": "Test Event",
        "venue": "Test Venue",
        "date": "N/A",
        "time": "N/A",
        "city": "N/A",
        "genres": "N/A",
        "cost": "N/A",
    }


def test_format_event_data_empty():
    """Test format_event_data with empty data."""
    event_data = {}
    formatted = CoreMCPTools.format_event_data(event_data)
    assert formatted == {
        "title": "N/A",
        "venue": "N/A",
        "date": "N/A",
        "time": "N/A",
        "city": "N/A",
        "genres": "N/A",
        "cost": "N/A",
    }


def test_format_event_data_malformed():
    """Test format_event_data with malformed nested data."""
    event_data = {
        "title": "Malformed Event",
        "time": "Invalid Time",
        "location": "Invalid Location",
        "genres": [],
    }
    formatted = CoreMCPTools.format_event_data(event_data)
    assert formatted["time"] == "N/A"
    assert formatted["city"] == "N/A"
    assert formatted["genres"] == "N/A"


@pytest.mark.asyncio
async def test_handle_import_event():
    """Test the handle_import_event method."""
    mock_router = AsyncMock()
    mock_router.route_request.return_value = {"success": True, "status": "success"}
    arguments = {"url": "http://example.com"}

    result = await CoreMCPTools.handle_import_event(arguments, mock_router)

    mock_router.route_request.assert_awaited_once_with(arguments)
    assert result == {"success": True, "status": "success"}


@pytest.mark.asyncio
async def test_handle_rebuild_event_description_success():
    """Test handle_rebuild_event_description on success."""
    mock_router = AsyncMock()
    mock_event = MagicMock()
    mock_event.model_dump.return_value = {
        "id": 1,
        "short_description": "New short description",
    }
    mock_router.importer.rebuild_description.return_value = mock_event
    arguments = {"event_id": 1, "description_type": "short"}

    result = await CoreMCPTools.handle_rebuild_event_description(arguments, mock_router)

    mock_router.importer.rebuild_description.assert_awaited_once_with(
        1, description_type="short", supplementary_context=None
    )
    assert result == {
        "success": True,
        "event_id": 1,
        "message": "Short description regenerated (preview only)",
        "updated_data": {"id": 1, "short_description": "New short description"},
    }


@pytest.mark.asyncio
async def test_handle_rebuild_event_description_failure():
    """Test handle_rebuild_event_description on failure."""
    mock_router = AsyncMock()
    mock_router.importer.rebuild_description.return_value = None
    arguments = {"event_id": 1, "description_type": "long"}

    result = await CoreMCPTools.handle_rebuild_event_description(arguments, mock_router)

    assert result == {
        "success": False,
        "event_id": 1,
        "error": "Event with ID 1 not found in cache",
    }


@pytest.mark.asyncio
async def test_handle_rebuild_event_description_no_id():
    """Test handle_rebuild_event_description with no event_id."""
    mock_router = AsyncMock()
    result = await CoreMCPTools.handle_rebuild_event_description({}, mock_router)
    assert result == {"success": False, "error": "Event ID is required"}


@pytest.mark.asyncio
async def test_handle_show_event_found(mock_db_session):
    """Test handle_show_event when an event is found."""
    mock_event = MagicMock()
    mock_event.id = 1
    mock_event.source_url = "http://example.com"
    mock_event.scraped_at = None
    mock_event.updated_at = None
    mock_event.data_hash = "12345"
    mock_event.scraped_data = {"title": "Test Event"}
    mock_event.submissions = []

    mock_db_session.query.return_value.filter.return_value.first.return_value = (
        mock_event
    )
    arguments = {"event_id": 1}

    result = await CoreMCPTools.handle_show_event(arguments)

    assert result["success"] is True
    assert result["event"]["id"] == 1


@pytest.mark.asyncio
async def test_handle_show_event_not_found(mock_db_session):
    """Test handle_show_event when an event is not found."""
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    arguments = {"event_id": 99}

    result = await CoreMCPTools.handle_show_event(arguments)

    assert result["success"] is False
    assert result["error"] == "Event with ID 99 not found"


@pytest.mark.asyncio
async def test_handle_list_events_empty(mock_db_session):
    """Test handle_list_events when no events are found."""
    mock_db_session.query.return_value.all.return_value = []
    arguments = {}

    result = await CoreMCPTools.handle_list_events(arguments)

    assert result == {"success": True, "events": [], "total": 0}


@pytest.mark.asyncio
async def test_handle_list_events_with_data(mock_db_session):
    """Test handle_list_events with sorting, filtering, and pagination."""
    # This is a simplified mock. A real test would have more realistic data.
    mock_event = MagicMock()
    mock_event.id = 1
    mock_event.source_url = "http://example.com/event"
    mock_event.scraped_at = None
    mock_event.updated_at = None
    mock_event.data_hash = "12345"
    mock_event.scraped_data = {"title": "Test"}
    mock_event.submissions = []

    mock_query = mock_db_session.query.return_value
    mock_query.all.return_value = [mock_event]
    mock_query.limit.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.filter.return_value = mock_query

    arguments = {"limit": 1, "sort": "url", "order": "asc", "search": "event"}

    result = await CoreMCPTools.handle_list_events(arguments)

    mock_query.limit.assert_called_with(1)
    mock_query.order_by.assert_called()
    mock_query.filter.assert_called()

    assert result["success"] is True
    assert len(result["events"]) == 1
    assert result["total"] == 1
    assert result["limit_applied"] == 1


@pytest.mark.asyncio
async def test_handle_get_statistics_combined():
    """Test handle_get_statistics for combined stats."""
    with patch("app.interfaces.mcp.server.StatisticsService") as mock_stats_service:
        mock_instance = mock_stats_service.return_value
        mock_instance.get_combined_statistics.return_value = {"total_events": 10}

        result = await CoreMCPTools.handle_get_statistics({})

        assert result == {"success": True, "statistics": {"total_events": 10}}
        mock_instance.get_combined_statistics.assert_called_once()


@pytest.mark.asyncio
async def test_handle_get_statistics_detailed():
    """Test handle_get_statistics for detailed stats."""
    with patch("app.interfaces.mcp.server.StatisticsService") as mock_stats_service:
        mock_instance = mock_stats_service.return_value
        mock_instance.get_detailed_statistics.return_value = {"by_source": {"a": 1}}

        result = await CoreMCPTools.handle_get_statistics({"detailed": True})

        assert result == {"success": True, "statistics": {"by_source": {"a": 1}}}
        mock_instance.get_detailed_statistics.assert_called_once()


@pytest.mark.asyncio
async def test_handle_get_statistics_error():
    """Test handle_get_statistics on error."""
    with patch("app.interfaces.mcp.server.StatisticsService") as mock_stats_service:
        mock_instance = mock_stats_service.return_value
        mock_instance.get_combined_statistics.side_effect = ValueError("Test Error")

        result = await CoreMCPTools.handle_get_statistics({})

        assert result["success"] is False
        assert "Test Error" in result["error"]


def test_get_all_tools():
    """Test that get_all_tools combines core and integration tools."""
    mock_integration_class = MagicMock()
    mock_integration_instance = MagicMock()
    mock_integration_class.return_value = mock_integration_instance

    mock_tools_module = MagicMock()
    mock_tools_module.TOOLS = [
        types.Tool(name="integration_tool", description="A test tool", inputSchema={})
    ]
    mock_integration_instance.get_mcp_tools.return_value = mock_tools_module

    with patch(
        "app.interfaces.mcp.server.get_available_integrations"
    ) as mock_get_integrations:
        mock_get_integrations.return_value = {"mock": mock_integration_class}
        tools = get_all_tools()
        assert len(tools) > len(CoreMCPTools.TOOLS)
        assert any(t.name == "integration_tool" for t in tools)


def test_get_all_tool_handlers():
    """Test that get_all_tool_handlers combines core and integration handlers."""
    mock_integration_class = MagicMock()
    mock_integration_instance = MagicMock()
    mock_integration_class.return_value = mock_integration_instance

    mock_tools_module = MagicMock()
    mock_tools_module.TOOL_HANDLERS = {"integration_handler": lambda: "handled"}
    mock_integration_instance.get_mcp_tools.return_value = mock_tools_module

    with patch(
        "app.interfaces.mcp.server.get_available_integrations"
    ) as mock_get_integrations:
        mock_get_integrations.return_value = {"mock": mock_integration_class}
        handlers = get_all_tool_handlers()
        assert "integration_handler" in handlers


@pytest.mark.asyncio
async def test_handle_call_tool_dispatch():
    """Test the main tool dispatcher."""
    mock_router = AsyncMock()
    mock_handler = AsyncMock(return_value={"status": "ok"})
    all_handlers = {"test_tool": mock_handler}

    # Test calling a known tool
    result = await handle_call_tool(
        name="test_tool", arguments={}, router=mock_router, all_handlers=all_handlers
    )
    mock_handler.assert_awaited_once_with({})
    assert '"status": "ok"' in result[0].text

    # Test calling an unknown tool
    result = await handle_call_tool(
        name="unknown_tool",
        arguments={},
        router=mock_router,
        all_handlers=all_handlers,
    )
    assert '"success": false' in result[0].text
    assert "Unknown tool: unknown_tool" in result[0].text

    # Test exception handling
    mock_handler.side_effect = ValueError("Something went wrong")
    result = await handle_call_tool(
        name="test_tool", arguments={}, router=mock_router, all_handlers=all_handlers
    )
    assert '"success": false' in result[0].text
    assert "Something went wrong" in result[0].text
