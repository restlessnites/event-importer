""" Base integration classes. """

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session

from app.errors import handle_errors_async

from ..shared.database.connection import get_db_session
from ..shared.database.models import EventCache, Submission

logger = logging.getLogger(__name__)


class BaseSelector(ABC):
    """Base class for event selection strategies"""

    @abstractmethod
    def select_events(
        self: BaseSelector, db: Session, service_name: str
    ) -> list[EventCache]:
        """Select events based on specific criteria"""
        pass


class BaseTransformer(ABC):
    """Base class for data transformation"""

    @abstractmethod
    def transform(self: BaseTransformer, event_data: dict[str, Any]) -> dict[str, Any]:
        """Transform scraped event data to service-specific format"""
        pass


class BaseClient(ABC):
    """Base class for service API clients"""

    @abstractmethod
    async def submit(self: BaseClient, data: dict[str, Any]) -> dict[str, Any]:
        """Submit data to the external service"""
        pass


class BaseSubmitter(ABC):
    """Base class for event submission integrations."""

    def __init__(self: BaseSubmitter) -> None:
        """Initialize submitter with client, transformer and selectors."""
        self.client = self._create_client()
        self.transformer = self._create_transformer()
        self.selectors = self._create_selectors()

    @property
    @abstractmethod
    def service_name(self: BaseSubmitter) -> str:
        """Name of the service for this integration."""
        pass

    @abstractmethod
    def _create_client(self: BaseSubmitter) -> BaseClient:
        """Create an instance of the API client."""
        pass

    @abstractmethod
    def _create_transformer(self: BaseSubmitter) -> BaseTransformer:
        """Create an instance of the data transformer."""
        pass

    @abstractmethod
    def _create_selectors(self: BaseSubmitter) -> dict[str, BaseSelector]:
        """Create a dictionary of available event selectors."""
        pass

    @handle_errors_async(reraise=True)
    async def submit_events(
        self: BaseSubmitter, selector_name: str = "unsubmitted", dry_run: bool = False
    ) -> dict[str, Any]:
        """
        Submit events to the integration.

        Args:
            selector_name: Name of selector to use
            dry_run: If True, don't actually submit

        Returns:
            Dictionary with submission results
        """
        selector = self.selectors.get(selector_name)
        if not selector:
            raise ValueError(
                f"Selector '{selector_name}' not found for {self.service_name}"
            )

        with get_db_session() as db:
            events = selector.select_events(db, self.service_name)
            event_ids = [e.id for e in events]

        if not event_ids:
            logger.info(
                f"No events found with selector: {selector_name} for service {self.service_name}"
            )
            return {
                "submitted": [],
                "errors": [],
                "total": 0,
                "selector": selector_name,
            }

        logger.info(f"Found {len(event_ids)} events to submit for {self.service_name}")
        results = {
            "submitted": [],
            "errors": [],
            "total": len(event_ids),
            "selector": selector_name,
        }

        for event_id in event_ids:
            submission_id = None
            source_url = None
            try:
                with get_db_session() as db:
                    event = db.query(EventCache).get(event_id)
                    if not event:
                        logger.warning(f"Event {event_id} not found, skipping.")
                        continue

                    source_url = event.source_url

                    submission = (
                        db.query(Submission)
                        .filter_by(
                            event_cache_id=event.id,
                            service_name=self.service_name,
                            status="pending",
                        )
                        .first()
                    )
                    if not submission:
                        submission = Submission(
                            event=event,
                            service_name=self.service_name,
                            status="pending",
                        )
                        db.add(submission)
                        db.commit()
                        db.refresh(submission)

                    submission_id = submission.id
                    scraped_data = event.scraped_data

                # Transform event data
                transformed_data = self.transformer.transform(scraped_data)

                if dry_run:
                    with get_db_session() as db:
                        db.query(Submission).filter_by(id=submission_id).update(
                            {"status": "dry_run", "response_data": {"dry_run": True}}
                        )
                        db.commit()
                    results["submitted"].append(
                        {
                            "event_id": event_id,
                            "submission_id": submission_id,
                            "url": source_url,
                            "status": "dry_run",
                        }
                    )
                    continue

                # Submit to service
                response = await self.client.submit(transformed_data)

                # Update submission with success
                with get_db_session() as db:
                    db.query(Submission).filter_by(id=submission_id).update(
                        {"status": "success", "response_data": response}
                    )
                    db.commit()
                results["submitted"].append(
                    {
                        "event_id": event_id,
                        "submission_id": submission_id,
                        "url": source_url,
                        "status": "success",
                    }
                )

            except Exception as e:
                error_message = str(e)
                logger.error(
                    f"Failed to process event {event_id} for {self.service_name}: {error_message}"
                )
                if submission_id:
                    with get_db_session() as db:
                        db.query(Submission).filter_by(id=submission_id).update(
                            {"status": "failed", "error_message": error_message}
                        )
                        db.commit()

                error_payload = {
                    "event_id": event_id,
                    "url": source_url or "N/A",
                    "error": error_message,
                }
                if submission_id:
                    error_payload["submission_id"] = submission_id
                results["errors"].append(error_payload)

        return results
