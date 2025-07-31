"""API request models."""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


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
    ticket_url: str | None = Field(None, description="URL for ticket purchase")
    promoters: list[str] | None = Field(None, description="List of event promoters")
    images: dict[str, str] | None = Field(None, description="Image URLs (full and thumbnail)")

    @field_validator("ticket_url")
    @classmethod
    def validate_ticket_url(cls, v: str | None) -> str | None:
        """Validate ticket URL is a valid URL."""
        if v is None:
            return v
        try:
            # Try to parse as URL
            HttpUrl(v)
            return v
        except Exception as err:
            raise ValueError("Invalid URL format for ticket_url") from err

    @field_validator("images")
    @classmethod
    def validate_images(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        """Validate images structure and URLs."""
        if v is None:
            return v

        # Check keys
        invalid_keys = set(v.keys()) - {"full", "thumbnail"}
        if invalid_keys:
            raise ValueError(f"Invalid image keys: {invalid_keys}. Only 'full' and 'thumbnail' are allowed")

        # Validate URLs
        for key, url in v.items():
            if url:
                try:
                    HttpUrl(url)
                except Exception as err:
                    raise ValueError(f"Invalid URL format for image '{key}': {url}") from err

        return v

    @field_validator("date", "end_date")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        """Validate date format YYYY-MM-DD."""
        if v is None:
            return v

        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("Date must be in YYYY-MM-DD format")

        # Check if it's a valid date
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as err:
            raise ValueError(f"Invalid date: {v}") from err

        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: dict | None) -> dict | None:
        """Validate time structure."""
        if v is None:
            return v

        required_keys = {"start", "end", "timezone"}
        if not all(k in v for k in required_keys):
            raise ValueError(f"Time must include: {required_keys}")

        # Validate time format
        for key in ["start", "end"]:
            if key in v and v[key] and not re.match(r"^\d{2}:\d{2}$", v[key]):
                raise ValueError(f"{key} time must be in HH:MM format")

        return v

    @field_validator("genres", "lineup", "promoters")
    @classmethod
    def validate_string_lists(cls, v: list[str] | None) -> list[str] | None:
        """Validate string lists are not empty strings."""
        if v is None:
            return v

        # Filter out empty strings
        cleaned = [item.strip() for item in v if item.strip()]
        return cleaned if cleaned else None


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
