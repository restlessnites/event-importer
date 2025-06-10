"""API response models."""

from typing import Optional, Any, List
from pydantic import BaseModel, Field

from app.schemas import EventData, ImportProgress


class ImportEventResponse(BaseModel):
    """Response model for event import."""
    
    success: bool = Field(..., description="Whether the import was successful")
    data: Optional[EventData] = Field(None, description="Imported event data")
    method_used: Optional[str] = Field(None, description="Import method that was used")
    import_time: Optional[float] = Field(None, description="Time taken for import in seconds")
    error: Optional[str] = Field(None, description="Error message if import failed")


class ProgressResponse(BaseModel):
    """Response model for progress tracking."""
    
    request_id: str = Field(..., description="Request ID")
    updates: List[ImportProgress] = Field(..., description="Progress updates")


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    features: List[str] = Field(..., description="Enabled features") 