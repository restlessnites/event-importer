#!/usr/bin/env -S uv run python
"""
Comprehensive test for the date parsing fix.
This script tests both the date parsing logic and imports the actual La Bamba event.
"""

from __future__ import annotations

import asyncio
import traceback
from datetime import datetime
from typing import TYPE_CHECKING

from dateutil import parser as date_parser

from app.core.router import Router
from app.schemas import EventData

if TYPE_CHECKING:
    pass

import pytest

from app.interfaces.cli import get_cli


def test_dateutil_directly() -> None:
    """Test dateutil behavior to understand the root cause."""
    cli = get_cli()

    cli.section("Testing dateutil directly")

    current_date = datetime.now()
    current_year = current_date.year

    cli.info(f"Current date: {current_date.strftime('%Y-%m-%d')}")
    cli.info(f"Current year: {current_year}")
    cli.console.print()

    test_input = "Sat, Jun 21"

    # Test 1: Default dateutil behavior
    cli.info(f"Test 1: dateutil.parse('{test_input}') - default behavior")
    try:
        result1 = date_parser.parse(test_input)
        cli.info(f"Result: {result1.strftime('%Y-%m-%d')} (year: {result1.year})")
    except Exception as e:
        cli.error(f"Failed: {e}")

    # Test 2: With current year as default
    cli.info(
        f"Test 2: dateutil.parse('{test_input}', default=datetime({current_year}, 1, 1))"
    )
    try:
        default_date = datetime(current_year, 1, 1)
        result2 = date_parser.parse(test_input, default=default_date)
        cli.info(f"Result: {result2.strftime('%Y-%m-%d')} (year: {result2.year})")
    except Exception as e:
        cli.error(f"Failed: {e}")

    # Test 3: With current date as default
    cli.info(f"Test 3: dateutil.parse('{test_input}', default=current_date)")
    try:
        result3 = date_parser.parse(test_input, default=current_date)
        cli.info(f"Result: {result3.strftime('%Y-%m-%d')} (year: {result3.year})")
    except Exception as e:
        cli.error(f"Failed: {e}")

    cli.console.print()


def test_fixed_eventdata_parsing() -> None:
    """Test the fixed EventData date parsing."""
    cli = get_cli()

    cli.section("Testing Fixed EventData Parsing")

    # Test various date formats that should all result in 2025-06-21
    test_cases = [
        ("Sat, Jun 21", "2025-06-21", "La Bamba format"),
        ("Saturday, June 21", "2025-06-21", "Full format"),
        ("June 21", "2025-06-21", "Month day only"),
        ("Jun 21", "2025-06-21", "Abbreviated month"),
        ("6/21", "2025-06-21", "Numeric format"),
        ("21 June", "2025-06-21", "Day month format"),
        # Past dates that should go to 2026
        ("January 15", "2026-01-15", "Past month (should be next year)"),
        ("March 10", "2026-03-10", "Past month (should be next year)"),
        # Explicit years should be preserved
        ("June 21, 2024", "2024-06-21", "Explicit 2024"),
        ("June 21, 2026", "2026-06-21", "Explicit 2026"),
    ]

    results = []

    for input_date, expected, description in test_cases:
        try:
            # Import here to get the latest version with the fix
            event = EventData(title="Test Event", date=input_date)
            actual = event.date

            status = "✅" if actual == expected else "❌"
            note = "" if actual == expected else f"Expected {expected}"

            results.append(
                {
                    "Input": input_date,
                    "Expected": expected,
                    "Actual": actual or "None",
                    "Status": status,
                    "Description": description,
                    "Note": note,
                }
            )

        except Exception as e:
            results.append(
                {
                    "Input": input_date,
                    "Expected": expected,
                    "Actual": f"ERROR: {e}",
                    "Status": "❌",
                    "Description": description,
                    "Note": "Parsing failed",
                }
            )

    cli.table(results, title="EventData Date Parsing Test Results")

    # Summary
    passed = sum(1 for r in results if r["Status"] == "✅")
    total = len(results)

    cli.console.print()
    if passed == total:
        cli.success(f"All {total} tests passed! 🎉")
    else:
        cli.warning(f"{passed}/{total} tests passed")
        failures = [r for r in results if r["Status"] == "❌"]
        for failure in failures:
            cli.error(f"  • {failure['Input']} → {failure['Note']}")


@pytest.mark.asyncio
async def test_la_bamba_import() -> None:
    """Test importing the actual La Bamba event."""
    cli = get_cli()

    cli.section("Testing La Bamba Event Import")

    url = "https://vidiotsfoundation.org/movies/la-bamba"
    cli.info(f"Importing: {url}")

    try:
        router = Router()

        with cli.spinner("Importing event"):
            result = await router.route_request(
                {
                    "url": url,
                    "timeout": 60,
                    "ignore_cache": True,  # Force fresh import to test parsing
                }
            )

        if result.get("success"):
            event_data = result["data"]
            date = event_data.get("date")
            title = event_data.get("title", "Unknown")
            venue = event_data.get("venue", "Unknown")

            cli.success("Import successful!")

            event_summary = {
                "Title": title,
                "Venue": venue,
                "Date": date,
                "Method": result.get("method_used", "Unknown"),
                "Import Time": f"{result.get('import_time', 0):.2f}s",
            }

            cli.table([event_summary], title="Event Import Results")

            # Check if date is correct
            if date == "2025-06-21":
                cli.success("✅ Date parsing is now CORRECT: 2025-06-21")
                cli.info("The fix worked! 🎉")
            elif date == "2024-06-21":
                cli.error("❌ Date is still wrong: 2024-06-21")
                cli.warning("The fix didn't work - need further investigation")
            else:
                cli.warning(f"⚠️ Unexpected date: {date}")

        else:
            cli.error(f"Import failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        cli.error(f"Import test failed: {e}")
        cli.code(traceback.format_exc(), "python", "Error Details")


async def main() -> None:
    """Run all tests."""
    cli = get_cli()

    cli.header(
        "Date Parsing Fix Verification", "Testing the comprehensive date parsing fix"
    )

    # Test 1: Direct dateutil behavior
    test_dateutil_directly()

    # Test 2: Fixed EventData parsing
    test_fixed_eventdata_parsing()

    # Test 3: Real event import
    await test_la_bamba_import()

    cli.rule("Test Complete")
    cli.success("All tests completed! Check the results above.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    except Exception as e:
        print(f"Test suite failed: {e}")
        import traceback

        traceback.print_exc()
