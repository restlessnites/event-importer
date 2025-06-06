#!/bin/bash

# ======================================================================
# COMPLETE RA.CO GRAPHQL API GUIDE
# ======================================================================

# Base URL and Headers
RA_API_URL="https://ra.co/graphql"
HEADERS=(
  -H 'accept: */*'
  -H 'accept-language: en-US,en;q=0.9'
  -H 'content-type: application/json'
  -H 'origin: https://ra.co'
  -H 'ra-content-language: en'
  -H 'referer: https://ra.co/events'
  -H 'sec-fetch-dest: empty'
  -H 'sec-fetch-mode: cors'
  -H 'sec-fetch-site: same-origin'
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
)

# Essential cookies (minimal working set)
COOKIES="locale=en; ra_content_language=en"

# For authenticated requests, add these cookies:
# COOKIES="locale=en; ra_content_language=en; ASP.NET_SessionId=f5cnx4oybvmrht25d5fgmkcq; sid=d12c1b1b-7477-4d3f-80b1-c4f6779462cf"

# ======================================================================
# 1. GET AREAS (Find Location IDs)
# ======================================================================

echo "=== Getting Areas ==="
curl "$RA_API_URL" \
  "${HEADERS[@]}" \
  -b "$COOKIES" \
  --data-raw '{
    "operationName": "GET_AREAS",
    "variables": {},
    "query": "query GET_AREAS {\n  areas {\n    id\n    name\n    country {\n      id\n      name\n    }\n  }\n}"
  }'

echo -e "\n\n"

# ======================================================================
# 2. GET EVENT LISTINGS (Paginated, Historical Data)
# ======================================================================

echo "=== Getting Event Listings (Page 1) ==="
curl "$RA_API_URL" \
  "${HEADERS[@]}" \
  -b "$COOKIES" \
  --data-raw '{
    "operationName": "GET_EVENT_LISTINGS",
    "variables": {
      "pageSize": 20,
      "page": 1
    },
    "query": "query GET_EVENT_LISTINGS($pageSize: Int, $page: Int) {\n  eventListings(pageSize: $pageSize, page: $page) {\n    data {\n      id\n      event {\n        id\n        title\n        date\n        venue {\n          name\n          area {\n            name\n            country {\n              name\n            }\n          }\n        }\n      }\n    }\n  }\n}"
  }'

echo -e "\n\n"

# ======================================================================
# 3. GET SINGLE EVENT (Complete Details)
# ======================================================================

echo "=== Getting Single Event (Full Details) ==="
curl "$RA_API_URL" \
  "${HEADERS[@]}" \
  -b "$COOKIES" \
  --data-raw '{
    "operationName": "GET_FULL_EVENT",
    "variables": {
      "id": "2141090"
    },
    "query": "query GET_FULL_EVENT($id: ID!) {\n  event(id: $id) {\n    id\n    title\n    content\n    date\n    startTime\n    endTime\n    contentUrl\n    interestedCount\n    isSaved\n    isInterested\n    cost\n    flyerFront\n    newEventForm\n    queueItEnabled\n    venue {\n      id\n      name\n      contentUrl\n      live\n      area {\n        id\n        name\n        country {\n          id\n          name\n        }\n      }\n    }\n    artists {\n      id\n      name\n      contentUrl\n    }\n    promoters {\n      id\n      name\n      contentUrl\n    }\n    genres {\n      id\n      name\n    }\n    images {\n      id\n      filename\n      alt\n      type\n      crop\n    }\n  }\n}"
  }'

echo -e "\n\n"

# ======================================================================
# 4. GET PROMOTER EVENTS (Known Working Pattern)
# ======================================================================

echo "=== Getting Promoter Events (6AM Group - LA Events) ==="
curl "$RA_API_URL" \
  "${HEADERS[@]}" \
  -b "$COOKIES" \
  --data-raw '{
    "operationName": "GET_PROMOTER_EVENTS",
    "variables": {
      "id": "27171"
    },
    "query": "query GET_PROMOTER_EVENTS($id: ID!) {\n  promoter(id: $id) {\n    id\n    name\n    logoUrl\n    blurb\n    contentUrl\n    isFollowing\n    events(limit: 20, type: LATEST) {\n      id\n      title\n      interestedCount\n      isSaved\n      isInterested\n      date\n      contentUrl\n      flyerFront\n      queueItEnabled\n      newEventForm\n      images {\n        id\n        filename\n        alt\n        type\n        crop\n      }\n      venue {\n        id\n        name\n        contentUrl\n        live\n        area {\n          id\n          name\n          country {\n            id\n            name\n          }\n        }\n      }\n      artists {\n        id\n        name\n        contentUrl\n      }\n      promoters {\n        id\n        name\n        contentUrl\n      }\n      cost\n      genres {\n        id\n        name\n      }\n    }\n  }\n}"
  }'

echo -e "\n\n"

# ======================================================================
# 5. HELP SCOUT CONFIGS (Working Example)
# ======================================================================

echo "=== Getting Help Scout Configs ==="
curl "$RA_API_URL" \
  "${HEADERS[@]}" \
  -b "$COOKIES" \
  --data-raw '{
    "operationName": "GET_HELPSCOUT_CONFIGS",
    "variables": {},
    "query": "query GET_HELPSCOUT_CONFIGS {\n  helpScoutConfigs {\n    screen\n    url\n    helpScoutBeacon {\n      beaconId\n      name\n      customFields {\n        fieldId\n      }\n    }\n  }\n}"
  }'

echo -e "\n\n"

# ======================================================================
# KEY FINDINGS & IMPORTANT NOTES
# ======================================================================

cat << 'EOF'
======================================================================
KEY FINDINGS & IMPORTANT NOTES
======================================================================

WORKING QUERIES:
✅ areas - Get location/area IDs
✅ eventListings(pageSize, page) - Paginated events (mostly historical)
✅ event(id: ID!) - Single event with full details including content
✅ promoter(id: ID!).events(limit, type: LATEST) - Events by promoter
✅ helpScoutConfigs - Help/support configs

IMPORTANT AREA IDS:
- Los Angeles: "23"
- San Diego: "309" 
- San Jose: "552"
- California: "308"
- Palm Springs: "596"

KNOWN LA EVENT IDS:
- 2141090: "RE/FORM: Risa Taniguchi, SOLëM, TonalTheory & Xiorro"
- 2141093: "WORK: 30 Years of Sonic Groove ft Adam X, Axkan, Frankie Bones & Mike Parker"
- 2175498: "The Cave x 6AM present Brutalism (a night of Techno)"
- 2154601: "WORK presents RAW 10 Years"
- 2133281: "WORK presents: Matrixxman [4 Hour Set] & Mesmé"

KNOWN LA PROMOTER IDS:
- 27171: "6AM Group" (Primary LA electronic music promoter)
- 32211: "Dirty Epic"
- 70754: "Synthetik Minds"

FIELD STRUCTURES:
- eventListings -> data[] -> event -> (event fields)
- event -> (direct event fields including 'content' for description)
- promoter -> events[] -> (event fields)

AUTHENTICATION:
- Basic queries work with minimal cookies
- Full access may require session cookies:
  ASP.NET_SessionId, sid, plus tracking cookies

EVENT QUERY TYPE ENUM:
- LATEST (confirmed working)
- Others may exist but not tested

LIMITATIONS DISCOVERED:
❌ eventListings doesn't support area/location filtering
❌ events(limit, type) returns empty results without proper session
❌ No direct search functionality found
❌ Most data appears to be historical unless using specific event IDs

STRATEGIES FOR LA EVENTS:
1. Use promoter(id: "27171") for 6AM Group LA events
2. Query specific event IDs if known
3. Parse eventListings and filter client-side
4. Use venue.area.name = "Los Angeles" for filtering

EOF