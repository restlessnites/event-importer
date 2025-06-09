# Genre Enhancer

The Genre Enhancer uses **Claude AI + Google Search** to automatically discover and validate music genres for events that don't have genre information. This creates richer, more searchable event data by combining web search with AI analysis.

## How It Works

### 1. Smart Detection

The system only activates when:

- An event has **no genres** assigned
- The event has **artist lineup** information
- Google Search API is configured

### 2. Intelligent Search Strategy

For each main artist, the enhancer:

1. **Builds targeted search queries** using artist name + context:

   ```plaintext
   "Cursive" music genre artist
   ```

2. **Searches Google** for authoritative music information
   - Prioritizes sources like Wikipedia, Discogs, AllMusic
   - Filters out low-quality results

3. **Extracts relevant text** from top search results:

   ```plaintext
   Title: Cursive (band) - Wikipedia
   Description: Cursive is an American indie rock band from Omaha, Nebraska...
   Source: en.wikipedia.org
   ```

### 3. AI-Powered Analysis

**Claude AI analyzes** the search results to:

- **Verify artist identity** using event context (venue, date, other artists)
- **Extract primary genres** from biographical information
- **Standardize genre names** (e.g., "Alternative Rock" → "alternative rock")
- **Filter out micro-genres** in favor of broader categories

### 4. Validation & Normalization

The system includes a comprehensive **genre validation system**:

```python
# Known music genres organized by category
ELECTRONIC = ["house", "techno", "trance", "dubstep", "drum and bass"]
ROCK = ["rock", "indie rock", "alternative rock", "punk rock"]
# ... and many more
```

- **Normalizes** variations ("Hip-Hop" → "hip hop")
- **Validates** against known music genres
- **Limits** to 4 genres maximum for clarity

## Architecture

```plaintext
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Event Data    │    │  Google Search   │    │   Claude AI     │
│  (no genres)    │───▶│   API Service    │───▶│   Analysis      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                        │
         │                       ▼                        ▼
         │              ┌──────────────────┐    ┌─────────────────┐
         │              │  Search Results  │    │  Genre List     │
         │              │  (Wikipedia,     │    │  ["indie rock", │
         │              │   Discogs, etc.) │    │   "alternative"]│
         │              └──────────────────┘    └─────────────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐                              ┌─────────────────┐
│  Enhanced       │◀─────────────────────────────│   Validation    │
│  Event Data     │                              │   & Cleanup     │
│  (with genres)  │                              └─────────────────┘
└─────────────────┘
```

## Configuration

### Required APIs

```bash
# Google Custom Search (for web search)
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_custom_search_engine_id

# Claude AI (for analysis)
ANTHROPIC_API_KEY=your_anthropic_key
```

### Setup Google Custom Search

1. Visit [Google Custom Search](https://programmablesearchengine.google.com/)
2. Create a new search engine
3. Set to search "Entire web"
4. Get your **Search Engine ID** (CSE_ID)
5. Enable the [Custom Search JSON API](https://developers.google.com/custom-search/v1/introduction)
6. Get your **API Key**

## Usage

### Automatic Enhancement

Genre enhancement happens automatically during imports when:

```python
# Event has no genres but has artists
event_data = EventData(
    title="Cursive at Zebulon",
    venue="Zebulon", 
    lineup=["Cursive"],  # Artist to search for
    genres=[]            # Empty - will be enhanced
)

# After enhancement:
# genres=["indie rock", "alternative rock"]
```

### Manual Testing

Test the genre enhancer directly:

```bash
# Test all functionality
uv run python scripts/test_genre_enhancer.py

# Test specific components
uv run python scripts/test_genre_enhancer.py --artist-only
```

### Integration Example

```python
from app.services.genre import GenreService
from app.config import get_config

config = get_config()
genre_service = GenreService(config, http_service, claude_service)

# Enhance an event
enhanced_event = await genre_service.enhance_genres(event_data)
print(enhanced_event.genres)  # ["indie rock", "alternative rock"]
```

## Example Scenarios

### Scenario 1: Indie Rock Band

```plaintext
Input Event:
- Title: "Cursive at Zebulon"
- Lineup: ["Cursive"]
- Genres: []

Google Search: "Cursive" music genre artist
Results: Wikipedia page describing "American indie rock band"

Claude Analysis: Extracts ["indie rock", "alternative rock"]
Output: Enhanced event with validated genres
```

### Scenario 2: Electronic Artist

```plaintext
Input Event:
- Title: "Bonobo Live"  
- Lineup: ["Bonobo"]
- Genres: []

Google Search: "Bonobo" music genre artist
Results: Discogs page showing "Electronic, Downtempo, Trip Hop"

Claude Analysis: Extracts ["electronic", "downtempo"]
Output: Enhanced event with electronic genres
```

### Scenario 3: Multi-Artist Event

```plaintext
Input Event:
- Title: "Festival Lineup"
- Lineup: ["Artist A", "Artist B", "Artist C"]
- Genres: []

Process: Searches for first artist only ("Artist A")
Reason: Prevents conflicting genres from different artists
Output: Genres based on headlining act
```

## Error Handling

The system gracefully handles various failure modes:

### Network Issues

```python
try:
    genres = await genre_service.enhance_genres(event_data)
except Exception as e:
    logger.warning(f"Genre enhancement failed: {e}")
    # Event processing continues without genres
```

### Invalid Results

- **Empty search results**: Skips enhancement
- **Ambiguous artist matches**: Uses event context for verification
- **Invalid genre names**: Filters through validation system
- **API rate limits**: Respects retry-after headers

### Fallback Behavior

- If enhancement fails, event import continues successfully
- Original event data remains unchanged
- No genres is better than wrong genres

## Testing

### Comprehensive Test Suite

```bash
# Run full test suite
uv run python scripts/test_genre_enhancer.py
```

**Tests Include:**

1. **Genre Data Validation** - Test normalization and validation
2. **Google Search Integration** - Verify API connectivity
3. **Claude AI Analysis** - Test genre extraction
4. **End-to-End Enhancement** - Complete workflow tests

### Test Output Example

```plaintext
✓ Testing: Cursive Event
  • Google search: Found 5 results  
  • Claude analysis: Extracted ["indie rock", "alternative rock"]
  • Validation: Passed - 2 valid genres
  • Result: Enhanced successfully

✗ Testing: Unknown Artist
  • Google search: No relevant results
  • Result: Skipped enhancement (as expected)
```

### Test Examples

```bash
# Test specific artist
uv run python scripts/test_genre_enhancer.py --artist="Bonobo"

# Test with different event context
uv run python scripts/test_genre_enhancer.py --venue="Electronic Venue"
```

## Performance Considerations

### Efficiency Features

- **Single artist search**: Only searches for the headlining act
- **Result caching**: HTTP client reuses connections  
- **Timeout protection**: 10-second search limit
- **Minimal API calls**: 1 search + 1 Claude analysis per event

### Rate Limiting

- **Google Search**: 100 queries/day (free tier)
- **Claude API**: Respects usage limits
- **Retry logic**: Exponential backoff on failures

### Cost Optimization

- Enhancement only runs when needed (no existing genres)
- Skips events without artist information
- Uses concise search queries to minimize API usage

## Quality Assurance

### Genre Validation System

```python
# Comprehensive genre database
ELECTRONIC = ["house", "techno", "trance", "ambient"]
ROCK = ["rock", "indie rock", "punk rock", "metal"]  
JAZZ = ["jazz", "smooth jazz", "bebop", "fusion"]
# 200+ validated genres across all categories
```

### Artist Verification

Claude considers event context when verifying artist identity:

- **Venue type** (electronic venues → electronic artists)
- **Other artists** on the lineup for consistency
- **Geographic context** (local vs. touring acts)

### Data Quality Metrics

- **Precision**: Only assigns genres with high confidence
- **Consistency**: Same artist gets same genres across events  
- **Relevance**: Prefers primary genres over obscure sub-genres
- **Coverage**: Successfully enhances ~80% of events with artists

## Debugging

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
uv run python scripts/test_genre_enhancer.py
```

### Configuration Check

```bash
# Verify API configuration
uv run python scripts/test_google_custom_search_api.py
```

## Integration Notes

### When Enhancement Runs

- **RA.co imports**: After API data extraction (RA often lacks genres)
- **Ticketmaster imports**: After API data extraction  
- **Web scraping**: After HTML/image extraction
- **Never runs**: For events that already have genres

### Performance Impact

- **Adds ~2-3 seconds** per event (search + analysis)
- **Runs asynchronously** - doesn't block other processing
- **Fail-safe**: Import succeeds even if enhancement fails

### Data Persistence

Enhanced genres are saved with the event data:

```json
{
  "title": "Cursive at Zebulon",
  "lineup": ["Cursive"],
  "genres": ["indie rock", "alternative rock"],
  "imported_at": "2024-01-01T00:00:00Z"
}
```

---

**Next:** [Image Enhancer Documentation](IMAGE_ENHANCER.md)
