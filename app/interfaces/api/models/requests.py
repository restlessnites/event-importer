"""API request models."""

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class ImportEventRequest(BaseModel):
    """Request model for importing an event."""

    url: HttpUrl = Field(..., description="URL of the event page to import")
    force_method: Literal["api", "web", "image"] | None = Field(
        None, description="Force a specific import method"
    )
    include_raw_data: bool = Field(
        False, description="Include raw extracted data in response"
    )
    timeout: int = Field(60, description="Timeout in seconds", ge=1, le=300)
    ignore_cache: bool = Field(False, description="Skip cache and force fresh import")
