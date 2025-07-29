"""Statistics service for TicketFairy integration."""

from sqlalchemy import func, select

from app.shared.database.connection import get_db_session
from app.shared.database.models import EventCache, Submission


class TicketFairyStatistics:
    """Service for retrieving TicketFairy submission statistics."""

    def __init__(self):
        self.service_name = "ticketfairy"

    def get_submission_status(self) -> dict:
        """Get submission status statistics."""
        with get_db_session() as session:
            # Get total events in cache
            total_events = session.execute(select(func.count(EventCache.id))).scalar() or 0

            # Get submission counts by status
            status_counts = (
                session.query(Submission.status, func.count(Submission.id))
                .filter(Submission.service_name == self.service_name)
                .group_by(Submission.status)
                .all()
            )

            # Get unsubmitted count - fix SQLAlchemy warning by using select() explicitly
            submitted_event_ids_query = select(Submission.event_cache_id).where(
                Submission.service_name == self.service_name,
            )
            unsubmitted_count = (
                session.query(func.count(EventCache.id))
                .filter(~EventCache.id.in_(submitted_event_ids_query))
                .scalar()
            )

            return {
                "total_events": total_events,
                "unsubmitted_count": unsubmitted_count,
                "status_counts": status_counts
            }
