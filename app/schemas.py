"""Data models for the Event Importer using Pydantic."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid

from pydantic import BaseModel, Field, HttpUrl, field_validator
from dateutil import parser as date_parser
import nh3


class ImportStatus(str, Enum):
    """Status of an import request."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportMethod(str, Enum):
    """Method used for import."""

    API = "api"  # Direct API (e.g., RA.co GraphQL, Ticketmaster)
    WEB = "web"  # Web scraping via Zyte
    IMAGE = "image"  # Visual extraction from images


class EventTime(BaseModel):
    """Event time information."""

    start: Optional[str] = None  # HH:MM format
    end: Optional[str] = None  # HH:MM format

    @field_validator("start", "end", mode="before")
    def parse_time(cls, v: Any) -> Optional[str]:
        """Parse various time formats to HH:MM."""
        if not v:
            return None

        v = str(v).strip()

        # Clean common prefixes
        import re

        v = re.sub(
            r"^\s*(doors?|show|start|begin|end)s?\s*:?\s*", "", v, flags=re.IGNORECASE
        )

        try:
            # dateutil can parse many time formats
            parsed = date_parser.parse(v, fuzzy=True)
            return parsed.strftime("%H:%M")
        except Exception:
            return None

    def __bool__(self) -> bool:
        """Check if any time is set."""
        return bool(self.start or self.end)


class Coordinates(BaseModel):
    """Geographic coordinates."""

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class EventLocation(BaseModel):
    """Event location details."""

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    coordinates: Optional[Coordinates] = None

    @field_validator("address", "city", "state", "country", mode="before")
    def clean_text(cls, v: Any) -> Optional[str]:
        """Clean location text fields."""
        if not v:
            return None
        return nh3.clean(str(v), tags=set()).strip() or None

    def __bool__(self) -> bool:
        """Check if any location data is set."""
        return any(
            [self.address, self.city, self.state, self.country, self.coordinates]
        )

    def to_string(self) -> str:
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


class EventImages(BaseModel):
    """Event image URLs."""

    full: Optional[HttpUrl] = None
    thumbnail: Optional[HttpUrl] = None

    def __bool__(self) -> bool:
        """Check if any image is set."""
        return bool(self.full or self.thumbnail)

    def get_best(self) -> Optional[str]:
        """Get the best available image URL."""
        return (
            str(self.full)
            if self.full
            else (str(self.thumbnail) if self.thumbnail else None)
        )


class ImageCandidate(BaseModel):
    """Information about a candidate image during import."""

    url: HttpUrl
    score: int = 0
    source: str = "unknown"  # "original", "google_search", "page", etc.
    dimensions: Optional[str] = None  # "800x600"
    reason: Optional[str] = None  # Reason for low score/rejection

    def __lt__(self, other: "ImageCandidate") -> bool:
        """Sort by score (highest first)."""
        return self.score > other.score


class ImageSearchResult(BaseModel):
    """Results from image search/enhancement for non-API imports."""

    original: Optional[ImageCandidate] = None
    candidates: List[ImageCandidate] = Field(default_factory=list)
    selected: Optional[ImageCandidate] = None

    def get_best_candidate(self) -> Optional[ImageCandidate]:
        """Get the highest scoring candidate."""
        all_candidates = [
            c for c in [self.original] + self.candidates if c and c.score > 0
        ]
        return max(all_candidates, key=lambda c: c.score) if all_candidates else None


class EventData(BaseModel):
    """Structured event data imported from sources."""

    # Required field
    title: str = Field(..., min_length=1)

    # Event details
    venue: Optional[str] = None
    date: Optional[str] = None  # ISO format YYYY-MM-DD
    time: Optional[EventTime] = None

    # People/organizations
    promoters: List[str] = Field(default_factory=list)
    lineup: List[str] = Field(default_factory=list)

    # Descriptions
    long_description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=150)

    # Categorization
    genres: List[str] = Field(default_factory=list)

    # Location
    location: Optional[EventLocation] = None

    # Media
    images: Optional[EventImages] = None
    image_search: Optional[ImageSearchResult] = None  # For non-API imports

    # Restrictions and pricing
    minimum_age: Optional[str] = None  # e.g., "21+", "All Ages"
    cost: Optional[str] = None

    # Links
    ticket_url: Optional[HttpUrl] = None
    source_url: Optional[HttpUrl] = None

    # Metadata
    imported_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("title", "venue", mode="before")
    def clean_text_field(cls, v: Any) -> Optional[str]:
        """Clean text fields."""
        if not v:
            return None
        cleaned = nh3.clean(str(v), tags=set()).strip()
        return cleaned or None

    @field_validator("date", mode="before")
    def parse_date(cls, v: Any) -> Optional[str]:
        """Parse various date formats to ISO format."""
        if not v:
            return None

        try:
            parsed = date_parser.parse(str(v), fuzzy=True)
            return parsed.date().isoformat()
        except Exception:
            return None

    @field_validator("promoters", "lineup", "genres", mode="before")
    def clean_list_field(cls, v: Any) -> List[str]:
        """Clean and deduplicate list fields."""
        if not v:
            return []

        if isinstance(v, str):
            v = [v]

        # Clean each item and remove duplicates while preserving order
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
    def clean_description(cls, v: Any) -> Optional[str]:
        """Clean description fields."""
        if not v:
            return None

        # Strip HTML and clean
        cleaned = nh3.clean(str(v), tags=set()).strip()

        # Remove excessive whitespace
        import re

        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Remove trailing ellipsis
        cleaned = cleaned.rstrip(".")

        return cleaned or None

    @field_validator("cost", mode="before")
    def parse_cost(cls, v: Any) -> Optional[str]:
        """Parse and standardize cost information."""
        if not v:
            return None

        v = str(v).strip()

        # Check for free events
        if any(
            word in v.lower()
            for word in ["free", "gratis", "no cover", "complimentary"]
        ):
            return "Free"

        # Otherwise just clean it
        return nh3.clean(v, tags=set()).strip() or None

    @field_validator("minimum_age", mode="before")
    def standardize_age(cls, v: Any) -> Optional[str]:
        """Standardize age restrictions."""
        if not v:
            return None

        v = str(v).strip()

        # Check for all ages
        if any(word in v.lower() for word in ["all ages", "todos", "family"]):
            return "All Ages"

        # Extract age number
        import re

        match = re.search(r"(\d+)\s*\+?", v)
        if match:
            age = int(match.group(1))
            return f"{age}+"

        return nh3.clean(v, tags=set()).strip() or None

    def is_complete(self) -> bool:
        """Check if the event has all important fields."""
        return all(
            [
                self.title,
                self.venue,
                self.date,
                bool(self.lineup or self.long_description),
            ]
        )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v),
        }


class ImportRequest(BaseModel):
    """Request to import event data."""

    url: HttpUrl
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    force_method: Optional[ImportMethod] = None
    include_raw_data: bool = False
    timeout: int = Field(default=60, ge=1, le=300)


class ImportProgress(BaseModel):
    """Progress update for import request."""

    request_id: str
    status: ImportStatus
    message: str
    progress: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[EventData] = None
    error: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class ImportResult(BaseModel):
    """Final result of import request."""

    request_id: str
    status: ImportStatus
    url: HttpUrl
    method_used: Optional[ImportMethod] = None
    event_data: Optional[EventData] = None
    error: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    import_time: float = Field(default=0.0, ge=0.0)  # seconds
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def __bool__(self) -> bool:
        """Check if import was successful."""
        return self.status == ImportStatus.SUCCESS and self.event_data is not None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v),
        }
