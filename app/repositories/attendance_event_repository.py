"""
Attendance Event Repository - Data access layer for attendance events
"""
from typing import List
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from atams.db import BaseRepository
from app.models.attendance_event import AttendanceEvent


class AttendanceEventRepository(BaseRepository[AttendanceEvent]):
    def __init__(self):
        super().__init__(AttendanceEvent)

    def get_user_events(
        self,
        db: Session,
        user_id: int,
        target_date: date = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[AttendanceEvent]:
        """Get user's attendance events for specific date using ORM"""
        query = db.query(AttendanceEvent).filter(
            AttendanceEvent.ae_user_id == user_id
        )
        
        if target_date:
            query = query.filter(func.date(AttendanceEvent.ae_occurred_at) == target_date)
            
        return query.order_by(AttendanceEvent.ae_occurred_at.desc()).offset(skip).limit(limit).all()

    def count_user_events(self, db: Session, user_id: int, target_date: date = None) -> int:
        """Count user's events for specific date using native SQL"""
        if target_date:
            query = """
                SELECT COUNT(*) 
                FROM hris.attendance_events 
                WHERE ae_user_id = :user_id 
                AND DATE(ae_occurred_at) = :target_date
            """
            return self.execute_raw_sql_scalar(db, query, {"user_id": user_id, "target_date": target_date})
        else:
            query = """
                SELECT COUNT(*) 
                FROM hris.attendance_events 
                WHERE ae_user_id = :user_id
            """
            return self.execute_raw_sql_scalar(db, query, {"user_id": user_id})

    def create_event(self, db: Session, event_data: dict) -> AttendanceEvent:
        """Create attendance event and return the created object"""
        db_event = AttendanceEvent(**event_data)
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        return db_event

    def get_events_with_filters(
        self,
        db: Session,
        user_id: int = None,
        site_id: str = None,
        session_id: int = None,
        event_type: str = None,
        date_from: date = None,
        date_to: date = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AttendanceEvent]:
        """Get events with various filters using ORM"""
        query = db.query(AttendanceEvent)
        
        if user_id:
            query = query.filter(AttendanceEvent.ae_user_id == user_id)
        if site_id:
            query = query.filter(AttendanceEvent.ae_site_id == site_id)
        if session_id:
            query = query.filter(AttendanceEvent.ae_session_id == session_id)
        if event_type:
            query = query.filter(AttendanceEvent.ae_event_type == event_type)
        if date_from:
            query = query.filter(func.date(AttendanceEvent.ae_occurred_at) >= date_from)
        if date_to:
            query = query.filter(func.date(AttendanceEvent.ae_occurred_at) <= date_to)
            
        return query.order_by(AttendanceEvent.ae_occurred_at.desc()).offset(skip).limit(limit).all()