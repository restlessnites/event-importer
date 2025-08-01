"""Base integration classes."""

from __future__ import annotations

import importlib
import logging
from abc import ABC, abstractmethod
from typing import Any, final

from sqlalchemy.orm import Session

from app.core.errors import handle_errors_async
from app.shared.database.connection import get_db_session
from app.shared.database.models import EventCache, Submission

logger = logging.getLogger(__name__)


class Integration(ABC):
    """Abstract base class for all integrations"""

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the integration (e.g., 'ticketfairy')"""
        raise NotImplementedError

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if the integration is properly configured and enabled."""
        raise NotImplementedError

    def _load_module(self, module_type: str) -> Any | None:
        """Generic module loader for integration components."""
        module_paths = {
            "mcp": f"app.integrations.{self.name}.mcp.tools",
            "api": f"app.integrations.{self.name}.api.routes",
            "cli": f"app.integrations.{self.name}.cli.commands",
        }

        module_path = module_paths.get(module_type)
        if not module_path:
            return None

        try:
            return importlib.import_module(module_path)
        except ImportError:
            return None

    @final
    def get_mcp_tools(self) -> Any | None:
        """Dynamically load and return the MCP tools module, if it exists."""
        return self._load_module("mcp")

    @final
    def get_api_routes(self) -> Any | None:
        """Dynamically load and return the API routes module, if it exists."""
        return self._load_module("api")

    @final
    def get_cli_commands(self) -> Any | None:
        """Dynamically load and return the CLI commands module, if it exists."""
        return self._load_module("cli")


class BaseSelector(ABC):
    """Base class for event selection strategies"""

    @abstractmethod
    def select_events(
        self: BaseSelector,
        db: Session,
        service_name: str,
    ) -> list[EventCache]:
        """Select events based on specific criteria

        Args:
            db: Database session
            service_name: Name of the service (used for filtering submissions)
                         Some selectors may not use this parameter.
        """


class BaseTransformer(ABC):
    """Base class for data transformation"""

    @abstractmethod
    def transform(self: BaseTransformer, event_data: dict[str, Any]) -> dict[str, Any]:
        """Transform scraped event data to service-specific format"""


class BaseClient(ABC):
    """Base class for service API clients"""

    @abstractmethod
    async def submit(self: BaseClient, data: dict[str, Any]) -> dict[str, Any]:
        """Submit data to the external service"""


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

    @abstractmethod
    def _create_client(self: BaseSubmitter) -> BaseClient:
        """Create an instance of the API client."""

    @abstractmethod
    def _create_transformer(self: BaseSubmitter) -> BaseTransformer:
        """Create an instance of the data transformer."""

    @abstractmethod
    def _create_selectors(self: BaseSubmitter) -> dict[str, BaseSelector]:
        """Create a dictionary of available event selectors."""

    def _validate_selector(self: BaseSubmitter, selector_name: str) -> BaseSelector:
        """Validate selector exists and return it."""
        selector = self.selectors.get(selector_name)
        if not selector:
            error_msg = f"Selector '{selector_name}' not found for {self.service_name}"
            raise ValueError(error_msg)
        return selector

    def _fetch_events(
        self: BaseSubmitter, selector: BaseSelector, service_name: str
    ) -> list[int]:
        """Fetch event IDs using the selector."""
        with get_db_session() as db:
            events = selector.select_events(db, service_name)
            return [e.id for e in events]

    def _create_or_get_submission(
        self: BaseSubmitter, event: EventCache, db: Session
    ) -> Submission:
        """Create or get existing submission for event."""
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
        return submission

    def _handle_dry_run(
        self: BaseSubmitter, submission_id: int, event_id: int, source_url: str
    ) -> dict[str, Any]:
        """Handle dry run submission."""
        with get_db_session() as db:
            db.query(Submission).filter_by(id=submission_id).update(
                {"status": "dry_run", "response_data": {"dry_run": True}},
            )
            db.commit()
        return {
            "event_id": event_id,
            "submission_id": submission_id,
            "url": source_url,
            "status": "dry_run",
        }

    def _handle_submission_success(
        self: BaseSubmitter,
        submission_id: int,
        event_id: int,
        source_url: str,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle successful submission."""
        with get_db_session() as db:
            db.query(Submission).filter_by(id=submission_id).update(
                {"status": "success", "response_data": response},
            )
            db.commit()
        return {
            "event_id": event_id,
            "submission_id": submission_id,
            "url": source_url,
            "status": "success",
        }

    def _handle_submission_error(
        self: BaseSubmitter,
        submission_id: int | None,
        event_id: int,
        source_url: str | None,
        error: Exception,
    ) -> dict[str, Any]:
        """Handle submission error."""
        error_message = str(error)
        logger.error(
            f"Failed to process event {event_id} for {self.service_name}: {error_message}",
        )
        if submission_id:
            with get_db_session() as db:
                db.query(Submission).filter_by(id=submission_id).update(
                    {"status": "failed", "error_message": error_message},
                )
                db.commit()

        error_payload = {
            "event_id": event_id,
            "url": source_url or "N/A",
            "error": error_message,
        }
        if submission_id:
            error_payload["submission_id"] = submission_id
        return error_payload

    async def _process_single_event(
        self: BaseSubmitter, event_id: int, dry_run: bool
    ) -> dict[str, Any]:
        """Process a single event for submission."""
        submission_id = None
        source_url = None

        with get_db_session() as db:
            event = db.query(EventCache).get(event_id)
            if not event:
                logger.warning(f"Event {event_id} not found, skipping.")
                return {"type": "skip"}

            source_url = event.source_url
            submission = self._create_or_get_submission(event, db)
            submission_id = submission.id
            scraped_data = event.scraped_data

        # Transform event data
        transformed_data = self.transformer.transform(scraped_data)

        if dry_run:
            result = self._handle_dry_run(submission_id, event_id, source_url)
            return {"type": "success", "data": result}

        # Submit to service
        response = await self.client.submit(transformed_data)
        result = self._handle_submission_success(
            submission_id, event_id, source_url, response
        )
        return {"type": "success", "data": result}

    @handle_errors_async(reraise=True)
    async def submit_events(
        self: BaseSubmitter,
        selector_name: str = "unsubmitted",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Submit events to the integration.

        Args:
            selector_name: Name of selector to use
            dry_run: If True, don't actually submit

        Returns:
            Dictionary with submission results

        """
        selector = self._validate_selector(selector_name)
        event_ids = self._fetch_events(selector, self.service_name)

        if not event_ids:
            logger.info(
                f"No events found with selector: {selector_name} for service {self.service_name}",
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
            try:
                result = await self._process_single_event(event_id, dry_run)
                if result["type"] == "success":
                    results["submitted"].append(result["data"])
                elif result["type"] == "skip":
                    continue
            except (ValueError, TypeError, KeyError) as e:
                error_payload = self._handle_submission_error(None, event_id, None, e)
                results["errors"].append(error_payload)

        return results
