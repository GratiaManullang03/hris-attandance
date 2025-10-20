"""
Attendance Event Model - Audit trail for all attendance actions
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from atams.db import Base


class AttendanceEvent(Base):
    """Attendance Event model for hris schema - Table: hris.attendance_events"""
    __tablename__ = "attendance_events"
    __table_args__ = {"schema": "hris"}

    ae_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    ae_session_id = Column(BigInteger, ForeignKey("hris.attendance_sessions.as_id"), nullable=False, index=True)
    ae_user_id = Column(BigInteger, nullable=False, index=True)  # References pt_atams_indonesia.users(u_id)
    ae_site_id = Column(String(50), ForeignKey("hris.sites.si_id"), nullable=False, index=True)
    ae_event_type = Column(String(10), nullable=False)  # 'checkin' or 'checkout'
    ae_occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ae_token_jti = Column(String(64), nullable=False)  # JWT ID for anti-replay
    ae_lat = Column(Float, nullable=True)  # Latitude
    ae_lon = Column(Float, nullable=True)  # Longitude
    ae_device_id = Column(String(255), nullable=True)  # Device identification
    ae_created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ae_updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)