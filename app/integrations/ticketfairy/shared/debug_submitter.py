"""Debug submitter that uses verbose selector."""

from __future__ import annotations

from typing import Any

from app.integrations.ticketfairy.shared.submitter import TicketFairySubmitter
from app.integrations.ticketfairy.utils.debug_selector import DebugURLSelector


class DebugTicketFairySubmitter(TicketFairySubmitter):
    """Debug version with verbose logging."""

    async def submit_by_url(
        self: DebugTicketFairySubmitter,
        url: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Submit a specific event by URL with debug logging"""
        print("\n=== DebugTicketFairySubmitter.submit_by_url ===")
        print(f"URL: {url}")
        print(f"Dry run: {dry_run}")

        # Create debug selector
        url_selector = DebugURLSelector(url)
        old_selectors = self.selectors.copy()
        self.selectors["url"] = url_selector

        try:
            result = await self.submit_events("url", dry_run)
            print(f"\nSubmit result: {result}")
            return result
        finally:
            # Restore original selectors
            self.selectors = old_selectors
