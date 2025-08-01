"""TicketFairy selectors."""

from __future__ import annotations

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.integrations.base import BaseSelector
from app.shared.database.models import Event, Submission


class UnsubmittedSelector(BaseSelector):
    """Select events that have never been submitted to TicketFairy"""

    def select_events(
        self: UnsubmittedSelector,
        db: Session,
        service_name: str,
    ) -> list[Event]:
        return (
            db.query(Event)
            .outerjoin(
                Submission,
                and_(
                    Submission.event_cache_id == Event.id,
                    Submission.service_name == service_name,
                ),
            )
            .filter(Submission.id is None)
            .all()
        )


class FailedSelector(BaseSelector):
    """Select events with failed submissions"""

    def select_events(
        self: FailedSelector,
        db: Session,
        service_name: str,
    ) -> list[Event]:
        return (
            db.query(Event)
            .join(Submission)
            .filter(
                and_(
                    Submission.service_name == service_name,
                    Submission.status == "failed",
                ),
            )
            .distinct()
            .all()
        )


class PendingSelector(BaseSelector):
    """Select events with pending submissions"""

    def select_events(
        self: PendingSelector,
        db: Session,
        service_name: str,
    ) -> list[Event]:
        return (
            db.query(Event)
            .join(Submission)
            .filter(
                and_(
                    Submission.service_name == service_name,
                    Submission.status == "pending",
                ),
            )
            .distinct()
            .all()
        )


class AllEventsSelector(BaseSelector):
    """Select all cached events, optionally excluding already submitted ones"""

    def __init__(self, include_submitted: bool = True):
        self.include_submitted = include_submitted

    def select_events(
        self: AllEventsSelector,
        db: Session,
        service_name: str,
    ) -> list[Event]:
        if self.include_submitted:
            return db.query(Event).all()

        # Exclude events already submitted to this service
        return (
            db.query(Event)
            .outerjoin(
                Submission,
                and_(
                    Submission.event_cache_id == Event.id,
                    Submission.service_name == service_name,
                    Submission.status.in_(["success", "pending"]),
                ),
            )
            .filter(Submission.id.is_(None))
            .all()
        )


class URLSelector(BaseSelector):
    """Select specific event by URL, checking if already submitted"""

    def __init__(self: URLSelector, url: str, check_submitted: bool = True) -> None:
        self.url = url
        self.check_submitted = check_submitted

    def select_events(
        self: URLSelector,
        db: Session,
        service_name: str,
    ) -> list[Event]:
        event = db.query(Event).filter(Event.source_url == self.url).first()

        if not event:
            return []

        # If check_submitted is True, only return if not already submitted to this service
        if self.check_submitted:
            existing_submission = (
                db.query(Submission)
                .filter(
                    and_(
                        Submission.event_cache_id == event.id,
                        Submission.service_name == service_name,
                        Submission.status.in_(["success", "pending"]),
                    )
                )
                .first()
            )
            if existing_submission:
                return []  # Already submitted

        return [event]
