from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.shared.database.models import EventCache, Submission
from app.shared.database.connection import get_db_session


class StatisticsService:
    """Service for generating various statistics about events and submissions"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session
    
    def _get_session(self) -> Session:
        """Get database session, either provided or create new one"""
        if self.db_session:
            return self.db_session
        return get_db_session()
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get core event statistics without integration dependencies"""
        with self._get_session() as db:
            # Basic event counts
            total_events = db.query(EventCache).count()
            
            # Recent activity (today)
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            events_today = db.query(EventCache).filter(
                EventCache.scraped_at >= today_start
            ).count()
            
            # This week
            week_start = today_start.replace(day=today_start.day - today_start.weekday())
            events_this_week = db.query(EventCache).filter(
                EventCache.scraped_at >= week_start
            ).count()
            
            # Events by status (based on whether they have any submissions)
            events_with_submissions = db.query(EventCache).join(Submission).distinct().count()
            events_without_submissions = total_events - events_with_submissions
            
            return {
                "total_events": total_events,
                "events_today": events_today,
                "events_this_week": events_this_week,
                "events_with_submissions": events_with_submissions,
                "events_without_submissions": events_without_submissions,
                "last_updated": datetime.now().isoformat()
            }
    
    def get_submission_statistics(self) -> Dict[str, Any]:
        """Get submission statistics (integration-related data)"""
        with self._get_session() as db:
            total_submissions = db.query(Submission).count()
            
            if total_submissions == 0:
                return {
                    "total_submissions": 0,
                    "by_status": {},
                    "by_service": {},
                    "success_rate": 0.0,
                    "last_updated": datetime.now().isoformat()
                }
            
            # Submissions by status
            status_counts = db.query(
                Submission.status,
                func.count(Submission.id).label('count')
            ).group_by(Submission.status).all()
            
            by_status = {status: count for status, count in status_counts}
            
            # Submissions by service
            service_counts = db.query(
                Submission.service_name,
                func.count(Submission.id).label('count')
            ).group_by(Submission.service_name).all()
            
            by_service = {service: count for service, count in service_counts}
            
            # Success rate
            successful = by_status.get('success', 0)
            success_rate = (successful / total_submissions) * 100 if total_submissions > 0 else 0.0
            
            return {
                "total_submissions": total_submissions,
                "by_status": by_status,
                "by_service": by_service,
                "success_rate": round(success_rate, 2),
                "last_updated": datetime.now().isoformat()
            }
    
    def get_combined_statistics(self) -> Dict[str, Any]:
        """Get all statistics combined"""
        event_stats = self.get_event_statistics()
        submission_stats = self.get_submission_statistics()
        
        return {
            "events": event_stats,
            "submissions": submission_stats,
            "generated_at": datetime.now().isoformat()
        }
    
    def get_event_trends(self, days: int = 7) -> Dict[str, Any]:
        """Get event trends over the specified number of days"""
        with self._get_session() as db:
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            
            daily_counts = []
            for i in range(days):
                day_start = start_date.replace(day=start_date.day - i)
                day_end = day_start.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                count = db.query(EventCache).filter(
                    and_(
                        EventCache.scraped_at >= day_start,
                        EventCache.scraped_at <= day_end
                    )
                ).count()
                
                daily_counts.append({
                    "date": day_start.strftime("%Y-%m-%d"),
                    "count": count
                })
            
            return {
                "period_days": days,
                "daily_counts": list(reversed(daily_counts)),
                "total_in_period": sum(day["count"] for day in daily_counts),
                "average_per_day": sum(day["count"] for day in daily_counts) / days if days > 0 else 0,
                "generated_at": datetime.now().isoformat()
            }
    
    def get_detailed_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics including trends"""
        return {
            **self.get_combined_statistics(),
            "trends": self.get_event_trends(),
            "trends_30_days": self.get_event_trends(30)
        } 