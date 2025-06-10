#!/usr/bin/env -S uv run python
"""Test script for RA.co GraphQL API exploration with CLI output."""

import asyncio
from typing import Dict, Any

from app.shared.http import get_http_service, close_http_service
from app.interfaces.cli import get_cli


class RAGraphQLTester:
    """Test RA.co GraphQL API functionality."""

    def __init__(self):
        self.api_url = "https://ra.co/graphql"
        self.headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": "https://ra.co",
            "ra-content-language": "en",
            "referer": "https://ra.co/events",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }
        self.cookies = "locale=en; ra_content_language=en"
        self.http = get_http_service()

    async def make_graphql_request(
        self, operation_name: str, query: str, variables: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make a GraphQL request to RA.co."""
        payload = {
            "operationName": operation_name,
            "variables": variables or {},
            "query": query,
        }

        # Add cookies header
        headers = self.headers.copy()
        headers["cookie"] = self.cookies

        response = await self.http.post_json(
            self.api_url, service="RA", headers=headers, json=payload
        )

        return response

    async def test_get_areas(self, cli) -> Dict[str, Any]:
        """Test GET_AREAS query to find location IDs."""
        cli.section("1. GET AREAS (Find Location IDs)")

        query = """
        query GET_AREAS {
          areas {
            id
            name
            country {
              id
              name
            }
          }
        }
        """

        try:
            with cli.spinner("Fetching areas"):
                response = await self.make_graphql_request("GET_AREAS", query)

            if "data" in response and response["data"].get("areas"):
                areas = response["data"]["areas"]
                cli.success(f"Found {len(areas)} areas")

                # Show some interesting areas (CA ones)
                ca_areas = [
                    a
                    for a in areas
                    if a.get("country", {}).get("name") == "United States"
                    and any(
                        city in a.get("name", "")
                        for city in [
                            "Los Angeles",
                            "San Diego",
                            "San Francisco",
                            "Oakland",
                        ]
                    )
                ]

                if ca_areas:
                    cli.info("California areas found:")
                    results = []
                    for area in ca_areas[:10]:  # Show top 10
                        results.append(
                            {
                                "ID": area["id"],
                                "Name": area["name"],
                                "Country": area.get("country", {}).get(
                                    "name", "Unknown"
                                ),
                            }
                        )
                    cli.table(results, title="California Areas")

                return response
            else:
                cli.error("No areas data in response")
                cli.json(response, title="Raw Response")
                return response

        except Exception as e:
            cli.error(f"GET_AREAS failed: {e}")
            return {"error": str(e)}

    async def test_get_event_listings(self, cli) -> Dict[str, Any]:
        """Test GET_EVENT_LISTINGS query for paginated events."""
        cli.section("2. GET EVENT LISTINGS (Paginated, Historical Data)")

        query = """
        query GET_EVENT_LISTINGS($pageSize: Int, $page: Int) {
          eventListings(pageSize: $pageSize, page: $page) {
            data {
              id
              event {
                id
                title
                date
                venue {
                  name
                  area {
                    name
                    country {
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {"pageSize": 20, "page": 1}

        try:
            with cli.spinner("Fetching event listings"):
                response = await self.make_graphql_request(
                    "GET_EVENT_LISTINGS", query, variables
                )

            if "data" in response and response["data"].get("eventListings", {}).get(
                "data"
            ):
                listings = response["data"]["eventListings"]["data"]
                cli.success(f"Found {len(listings)} event listings")

                # Show some events
                results = []
                for listing in listings[:5]:  # Show first 5
                    event = listing.get("event", {})
                    venue = event.get("venue", {})
                    area = venue.get("area", {})

                    results.append(
                        {
                            "Event ID": event.get("id", "N/A"),
                            "Title": event.get("title", "No title")[:40],
                            "Date": event.get("date", "No date"),
                            "Venue": venue.get("name", "No venue")[:20],
                            "Location": area.get("name", "No location"),
                        }
                    )

                cli.table(results, title="Recent Event Listings")
                return response
            else:
                cli.error("No event listings in response")
                cli.json(response, title="Raw Response")
                return response

        except Exception as e:
            cli.error(f"GET_EVENT_LISTINGS failed: {e}")
            return {"error": str(e)}

    async def test_get_single_event(
        self, cli, event_id: str = "2141090"
    ) -> Dict[str, Any]:
        """Test GET_FULL_EVENT query for complete event details."""
        cli.section(f"3. GET SINGLE EVENT (Complete Details) - ID: {event_id}")

        query = """
        query GET_FULL_EVENT($id: ID!) {
          event(id: $id) {
            id
            title
            content
            date
            startTime
            endTime
            contentUrl
            interestedCount
            isSaved
            isInterested
            cost
            flyerFront
            newEventForm
            queueItEnabled
            venue {
              id
              name
              contentUrl
              live
              area {
                id
                name
                country {
                  id
                  name
                }
              }
            }
            artists {
              id
              name
              contentUrl
            }
            promoters {
              id
              name
              contentUrl
            }
            genres {
              id
              name
            }
            images {
              id
              filename
              alt
              type
              crop
            }
          }
        }
        """

        variables = {"id": event_id}

        try:
            with cli.spinner(f"Fetching event {event_id}"):
                response = await self.make_graphql_request(
                    "GET_FULL_EVENT", query, variables
                )

            if "data" in response and response["data"].get("event"):
                event = response["data"]["event"]
                cli.success("Event details retrieved successfully")

                # Show key event details
                details = {
                    "Title": event.get("title", "No title"),
                    "Date": event.get("date", "No date"),
                    "Start Time": event.get("startTime", "No time"),
                    "Venue": event.get("venue", {}).get("name", "No venue"),
                    "Location": event.get("venue", {})
                    .get("area", {})
                    .get("name", "No location"),
                    "Cost": event.get("cost", "No cost info"),
                    "Artists": len(event.get("artists", [])),
                    "Genres": len(event.get("genres", [])),
                    "Images": len(event.get("images", [])),
                }

                cli.table([details], title="Event Summary")

                # Show artists if any
                if event.get("artists"):
                    artist_list = [
                        {"Name": a["name"], "ID": a["id"]} for a in event["artists"][:5]
                    ]
                    cli.table(artist_list, title="Artists (Top 5)")

                # Show description snippet
                if event.get("content"):
                    content = (
                        event["content"][:200] + "..."
                        if len(event["content"]) > 200
                        else event["content"]
                    )
                    cli.info(f"Description: {content}")

                return response
            else:
                cli.error(f"Event {event_id} not found")
                cli.json(response, title="Raw Response")
                return response

        except Exception as e:
            cli.error(f"GET_FULL_EVENT failed: {e}")
            return {"error": str(e)}

    async def test_get_promoter_events(
        self, cli, promoter_id: str = "27171"
    ) -> Dict[str, Any]:
        """Test GET_PROMOTER_EVENTS query for 6AM Group LA events."""
        cli.section(f"4. GET PROMOTER EVENTS (ID: {promoter_id} - 6AM Group)")

        query = """
        query GET_PROMOTER_EVENTS($id: ID!) {
          promoter(id: $id) {
            id
            name
            logoUrl
            blurb
            contentUrl
            isFollowing
            events(limit: 20, type: LATEST) {
              id
              title
              interestedCount
              isSaved
              isInterested
              date
              contentUrl
              flyerFront
              queueItEnabled
              newEventForm
              images {
                id
                filename
                alt
                type
                crop
              }
              venue {
                id
                name
                contentUrl
                live
                area {
                  id
                  name
                  country {
                    id
                    name
                  }
                }
              }
              artists {
                id
                name
                contentUrl
              }
              promoters {
                id
                name
                contentUrl
              }
              cost
              genres {
                id
                name
              }
            }
          }
        }
        """

        variables = {"id": promoter_id}

        try:
            with cli.spinner(f"Fetching promoter {promoter_id} events"):
                response = await self.make_graphql_request(
                    "GET_PROMOTER_EVENTS", query, variables
                )

            if "data" in response and response["data"].get("promoter"):
                promoter = response["data"]["promoter"]
                events = promoter.get("events", [])

                cli.success(f"Promoter: {promoter.get('name', 'Unknown')}")
                cli.info(f"Found {len(events)} events")

                if events:
                    # Show event summary
                    results = []
                    for event in events[:10]:  # Show first 10
                        venue = event.get("venue", {})
                        area = venue.get("area", {})
                        artists = event.get("artists", [])

                        results.append(
                            {
                                "Event ID": event.get("id", "N/A"),
                                "Title": event.get("title", "No title")[:30],
                                "Date": event.get("date", "No date"),
                                "Venue": venue.get("name", "No venue")[:20],
                                "Artists": len(artists),
                                "Location": area.get("name", "No location"),
                            }
                        )

                    cli.table(results, title="Recent Promoter Events")
                else:
                    cli.warning("No events found for this promoter")

                return response
            else:
                cli.error(f"Promoter {promoter_id} not found")
                cli.json(response, title="Raw Response")
                return response

        except Exception as e:
            cli.error(f"GET_PROMOTER_EVENTS failed: {e}")
            return {"error": str(e)}

    async def test_help_scout_configs(self, cli) -> Dict[str, Any]:
        """Test GET_HELPSCOUT_CONFIGS query."""
        cli.section("5. HELP SCOUT CONFIGS (Working Example)")

        query = """
        query GET_HELPSCOUT_CONFIGS {
          helpScoutConfigs {
            screen
            url
            helpScoutBeacon {
              beaconId
              name
              customFields {
                fieldId
              }
            }
          }
        }
        """

        try:
            with cli.spinner("Fetching Help Scout configs"):
                response = await self.make_graphql_request(
                    "GET_HELPSCOUT_CONFIGS", query
                )

            if "data" in response and response["data"].get("helpScoutConfigs"):
                configs = response["data"]["helpScoutConfigs"]
                cli.success(f"Found {len(configs)} Help Scout configurations")

                # Show config summary
                results = []
                for config in configs:
                    beacon = config.get("helpScoutBeacon", {})
                    results.append(
                        {
                            "Screen": config.get("screen", "Unknown"),
                            "URL": config.get("url", "No URL")[:40],
                            "Beacon ID": beacon.get("beaconId", "No ID"),
                            "Beacon Name": beacon.get("name", "No name"),
                        }
                    )

                cli.table(results, title="Help Scout Configurations")
                return response
            else:
                cli.error("No Help Scout configs in response")
                cli.json(response, title="Raw Response")
                return response

        except Exception as e:
            cli.error(f"GET_HELPSCOUT_CONFIGS failed: {e}")
            return {"error": str(e)}

    def show_findings_summary(self, cli):
        """Show key findings and notes."""
        cli.section("KEY FINDINGS & IMPORTANT NOTES")

        cli.info("✅ WORKING QUERIES:")
        working_queries = [
            "areas - Get location/area IDs",
            "eventListings(pageSize, page) - Paginated events (mostly historical)",
            "event(id: ID!) - Single event with full details including content",
            "promoter(id: ID!).events(limit, type: LATEST) - Events by promoter",
            "helpScoutConfigs - Help/support configs",
        ]

        for query in working_queries:
            cli.info(f"  • {query}")

        cli.console.print()
        cli.info("🗺️ IMPORTANT AREA IDS:")
        areas = [
            ("Los Angeles", "23"),
            ("San Diego", "309"),
            ("San Jose", "552"),
            ("California", "308"),
            ("Palm Springs", "596"),
        ]

        area_results = [
            {"Location": name, "Area ID": area_id} for name, area_id in areas
        ]
        cli.table(area_results, title="Key California Area IDs")

        cli.info("🎵 KNOWN LA PROMOTER IDS:")
        promoters = [
            ("6AM Group", "27171", "Primary LA electronic music promoter"),
            ("Dirty Epic", "32211", ""),
            ("Synthetik Minds", "70754", ""),
        ]

        promoter_results = [
            {"Promoter": name, "ID": pid, "Notes": notes}
            for name, pid, notes in promoters
        ]
        cli.table(promoter_results, title="Known LA Promoter IDs")

        cli.console.print()
        cli.warning("❌ LIMITATIONS DISCOVERED:")
        limitations = [
            "eventListings doesn't support area/location filtering",
            "events(limit, type) returns empty results without proper session",
            "No direct search functionality found",
            "Most data appears to be historical unless using specific event IDs",
        ]

        for limitation in limitations:
            cli.warning(f"  • {limitation}")

        cli.console.print()
        cli.info("🎯 STRATEGIES FOR LA EVENTS:")
        strategies = [
            'Use promoter(id: "27171") for 6AM Group LA events',
            "Query specific event IDs if known",
            "Parse eventListings and filter client-side",
            'Use venue.area.name = "Los Angeles" for filtering',
        ]

        for strategy in strategies:
            cli.info(f"  • {strategy}")


async def main():
    """Run all RA.co GraphQL API tests."""
    cli = get_cli()

    cli.header(
        "RA.co GraphQL API Test Suite", "Testing all known working queries and patterns"
    )

    tester = RAGraphQLTester()
    results = {}

    try:
        # Start capturing errors
        with cli.error_capture.capture():
            # Test all queries
            results["areas"] = await tester.test_get_areas(cli)
            await asyncio.sleep(1)  # Be nice to the API

            results["event_listings"] = await tester.test_get_event_listings(cli)
            await asyncio.sleep(1)

            results["single_event"] = await tester.test_get_single_event(cli)
            await asyncio.sleep(1)

            results["promoter_events"] = await tester.test_get_promoter_events(cli)
            await asyncio.sleep(1)

            results["help_scout"] = await tester.test_help_scout_configs(cli)

        # Show summary of findings
        tester.show_findings_summary(cli)

        # Overall test summary
        cli.rule("Test Summary")
        successful_tests = sum(1 for r in results.values() if "error" not in r)
        total_tests = len(results)

        cli.success(f"Completed {successful_tests}/{total_tests} tests successfully")

        if successful_tests < total_tests:
            cli.warning("Some tests failed - check the error details above")

        # Show any captured errors
        if cli.error_capture.has_errors() or cli.error_capture.has_warnings():
            cli.show_captured_errors("Issues During Tests")

    except KeyboardInterrupt:
        cli.warning("\nTests interrupted by user")
    except Exception as e:
        cli.error(f"Test suite failed: {e}")
        import traceback

        cli.code(traceback.format_exc(), "python", "Exception Traceback")
    finally:
        # Clean up
        with cli.spinner("Cleaning up connections"):
            await close_http_service()


if __name__ == "__main__":
    asyncio.run(main())
