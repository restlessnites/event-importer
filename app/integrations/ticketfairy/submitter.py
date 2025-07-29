"""TicketFairy submitter."""

from __future__ import annotations

from typing import Any

from app.integrations.base import (
    BaseClient,
    BaseSelector,
    BaseSubmitter,
    BaseTransformer,
)
from app.integrations.ticketfairy.client import TicketFairyClient
from app.integrations.ticketfairy.selectors import (
    AllEventsSelector,
    FailedSelector,
    PendingSelector,
    UnsubmittedSelector,
    URLSelector,
)
from app.integrations.ticketfairy.transformer import TicketFairyTransformer


class TicketFairySubmitter(BaseSubmitter):
    """Complete submitter for TicketFairy integration"""

    def __init__(self: TicketFairySubmitter) -> None:
        super().__init__()

    @property
    def service_name(self: TicketFairySubmitter) -> str:
        return "ticketfairy"

    def _create_client(self: TicketFairySubmitter) -> BaseClient:
        return TicketFairyClient()

    def _create_transformer(self: TicketFairySubmitter) -> BaseTransformer:
        return TicketFairyTransformer()

    def _create_selectors(self: TicketFairySubmitter) -> dict[str, BaseSelector]:
        return {
            "unsubmitted": UnsubmittedSelector(),
            "failed": FailedSelector(),
            "pending": PendingSelector(),
            "all": AllEventsSelector(),
        }

    async def submit_by_url(
        self: TicketFairySubmitter,
        url: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Submit a specific event by URL"""
        # Create temporary selector
        url_selector = URLSelector(url)
        old_selectors = self.selectors.copy()
        self.selectors["url"] = url_selector

        try:
            return await self.submit_events("url", dry_run)
        finally:
            # Restore original selectors
            self.selectors = old_selectors
