"""Data models for the Event Importer using Pydantic."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, date, datetime, time, timedelta

try:
    from datetime import UTC
except ImportError:
    UTC = UTC
from enum import StrEnum
from typing import Any, ForwardRef, TypeVar

import nh3
from dateutil import parser as date_parser
from pydantic import (  # pylint: disable=E0611
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_serializer,
    field_validator,
    model_validator,
)

logger = logging.getLogger(__name__)


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    return "".join(
        word.capitalize() if i > 0 else word for i, word in enumerate(string.split("_"))
    )


class CustomBaseModel(BaseModel):
    """Custom base model with shared configuration."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    @field_serializer("*", mode="wrap")
    def serialize_datetime_fields(
        self: CustomBaseModel,
        value: Any,
        serializer: Any,
    ) -> Any:
        """Serialize datetime fields to ISO format."""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, time):
            return value.isoformat()
        if isinstance(value, timedelta):
            return value.total_seconds()
        return serializer(value)


class ImportStatus(StrEnum):
    """Status of an import request."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportMethod(StrEnum):
    """Method used for import."""

    API = "api"
    WEB = "web"
    IMAGE = "image"
    CACHE = "cache"


class EventTime(BaseModel):
    """Event time information."""

    start: str | None = None
    end: str | None = None
    timezone: str | None = None

    @field_validator("start", "end", mode="before")
    @classmethod
    def parse_time(cls: type[EventTime], v: str | None) -> str | None:
        """Parse various time formats to HH:MM."""
        if not v:
            return None
        try:
            # Use dateutil.parser for robust time parsing with fuzzy matching
            parsed_time = date_parser.parse(v, fuzzy=True)
            return parsed_time.strftime("%H:%M")
        except (ValueError, TypeError):
            # Return None if parsing fails, indicating an invalid time format
            return None

    def __bool__(self: EventTime) -> bool:
        """Check if any time is set."""
        return bool(self.start or self.end)


class Coordinates(BaseModel):
    """Geographic coordinates."""

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class EventLocation(BaseModel):
    """Event location details."""

    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    coordinates: Coordinates | None = None

    @field_validator("address", "city", "state", "country", mode="before")
    @classmethod
    def clean_text(cls: type[EventLocation], v: str | None) -> str | None:
        """Clean location text fields."""
        if not v:
            return None
        return nh3.clean(str(v), tags=set()).strip() or None

    def __bool__(self: EventLocation) -> bool:
        """Check if any location data is set."""
        return any(
            [self.address, self.city, self.state, self.country, self.coordinates],
        )

    def to_string(self: EventLocation) -> str:
        """Format location as a string."""
        parts = []
        if self.address:
            parts.append(self.address)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts)

    @field_validator("coordinates", mode="before")
    @classmethod
    def validate_coordinates(
        cls: type[EventLocation],
        v: dict[str, Any] | Coordinates | None,
    ) -> dict | Coordinates | None:
        """Ensure coordinates are a valid dict or None."""
        if v is None:
            return None
        if isinstance(v, Coordinates):
            return v
        if not isinstance(v, dict):
            return None
        if v.get("lat") is None or v.get("lng") is None:
            return None
        return v


T = TypeVar("T")

ResponseRef = ForwardRef("Response")


class Response[T](CustomBaseModel):
    """Generic API response model."""

    success: bool = True
    data: T | None = None
    error: str | None = None


class ImageCandidate(BaseModel):
    """Information about a candidate image during import."""

    url: str
    score: int = 0
    source: str = "unknown"
    dimensions: str | None = None
    reason: str | None = None

    def __lt__(self: ImageCandidate, other: ImageCandidate) -> bool:
        """Sort by score (highest first)."""
        return self.score > other.score


class ImageSearchResult(BaseModel):
    """Results from image search/enhancement for non-API imports."""

    original: ImageCandidate | None = None
    candidates: list[ImageCandidate] = Field(default_factory=list)
    selected: ImageCandidate | None = None

    def get_best_candidate(self: ImageSearchResult) -> ImageCandidate | None:
        """Get the highest scoring candidate."""
        all_candidates = [
            c for c in [self.original] + self.candidates if c and c.score > 0
        ]
        return max(all_candidates, key=lambda c: c.score) if all_candidates else None


class Statistics(BaseModel):
    """Statistics model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    total_events: int = 0
    new_events: int = 0
    updated_events: int = 0
    last_updated: timedelta | None = None

    @field_serializer("last_updated", when_used="json")
    def ser_json_timedelta(self: Statistics, v: timedelta) -> float:
        """Serialize timedelta to seconds."""
        return v.total_seconds()


class EventData(BaseModel):
    """Structured event data imported from sources."""

    title: str = Field(..., min_length=3, max_length=200)
    venue: str | None = None
    date: str | None = None
    end_date: str | None = None
    time: EventTime | None = None
    promoters: list[str] = Field(default_factory=list)
    lineup: list[str] = Field(default_factory=list)
    long_description: str | None = None
    short_description: str | None = Field(None, max_length=200)
    genres: list[str] = Field(default_factory=list)
    location: EventLocation | None = None
    images: dict[str, str] | None = None
    image_search: ImageSearchResult | None = None
    minimum_age: str | None = None
    cost: str | None = None
    ticket_url: HttpUrl | None = None
    source_url: HttpUrl | None = None
    imported_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_serializer("*", mode="wrap")
    def serialize_fields(
        self: EventData,
        value: Any,
        serializer: Any,
    ) -> Any:
        """Serialize special fields."""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, HttpUrl):
            return str(value)
        return serializer(value)

    @field_validator("images", mode="before")
    @classmethod
    def ensure_dict_or_none(cls: type[EventData], v: object | None) -> dict | None:
        """Ensure that fields that should be objects are dicts, or None if invalid."""
        if v and not isinstance(v, dict):
            return None
        return v

    @field_validator("title", "venue", mode="before")
    @classmethod
    def clean_text_field(cls: type[EventData], v: str | None) -> str | None:
        """Strip whitespace and handle None for text fields."""
        if not v:
            return None
        cleaned = nh3.clean(str(v), tags=set()).strip()
        return cleaned or None

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls: type[EventData], v: str | None) -> str | None:
        """Parse various date formats to ISO format with smart year handling."""
        if not v:
            return None
        try:
            current_date = datetime.now()
            current_year = current_date.year
            date_str = str(v).strip()
            original_str = date_str.lower()
            year_indicators = [
                str(current_year - 2),
                str(current_year - 1),
                str(current_year),
                str(current_year + 1),
                str(current_year + 2),
                str(current_year + 3),
                "'22",
                "'23",
                "'24",
                "'25",
                "'26",
                "'27",
                "'28",
                "2022",
                "2023",
                "2024",
                "2025",
                "2026",
                "2027",
                "2028",
            ]
            has_explicit_year = any(
                year_str in original_str for year_str in year_indicators
            )
            default_date = datetime(current_year, 1, 1)
            parsed = date_parser.parse(date_str, fuzzy=True, default=default_date)
            if not has_explicit_year and parsed.date() < current_date.date():
                # If the date is in the past, check how far back.
                days_diff = (current_date.date() - parsed.date()).days
                # If it's over 90 days ago, assume it's for the next year.
                # Otherwise, it's a recent event from the current year.
                if days_diff > 90:
                    parsed = parsed.replace(year=current_year + 1)
            return parsed.date().isoformat()
        except (ValueError, TypeError) as e:
            logger.debug(f"Date parsing failed for '{v}': {e}")
            return None

    @field_validator("promoters", "lineup", "genres", mode="before")
    @classmethod
    def clean_list_field(
        cls: type[EventData],
        v: list[str] | str | None,
    ) -> list[str]:
        """Clean and deduplicate list fields."""
        if not v:
            return []
        if isinstance(v, str):
            v = [v]
        seen = set()
        result = []
        for item in v:
            if not item:
                continue
            cleaned = nh3.clean(str(item), tags=set()).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
        return result

    @field_validator("long_description", "short_description", mode="before")
    @classmethod
    def clean_description(cls: type[EventData], v: str | None) -> str | None:
        """Clean description fields."""
        if not v:
            return None
        cleaned = nh3.clean(str(v), tags=set()).strip()
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = cleaned.rstrip(".")
        return cleaned or None

    @field_validator("cost", mode="before")
    @classmethod
    def parse_cost(cls: type[EventData], v: str | float | None) -> str | None:
        """Parse and standardize cost information."""
        if not v:
            return None
        v_str = str(v).strip().lower()
        v_clean = nh3.clean(v_str, tags=set()).strip()
        free_indicators = [
            "free",
            "gratis",
            "no cover",
            "complimentary",
            "admission free",
            "free admission",
            "free entry",
            "no charge",
            "gratuito",
            "gratuit",
            "none",
            "null",
            "n/a",
            "na",
            "no cost",
            "no fee",
            "free w/ rsvp",
            "free with rsvp",
            "free w/rsvp",
            "donation",
            "donation only",
            "donations",
            "suggested donation",
            "pay what you want",
            "pwyw",
            "by donation",
        ]
        for indicator in free_indicators:
            if indicator in v_clean:
                return "Free"
        zero_patterns = [
            r"^0+$",
            r"^0+\.0+$",
            r"^[\$£€¥]?\s*0+$",
            r"^[\$£€¥]?\s*0+\.0+$",
            r"^\s*0+\s*(usd|gbp|eur|cad|dollars?|pounds?|euros?)\s*$",
        ]
        for pattern in zero_patterns:
            if re.match(pattern, v_clean):
                return "Free"
        original_clean = nh3.clean(str(v), tags=set()).strip()
        if original_clean and original_clean.lower() not in [
            "",
            "n/a",
            "na",
            "none",
            "null",
            "tbd",
            "tba",
        ]:
            return original_clean
        return None

    @field_validator("minimum_age", mode="before")
    @classmethod
    def standardize_age(cls: type[EventData], v: str | int | None) -> str | None:
        """Standardize age restrictions."""
        if not v:
            return None
        v = str(v).strip()
        if any(word in v.lower() for word in ["all ages", "todos", "family"]):
            return "All Ages"
        match = re.search(r"(\d+)\s*\+?", v)
        if match:
            age = int(match.group(1))
            return f"{age}+"
        return nh3.clean(v, tags=set()).strip() or None

    @model_validator(mode="after")
    def calculate_end_date(self: EventData) -> EventData:
        """Calculate end_date if it's not provided.
        Sets end_date to the next day if end time is earlier than start time.
        Otherwise, sets end_date to be the same as the start date.
        """
        # Don't overwrite an existing end_date
        if self.end_date:
            return self

        # Check for required fields
        if not self.date or not self.time or not self.time.start or not self.time.end:
            return self

        try:
            # Use dateutil.parser for robust parsing of date and time
            start_time_obj = date_parser.parse(self.time.start).time()
            end_time_obj = date_parser.parse(self.time.end).time()
            start_date_obj = date_parser.parse(self.date)

            logger.debug(
                "Calculating end date: start_date=%s, start_time=%s, end_time=%s",
                start_date_obj.date(),
                start_time_obj,
                end_time_obj,
            )

            # A time of 00:00 is considered the end of the current day in this context.
            # Only advance to the next day if the end time is past midnight.
            if end_time_obj < start_time_obj and end_time_obj != time(0, 0):
                self.end_date = (start_date_obj + timedelta(days=1)).strftime(
                    "%Y-%m-%d"
                )
                logger.info(f"Calculated next-day end date: {self.end_date}")
            else:
                # If end time is not earlier (or is midnight), end date is the same day
                self.end_date = start_date_obj.strftime("%Y-%m-%d")
                logger.info(f"Calculated same-day end date: {self.end_date}")
        except (ValueError, TypeError) as e:
            # In case of date or time parsing errors, leave end_date as None
            logger.warning(f"Could not calculate end_date due to error: {e}")
            pass

        return self

    def is_complete(self: EventData) -> bool:
        """Check if the event data is sufficiently complete."""
        return all(
            [
                self.title,
                self.venue,
                self.date,
                bool(self.lineup or self.long_description),
            ],
        )


class ImportRequest(BaseModel):
    """Request to import event data."""

    url: HttpUrl
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    force_method: ImportMethod | None = None
    include_raw_data: bool = False
    timeout: int = Field(default=60, ge=1, le=300)
    ignore_cache: bool = Field(
        default=False,
        description="Skip cache and force fresh import",
    )
    force_description_rebuild: bool = Field(
        default=False, description="Force regeneration of event descriptions"
    )


class ImportProgress(BaseModel):
    """Progress update for import request."""

    request_id: str
    status: ImportStatus
    message: str
    progress: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data: EventData | None = None
    error: str | None = None

    @field_serializer("timestamp", mode="plain")
    def serialize_timestamp(self: ImportProgress, value: datetime) -> str:
        """Serialize timestamp to ISO format."""
        return value.isoformat()


class ServiceFailure(BaseModel):
    """Information about a failed service during import."""

    service: str
    error: str
    detail: str | None = None


class ImportResult(BaseModel):
    """Final result of import request."""

    request_id: str
    status: ImportStatus
    url: HttpUrl
    method_used: ImportMethod | None = None
    event_data: EventData | None = None
    error: str | None = None
    raw_data: dict[str, Any] | None = None
    import_time: float = Field(default=0.0, ge=0.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    service_failures: list[ServiceFailure] = Field(default_factory=list)

    def __bool__(self: ImportResult) -> bool:
        """Check if import was successful."""
        return self.status == ImportStatus.SUCCESS and self.event_data is not None

    @field_serializer("timestamp", mode="plain")
    def serialize_timestamp(self: ImportResult, value: datetime) -> str:
        """Serialize timestamp to ISO format."""
        return value.isoformat()

    @field_serializer("url", mode="plain")
    def serialize_url(self: ImportResult, value: HttpUrl) -> str:
        """Serialize URL to string."""
        return str(value)
