"""
Attendance Session Repository - Data access layer for attendance sessions
"""
from typing import Optional, List
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from atams.db import BaseRepository
from app.models.attendance_session import AttendanceSession


class AttendanceSessionRepository(BaseRepository[AttendanceSession]):
    def __init__(self):
        super().__init__(AttendanceSession)

    def get_open_session_today(self, db: Session, user_id: int, target_date: date = None) -> Optional[AttendanceSession]:
        """Get open session for user on specific date (default today) using ORM"""
        if target_date is None:
            target_date = date.today()
            
        return db.query(AttendanceSession).filter(
            and_(
                AttendanceSession.as_user_id == user_id,
                func.date(AttendanceSession.as_checkin_at) == target_date,
                AttendanceSession.as_status == "open"
            )
        ).first()

    def get_session_today(self, db: Session, user_id: int, target_date: date = None) -> Optional[AttendanceSession]:
        """Get any session (open or closed) for user on specific date using ORM"""
        if target_date is None:
            target_date = date.today()
            
        return db.query(AttendanceSession).filter(
            and_(
                AttendanceSession.as_user_id == user_id,
                func.date(AttendanceSession.as_checkin_at) == target_date
            )
        ).first()

    def get_user_sessions(self, db: Session, user_id: int, skip: int = 0, limit: int = 50) -> List[AttendanceSession]:
        """Get user's sessions with pagination using ORM"""
        return db.query(AttendanceSession).filter(
            AttendanceSession.as_user_id == user_id
        ).order_by(AttendanceSession.as_checkin_at.desc()).offset(skip).limit(limit).all()

    def get_sessions_with_filters(
        self,
        db: Session,
        user_id: int = None,
        site_id: str = None,
        date_from: date = None,
        date_to: date = None,
        status: str = None,
        skip: int = 0,
        limit: int = 100,
        sort: str = "desc"
    ) -> List[AttendanceSession]:
        """Get sessions with various filters using ORM"""
        query = db.query(AttendanceSession)
        
        if user_id:
            query = query.filter(AttendanceSession.as_user_id == user_id)
        if site_id:
            query = query.filter(AttendanceSession.as_site_id == site_id)
        if date_from:
            query = query.filter(func.date(AttendanceSession.as_checkin_at) >= date_from)
        if date_to:
            query = query.filter(func.date(AttendanceSession.as_checkin_at) <= date_to)
        if status:
            query = query.filter(AttendanceSession.as_status == status)
            
        # Sorting
        if sort.lower() == "asc":
            query = query.order_by(AttendanceSession.as_checkin_at.asc())
        else:
            query = query.order_by(AttendanceSession.as_checkin_at.desc())
            
        return query.offset(skip).limit(limit).all()

    def count_sessions_with_filters(
        self,
        db: Session,
        user_id: int = None,
        site_id: str = None,
        date_from: date = None,
        date_to: date = None,
        status: str = None
    ) -> int:
        """Count sessions with filters using native SQL"""
        conditions = []
        params = {}
        
        if user_id:
            conditions.append("as_user_id = :user_id")
            params["user_id"] = user_id
        if site_id:
            conditions.append("as_site_id = :site_id")
            params["site_id"] = site_id
        if date_from:
            conditions.append("DATE(as_checkin_at) >= :date_from")
            params["date_from"] = date_from
        if date_to:
            conditions.append("DATE(as_checkin_at) <= :date_to")
            params["date_to"] = date_to
        if status:
            conditions.append("as_status = :status")
            params["status"] = status
            
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT COUNT(*) 
            FROM hris.attendance_sessions 
            WHERE {where_clause}
        """
        
        return self.execute_raw_sql_scalar(db, query, params)

    def get_open_sessions_for_auto_checkout(self, db: Session, cutoff_time: datetime) -> List[AttendanceSession]:
        """Get all open sessions that should be auto-closed using native SQL"""
        query = """
            SELECT as_id, as_user_id, as_site_id, as_checkin_at, as_checkout_at, 
                   as_status, as_created_at, as_updated_at
            FROM hris.attendance_sessions
            WHERE as_status = 'open' 
            AND as_checkin_at < :cutoff_time
        """
        
        results = self.execute_raw_sql_dict(db, query, {"cutoff_time": cutoff_time})
        
        # Convert dict results to AttendanceSession objects
        sessions = []
        for row in results:
            session = AttendanceSession()
            for key, value in row.items():
                setattr(session, key, value)
            sessions.append(session)
            
        return sessions