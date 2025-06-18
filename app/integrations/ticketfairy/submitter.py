from typing import Dict

from app.config import get_config
from ..base import BaseSubmitter, BaseClient, BaseTransformer, BaseSelector
from .client import TicketFairyClient
from .transformer import TicketFairyTransformer
from .selectors import (
    UnsubmittedSelector,
    FailedSelector,
    PendingSelector,
    AllEventsSelector,
    URLSelector
)


class TicketFairySubmitter(BaseSubmitter):
    """Complete submitter for TicketFairy integration"""
    
    def __init__(self):
        super().__init__()
    
    @property
    def service_name(self) -> str:
        return "ticketfairy"
    
    def _create_client(self) -> BaseClient:
        return TicketFairyClient()
    
    def _create_transformer(self) -> BaseTransformer:
        return TicketFairyTransformer()
    
    def _create_selectors(self) -> Dict[str, BaseSelector]:
        return {
            "unsubmitted": UnsubmittedSelector(),
            "failed": FailedSelector(),
            "pending": PendingSelector(),
            "all": AllEventsSelector(),
        }
    
    def get_url_selector(self, url: str) -> BaseSelector:
        """Create a URL-specific selector"""
        return URLSelector(url)
    
    async def submit_by_url(self, url: str, dry_run: bool = False) -> Dict:
        """Submit a specific event by URL"""
        # Create temporary selector
        url_selector = URLSelector(url)
        old_selectors = self.selectors.copy()
        self.selectors["url"] = url_selector
        
        try:
            result = await self.submit_events("url", dry_run)
            return result
        finally:
            # Restore original selectors
            self.selectors = old_selectors 