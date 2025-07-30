"""API request models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ImportEventRequest(BaseModel):
    """Request model for importing an event."""

    url: HttpUrl = Field(..., description="URL of the event page to import")
    force_method: Literal["api", "web", "image"] | None = Field(
        None,
        description="Force a specific import method",
    )
    include_raw_data: bool = Field(
        False,
        description="Include raw extracted data in response",
    )
    timeout: int = Field(60, description="Timeout in seconds", ge=1, le=300)
    ignore_cache: bool = Field(False, description="Skip cache and force fresh import")


class RebuildDescriptionRequest(BaseModel):
    """Request model for rebuilding event description."""

    description_type: Literal["short", "long"] = Field(
        ..., description="Which description to regenerate: 'short' or 'long'"
    )
    supplementary_context: str | None = Field(
        None,
        description="Additional context to help regenerate descriptions",
        max_length=1000,
    )


class UpdateEventRequest(BaseModel):
    """Request model for updating event fields."""

    model_config = ConfigDict(extra="forbid")  # Don't allow extra fields

    title: str | None = Field(None, description="Event title")
    venue: str | None = Field(None, description="Venue name")
    date: str | None = Field(None, description="Event start date (YYYY-MM-DD)")
    end_date: str | None = Field(
        None, description="Event end date for multi-day events (YYYY-MM-DD)"
    )
    time: dict | None = Field(
        None, description="Event time with start, end, and timezone"
    )
    short_description: str | None = Field(None, description="Short event description")
    long_description: str | None = Field(None, description="Detailed event description")
    genres: list[str] | None = Field(None, description="List of genres")
    lineup: list[str] | None = Field(None, description="List of artists/performers")
    minimum_age: str | None = Field(
        None, description="Minimum age requirement (e.g., '18+', '21+', 'All Ages')"
    )
    cost: str | None = Field(None, description="Ticket cost information")


class RebuildGenresRequest(BaseModel):
    """Request model for rebuilding event genres."""

    supplementary_context: str | None = Field(
        None,
        description="Additional context to help identify genres (e.g., style, similar artists)",
        max_length=1000,
    )


class RebuildImageRequest(BaseModel):
    """Request model for rebuilding event image."""

    supplementary_context: str | None = Field(
        None,
        description="Additional context to help find better images (e.g., specific lineup, festival year)",
        max_length=1000,
    )
