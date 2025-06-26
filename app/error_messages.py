"""Centralized error messages for the Event Importer application.

This module provides a single source of truth for all error messages,
organized by domain and functionality to ensure consistency and maintainability.
"""


class CommonMessages:
    """Common error messages used across multiple modules."""

    STARTUP_FAILED = "Startup failed"
    CONFIGURATION_ERROR = "Configuration error"
    IMPORT_FAILED = "Import failed"
    FATAL_ERROR = "Fatal error"
    UNEXPECTED_ERROR = "An unexpected error occurred"
    OPERATION_FAILED = "Operation failed"
    SERVICE_UNAVAILABLE = "Service unavailable"
    VALIDATION_FAILED = "Validation failed"
    INITIALIZATION_FAILED = "Initialization failed"


class ServiceMessages:
    """Error messages for external services and APIs."""

    # LLM Services
    LLM_NO_PROVIDERS_CONFIGURED = "No LLM providers configured"
    LLM_RESPONSE_FAILED = "Failed to get LLM response"
    LLM_EXTRACTION_FAILED = "Failed to extract from image using LLM"

    # OpenAI
    OPENAI_CLIENT_NOT_INITIALIZED = "OpenAI client not initialized"
    OPENAI_API_KEY_NOT_FOUND = "OpenAI API key not found"
    OPENAI_API_ERROR = "OpenAI API error"

    # Claude
    CLAUDE_CLIENT_NOT_INITIALIZED = "Claude client not initialized"
    CLAUDE_API_KEY_NOT_FOUND = "Claude API key not found"
    CLAUDE_API_ERROR = "Claude API error"

    # Image Service
    IMAGE_PROCESSING_FAILED = "Image processing failed"
    IMAGE_DOWNLOAD_FAILED = "Failed to download image"
    IMAGE_VALIDATION_FAILED = "Image validation failed"

    # Genre Service
    GENRE_ENHANCEMENT_FAILED = "Genre enhancement failed"
    GENRE_SEARCH_FAILED = "Failed to search genres"
    LLM_GENRE_ANALYSIS_FAILED = "LLM genre analysis failed"

    # Zyte Service
    ZYTE_API_ERROR = "Zyte API error"
    ZYTE_SCRAPING_FAILED = "Zyte scraping failed"


class AgentMessages:
    """Error messages for import agents."""

    # Generic agent messages
    AGENT_IMPORT_FAILED = "Agent import failed"
    EVENT_DATA_EXTRACTION_FAILED = "Failed to extract event data"
    DESCRIPTION_GENERATION_FAILED = "Failed to generate descriptions"

    # Dice Agent
    DICE_SEARCH_FAILED = "Dice search failed"
    DICE_API_ERROR = "Error fetching Dice API data"
    DICE_TRANSFORM_ERROR = "Error transforming Dice API data"
    DICE_EVENT_NOT_FOUND = "Could not find event using Dice search API"
    DICE_DATA_FETCH_FAILED = "Could not fetch event data from Dice API"
    DICE_DATA_TRANSFORM_FAILED = "Could not transform Dice API data to event format"

    # RA Agent
    RA_IMPORT_FAILED = "RA import failed"

    # Ticketmaster Agent
    TICKETMASTER_IMPORT_FAILED = "Ticketmaster import failed"
    DISCOVERY_API_ERROR = "Error searching Discovery API"
    TICKETMASTER_URL_EXTRACT_FAILED = "Could not extract event information from URL"
    TICKETMASTER_EVENT_NOT_FOUND = "Could not find event using Ticketmaster search"

    # Image Agent
    IMAGE_IMPORT_FAILED = "Image import failed"
    IMAGE_EXTRACT_FAILED = "Could not extract event information from image"

    # Web Agent
    WEB_SCRAPING_FAILED = "Web scraping failed"
    WEB_EXTRACTION_FAILED = "Could not extract event data from any method"


class InterfaceMessages:
    """Error messages for user interfaces (CLI, API, MCP)."""

    # CLI Messages
    CLI_ERROR = "CLI error"
    CLEANUP_WARNING = "Cleanup warning"

    # API Messages
    API_ERROR = "API error"
    HEALTH_CHECK_ERROR = "Health check error"
    ROUTER_ERROR = "Router error"
    PROGRESS_ERROR = "Progress error"

    # MCP Messages
    STATISTICS_ERROR = "Failed to get statistics"
    TOOL_CALL_ERROR = "Tool call error"


class HTTPMessages:
    """Error messages for HTTP operations."""

    HTTP_REQUEST_FAILED = "HTTP request failed"
    HTTP_TIMEOUT = "HTTP request timeout"
    HTTP_CLIENT_ERROR = "HTTP client error"
    HTTP_SERVER_ERROR = "HTTP server error"
    RESPONSE_VALIDATION_FAILED = "Response validation failed"
    INVALID_RESPONSE_SIZE = "Response size validation failed"


class DatabaseMessages:
    """Error messages for database operations."""

    DATABASE_CONNECTION_FAILED = "Database connection failed"
    DATABASE_QUERY_FAILED = "Database query failed"
    DATABASE_MIGRATION_FAILED = "Database migration failed"


class IntegrationMessages:
    """Error messages for third-party integrations."""

    INTEGRATION_DISCOVERY_ERROR = "Error discovering integrations"
    INTEGRATION_LOAD_ERROR = "Failed to load integration"
    INTEGRATION_PROCESSING_FAILED = "Failed to process event for integration"

    # TicketFairy
    TICKETFAIRY_SUBMISSION_FAILED = "TicketFairy submission failed"


class ValidationMessages:
    """Error messages for data validation."""

    INVALID_URL = "Invalid URL"
    INVALID_DATE_FORMAT = "Invalid date format"
    INVALID_TIME_FORMAT = "Invalid time format"
    MISSING_REQUIRED_FIELD = "Missing required field"
    INVALID_DATA_FORMAT = "Invalid data format"


# Convenience functions for common message patterns
def service_not_available(service_name: str) -> str:
    """Generate a service unavailable message."""
    return f"{service_name} service not available"


def api_call_failed(service_name: str) -> str:
    """Generate an API call failed message."""
    return f"{service_name} API call failed"


def processing_failed_for(item_type: str) -> str:
    """Generate a processing failed message for a specific item type."""
    return f"Failed to process {item_type}"


def timeout_exceeded_for(operation: str) -> str:
    """Generate a timeout message for a specific operation."""
    return f"Timeout exceeded for {operation}"
