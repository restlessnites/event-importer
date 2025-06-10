from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..shared.database.models import EventCache, Submission


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
    """Base class for integration submitters"""
    
    def __init__(self):
        self.client = self._create_client()
        self.transformer = self._create_transformer()
        self.selectors = self._create_selectors()
    
    @abstractmethod
    def _create_client(self) -> BaseClient:
        """Create the service client"""
        pass
    
    @abstractmethod
    def _create_transformer(self) -> BaseTransformer:
        """Create the data transformer"""
        pass
    
    @abstractmethod
    def _create_selectors(self) -> Dict[str, BaseSelector]:
        """Create available selectors"""
        pass
    
    @property
    @abstractmethod
    def service_name(self) -> str:
        """Name of the service this submitter handles"""
        pass
    
    async def submit_events(
        self, 
        selector_name: str = "unsubmitted", 
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Submit events using specified selector"""
        from ..shared.database.connection import get_db_session
        
        results = {
            "service": self.service_name,
            "selector": selector_name,
            "dry_run": dry_run,
            "submitted": [],
            "errors": [],
            "total": 0
        }
        
        with get_db_session() as db:
            # Get selector
            if selector_name not in self.selectors:
                raise ValueError(f"Unknown selector: {selector_name}")
            
            selector = self.selectors[selector_name]
            events = selector.select_events(db, self.service_name)
            results["total"] = len(events)
            
            for event in events:
                try:
                    # Transform data
                    transformed_data = self.transformer.transform(event.scraped_data)
                    
                    if dry_run:
                        results["submitted"].append({
                            "event_id": event.id,
                            "url": event.source_url,
                            "data": transformed_data
                        })
                        continue
                    
                    # Create submission record
                    submission = Submission(
                        event_cache_id=event.id,
                        service_name=self.service_name,
                        status="pending",
                        selection_criteria={"selector": selector_name}
                    )
                    db.add(submission)
                    db.flush()  # Get the ID
                    
                    try:
                        # Submit to service
                        response = await self.client.submit(transformed_data)
                        
                        # Update submission with success
                        submission.status = "success"
                        submission.response_data = response
                        
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