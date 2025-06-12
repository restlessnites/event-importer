from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import traceback
from tenacity import RetryError

from ..shared.database.models import EventCache, Submission
from app.errors import handle_errors_async, APIError
from app.models import Event
from app.schemas import EventData

import logging

logger = logging.getLogger(__name__)


class BaseSelector(ABC):
    """Base class for event selection strategies"""
    
    @abstractmethod
    def select_events(self, db: Session, service_name: str) -> List[EventCache]:
        """Select events based on specific criteria"""
        pass


class BaseTransformer(ABC):
    """Base class for data transformation"""
    
    @abstractmethod
    def transform(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform scraped event data to service-specific format"""
        pass


class BaseClient(ABC):
    """Base class for service API clients"""
    
    @abstractmethod
    async def submit(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit data to the external service"""
        pass


class BaseSubmitter(ABC):
    """Base class for event submission integrations."""

    def __init__(self, client: Any):
        """Initialize submitter with client."""
        self.client = client

    @abstractmethod
    async def transform_event(self, event: Event) -> Dict[str, Any]:
        """
        Transform event data for submission.

        Args:
            event: Event to transform

        Returns:
            Transformed data ready for submission
        """
        pass

    @handle_errors_async(reraise=True)
    async def submit_events(
        self, 
        selector_name: str = "unsubmitted", 
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Submit events to the integration.

        Args:
            selector_name: Name of selector to use
            dry_run: If True, don't actually submit

        Returns:
            Dictionary with submission results
        """
        # Get events to submit
        events = await Event.filter(selector=selector_name)
        if not events:
            logger.info(f"No events found with selector: {selector_name}")
            return {
                "submitted": [],
                "errors": [],
                "total": 0
            }

        logger.info(f"Found {len(events)} events to submit")
        results = {
            "submitted": [],
            "errors": [],
            "total": len(events)
        }

        # Process each event
        for event in events:
            try:
                # Create submission record
                submission = Submission(
                    event=event,
                    integration=self.client.__class__.__name__,
                    status="pending"
                )
                await submission.save()

                # Transform event data
                try:
                    transformed_data = await self.transform_event(event)
                except Exception as transform_error:
                    # Update submission with error
                    submission.status = "failed"
                    submission.error_message = str(transform_error)
                    await submission.save()

                    results["errors"].append({
                        "event_id": event.id,
                        "submission_id": submission.id,
                        "url": event.source_url,
                        "error": str(transform_error)
                    })
                    continue

                if dry_run:
                    # Update submission for dry run
                    submission.status = "dry_run"
                    submission.response_data = {"dry_run": True}
                    await submission.save()

                    results["submitted"].append({
                        "event_id": event.id,
                        "submission_id": submission.id,
                        "url": event.source_url,
                        "status": "dry_run"
                    })
                    continue

                # Submit to service
                try:
                    response = await self.client.submit(transformed_data)
                    
                    # Update submission with success
                    submission.status = "success"
                    submission.response_data = response
                    await submission.save()
                    
                    results["submitted"].append({
                        "event_id": event.id,
                        "submission_id": submission.id,
                        "url": event.source_url,
                        "status": "success"
                    })
                    
                except Exception as submit_error:
                    # Update submission with error
                    submission.status = "failed"
                    submission.error_message = str(submit_error)
                    await submission.save()
                    
                    results["errors"].append({
                        "event_id": event.id,
                        "submission_id": submission.id,
                        "url": event.source_url,
                        "error": str(submit_error)
                    })

            except Exception as event_error:
                results["errors"].append({
                    "event_id": event.id,
                    "url": event.source_url,
                    "error": str(event_error)
                })

        return results 