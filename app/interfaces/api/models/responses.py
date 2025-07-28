"""API response models."""

from pydantic import BaseModel, Field

from app.schemas import EventData, ImportProgress


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


class ProgressResponse(BaseModel):
    """Response model for progress tracking."""

    request_id: str = Field(..., description="Request ID")
    updates: list[ImportProgress] = Field(..., description="Progress updates")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    features: list[str] = Field(..., description="Enabled features")


class RebuildDescriptionResponse(BaseModel):
    """Response model for rebuilding descriptions."""

    success: bool = Field(..., description="Whether the rebuild was successful")
    event_id: int = Field(..., description="Event ID")
    message: str = Field(..., description="Status message")
    data: EventData | None = Field(None, description="Updated event data")
