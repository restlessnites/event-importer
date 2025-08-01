"""API response models."""

from pydantic import BaseModel, Field

from app.core.schemas import EventData, ImportProgress, ServiceFailure


class ImportEventResponse(BaseModel):
    """Response model for event import."""

    success: bool = Field(..., description="Whether the import was successful")
    data: EventData | None = Field(None, description="Imported event data")
    method_used: str | None = Field(None, description="Import method that was used")
    import_time: float | None = Field(
        None,
        description="Time taken for import in seconds",
    )
    error: str | None = Field(None, description="Error message if import failed")
    service_failures: list[ServiceFailure] | None = Field(
        None, description="List of services that failed during import"
    )
    service_failure_messages: list[str] | None = Field(
        None, description="User-friendly messages for service failures"
    )
    service_failure_summary: str | None = Field(
        None, description="Summary of service failures for display"
    )


class ProgressResponse(BaseModel):
    """Response model for progress tracking."""

    request_id: str = Field(..., description="Request ID")
    updates: list[ImportProgress] = Field(..., description="Progress updates")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    features: list[str] = Field(..., description="Enabled features")
    integrations: list[str] = Field(
        default_factory=list, description="Enabled integrations"
    )


class RebuildDescriptionResponse(BaseModel):
    """Response model for rebuilding descriptions."""

    success: bool = Field(..., description="Whether the rebuild was successful")
    event_id: int = Field(..., description="Event ID")
    message: str = Field(..., description="Status message")
    data: EventData | None = Field(None, description="Updated event data")


class UpdateEventResponse(BaseModel):
    """Response model for updating event."""

    success: bool = Field(..., description="Whether the update was successful")
    event_id: int = Field(..., description="Event ID")
    message: str = Field(..., description="Status message")
    data: EventData | None = Field(None, description="Updated event data")
    updated_fields: list[str] = Field(
        ..., description="List of fields that were updated"
    )


class RebuildGenresResponse(BaseModel):
    """Response model for rebuilding genres."""

    success: bool = Field(..., description="Whether the rebuild was successful")
    event_id: int = Field(..., description="Event ID")
    message: str = Field(..., description="Status message")
    data: EventData | None = Field(None, description="Updated event data")
    genres_found: list[str] | None = Field(
        None, description="List of genres found (preview)"
    )
    service_failures: list[ServiceFailure] | None = Field(
        None, description="List of services that failed during rebuild"
    )
    service_failure_messages: list[str] | None = Field(
        None, description="User-friendly messages for service failures"
    )
    service_failure_summary: str | None = Field(
        None, description="Summary of service failures for display"
    )


class RebuildImageResponse(BaseModel):
    """Response model for rebuilding image."""

    success: bool = Field(..., description="Whether the rebuild was successful")
    event_id: int = Field(..., description="Event ID")
    message: str = Field(..., description="Status message")
    data: EventData | None = Field(None, description="Updated event data")
    image_candidates: list[dict] | None = Field(
        None,
        description="All image candidates found with scores, sources, dimensions and reasons",
    )
    best_image: dict | None = Field(
        None,
        description="The best image candidate selected with score, source, dimensions and reason",
    )
    service_failures: list[ServiceFailure] | None = Field(
        None, description="List of services that failed during rebuild"
    )
    service_failure_messages: list[str] | None = Field(
        None, description="User-friendly messages for service failures"
    )
    service_failure_summary: str | None = Field(
        None, description="Summary of service failures for display"
    )
