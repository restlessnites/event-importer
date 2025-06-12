"""Data models for the Event Importer using Pydantic."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
import re

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
    CACHE = "cache"  # Served from cache


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

    @field_validator("coordinates", mode="before")
    def validate_coordinates(cls, v: Any) -> Optional[Dict]:
        """Ensure coordinates are a valid dict or None."""
        if not isinstance(v, dict):
            return None
        # If lat or lng are missing or None, the whole object is invalid
        if v.get("lat") is None or v.get("lng") is None:
            return None
        return v


class ImageCandidate(BaseModel):
    """Information about a candidate image during import."""

    url: str  # Changed from HttpUrl to avoid validation issues
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
    images: Optional[Dict[str, str]] = None  # Changed from EventImages to Dict
    image_search: Optional[ImageSearchResult] = None  # For non-API imports

    # Restrictions and pricing
    minimum_age: Optional[str] = None  # e.g., "21+", "All Ages"
    cost: Optional[str] = None

    # Links
    ticket_url: Optional[HttpUrl] = None
    source_url: Optional[HttpUrl] = None

    # Metadata
    imported_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("time", "location", "images", mode="before")
    def ensure_dict_or_none(cls, v: Any) -> Optional[Dict]:
        """Ensure that fields that should be objects are dicts, or None if invalid."""
        if v and not isinstance(v, dict):
            return None
        return v

    @field_validator("title", "venue", mode="before")
    def clean_text_field(cls, v: Any) -> Optional[str]:
        """Strip whitespace and handle None for text fields."""
        if not v:
            return None
        cleaned = nh3.clean(str(v), tags=set()).strip()
        return cleaned or None

    @field_validator("date", mode="before")
    def parse_date(cls, v: Any) -> Optional[str]:
        """Parse various date formats to ISO format with smart year handling."""
        if not v:
            return None

        try:
            current_date = datetime.now()
            current_year = current_date.year
            
            # Clean the input string
            date_str = str(v).strip()
            original_str = date_str.lower()
            
            # Check if year is explicitly mentioned in the string
            year_indicators = [
                str(current_year - 2), str(current_year - 1), str(current_year), 
                str(current_year + 1), str(current_year + 2), str(current_year + 3),
                "'22", "'23", "'24", "'25", "'26", "'27", "'28",
                "2022", "2023", "2024", "2025", "2026", "2027", "2028"
            ]
            
            has_explicit_year = any(year_str in original_str for year_str in year_indicators)
            
            # IMPORTANT: Always use current year as the default to start with
            default_date = datetime(current_year, 1, 1)
            parsed = date_parser.parse(date_str, fuzzy=True, default=default_date)
            
            # If no explicit year was provided, apply smart year logic
            if not has_explicit_year:
                # Ensure the parsed date used our current year default
                if parsed.year != current_year:
                    # If dateutil somehow chose a different year, force it to current year first
                    parsed = parsed.replace(year=current_year)
                
                # Now check if the date with current year is in the past
                if parsed.date() < current_date.date():
                    days_diff = (current_date.date() - parsed.date()).days
                    
                    # If it's more than 1 day in the past, assume it's next year
                    if days_diff > 1:
                        parsed = parsed.replace(year=current_year + 1)
            
            return parsed.date().isoformat()
            
        except Exception as e:
            # Import logging here to avoid circular imports
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Date parsing failed for '{v}': {e}")
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
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Remove trailing ellipsis
        cleaned = cleaned.rstrip(".")

        return cleaned or None

    @field_validator("cost", mode="before")
    def parse_cost(cls, v: Any) -> Optional[str]:
        """Parse and standardize cost information with comprehensive normalization."""
        if not v:
            return None

        # Convert to string and clean
        v_str = str(v).strip().lower()
        
        # Remove common HTML entities and extra whitespace
        v_clean = nh3.clean(v_str, tags=set()).strip()
        
        # Check for free indicators (case insensitive)
        free_indicators = [
            # Direct free terms
            "free", "gratis", "no cover", "complimentary", "admission free",
            "free admission", "free entry", "no charge", "gratuito", "gratuit",
            
            # Zero values
            "0", "0.00", "$0", "$0.00", "£0", "€0", "¥0",
            "usd 0", "gbp 0", "eur 0", "cad 0",
            
            # None/null indicators  
            "none", "null", "n/a", "na", "no cost", "no fee",
            
            # Special free event phrases
            "free w/ rsvp", "free with rsvp", "free w/rsvp",
            "donation", "donation only", "donations", "suggested donation",
            "pay what you want", "pwyw", "by donation"
        ]
        
        # Check if it's a free event
        for indicator in free_indicators:
            if indicator in v_clean:
                return "Free"
        
        # Check for numeric zero values with various formats
        # Match patterns like "0", "$0", "0.00", "$0.00", etc.
        zero_patterns = [
            r'^0+$',                    # Just zeros
            r'^0+\.0+$',               # 0.00, 0.000, etc.
            r'^[\$£€¥]?\s*0+$',        # Currency + zeros
            r'^[\$£€¥]?\s*0+\.0+$',    # Currency + 0.00
            r'^\s*0+\s*(usd|gbp|eur|cad|dollars?|pounds?|euros?)\s*$',  # 0 USD, etc.
        ]
        
        for pattern in zero_patterns:
            if re.match(pattern, v_clean):
                return "Free"
        
        # If we get here, it's not free - clean up the original value
        original_clean = nh3.clean(str(v), tags=set()).strip()
        
        # Return the cleaned cost if it has meaningful content
        if original_clean and original_clean.lower() not in ["", "n/a", "na", "none", "null", "tbd", "tba"]:
            return original_clean
        
        # Default to None if no meaningful cost information
        return None

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
    ignore_cache: bool = Field(default=False, description="Skip cache and force fresh import")


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