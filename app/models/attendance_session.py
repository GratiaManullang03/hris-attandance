"""
Attendance Session Model - Check-in to Check-out sessions
"""
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from atams.db import Base


class AttendanceSession(Base):
    """Attendance Session model for hris schema - Table: hris.attendance_sessions"""
    __tablename__ = "attendance_sessions"
    __table_args__ = {"schema": "hris"}

    as_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    as_user_id = Column(BigInteger, nullable=False, index=True)  # References pt_atams_indonesia.users(u_id)
    as_site_id = Column(String(50), ForeignKey("hris.sites.si_id"), nullable=False, index=True)
    as_checkin_at = Column(DateTime(timezone=True), nullable=False)
    as_checkout_at = Column(DateTime(timezone=True), nullable=True)
    as_status = Column(String(10), nullable=False, default="open")  # 'open' or 'closed'
    as_created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    as_updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)