""" TicketFairy selectors. """

from __future__ import annotations

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ...shared.database.models import EventCache, Submission
from ..base import BaseSelector


class UnsubmittedSelector(BaseSelector):
    """Select events that have never been submitted to TicketFairy"""

    def select_events(
        self: UnsubmittedSelector, db: Session, service_name: str
    ) -> list[EventCache]:
        return (
            db.query(EventCache)
            .outerjoin(
                Submission,
                and_(
                    Submission.event_cache_id == EventCache.id,
                    Submission.service_name == service_name,
                ),
            )
            .filter(Submission.id is None)
            .all()
        )


class FailedSelector(BaseSelector):
    """Select events with failed submissions"""

    def select_events(
        self: FailedSelector, db: Session, service_name: str
    ) -> list[EventCache]:
        return (
            db.query(EventCache)
            .join(Submission)
            .filter(
                and_(
                    Submission.service_name == service_name,
                    Submission.status == "failed",
                )
            )
            .distinct()
            .all()
        )


class PendingSelector(BaseSelector):
    """Select events with pending submissions"""

    def select_events(
        self: PendingSelector, db: Session, service_name: str
    ) -> list[EventCache]:
        return (
            db.query(EventCache)
            .join(Submission)
            .filter(
                and_(
                    Submission.service_name == service_name,
                    Submission.status == "pending",
                )
            )
            .distinct()
            .all()
        )


class AllEventsSelector(BaseSelector):
    """Select all cached events"""

    def select_events(
        self: AllEventsSelector, db: Session, service_name: str
    ) -> list[EventCache]:
        return db.query(EventCache).all()


class URLSelector(BaseSelector):
    """Select specific event by URL"""

    def __init__(self: URLSelector, url: str) -> None:
        self.url = url

    def select_events(
        self: URLSelector, db: Session, service_name: str
    ) -> list[EventCache]:
        event = db.query(EventCache).filter(EventCache.source_url == self.url).first()
        return [event] if event else []
