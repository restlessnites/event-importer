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


class ServiceMessages:
    """Error messages for external services and APIs."""

    # LLM Services
    LLM_NO_PROVIDERS_CONFIGURED = "No LLM providers configured"
    LLM_EXTRACTION_FAILED = "Failed to extract from image using LLM"

    # OpenAI
    OPENAI_CLIENT_NOT_INITIALIZED = "OpenAI client not initialized"
    OPENAI_API_KEY_NOT_FOUND = "OpenAI API key not found"

    # Genre Service
    GENRE_ENHANCEMENT_FAILED = "Genre enhancement failed"
    GENRE_SEARCH_FAILED = "Failed to search genres"
    LLM_GENRE_ANALYSIS_FAILED = "LLM genre analysis failed"


class AgentMessages:
    """Error messages for import agents."""

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

    # Image Agent
    IMAGE_IMPORT_FAILED = "Image import failed"
    IMAGE_EXTRACT_FAILED = "Could not extract event information from image"

    # Web Agent
    WEB_EXTRACTION_FAILED = "Could not extract event data from any method"


class InterfaceMessages:
    """Error messages for user interfaces (CLI, API, MCP)."""

    # CLI Messages
    CLI_ERROR = "CLI error"
    CLEANUP_WARNING = "Cleanup warning"

    # MCP Messages
    STATISTICS_ERROR = "Failed to get statistics"
    TOOL_CALL_ERROR = "Tool call error"
