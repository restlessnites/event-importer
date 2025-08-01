#!/usr/bin/env python3
"""Test TicketFairy dry run with debug logging."""

import asyncio

from app.integrations.ticketfairy.shared.debug_submitter import (
    DebugTicketFairySubmitter,
)


async def test_dry_run():
    """Test dry run with debug logging."""
    url = "https://ra.co/events/2213092"

    print("=== Testing TicketFairy Dry Run ===")
    print(f"URL: {url}")

    submitter = DebugTicketFairySubmitter()
    result = await submitter.submit_by_url(url, dry_run=True)

    print("\n=== Final Result ===")
    print(f"Submitted count: {len(result.get('submitted', []))}")
    if result.get("submitted"):
        for item in result["submitted"]:
            print(f"  - {item}")
    else:
        print("No events were selected for submission")


if __name__ == "__main__":
    asyncio.run(test_dry_run())
