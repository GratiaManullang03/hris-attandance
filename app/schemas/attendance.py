"""
Attendance Schemas for sessions and events
"""
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class AttendanceSessionBase(BaseModel):
    as_user_id: int
    as_site_id: str
    as_checkin_at: datetime
    as_checkout_at: Optional[datetime] = None
    as_status: Literal["open", "closed"] = "open"


class AttendanceSessionInDB(AttendanceSessionBase):
    model_config = ConfigDict(from_attributes=True)
    
    as_id: int
    as_created_at: datetime
    as_updated_at: Optional[datetime] = None

    @field_validator('as_checkout_at', 'as_checkin_at', 'as_updated_at', 'as_created_at', mode='before')
    @classmethod
    def fix_datetime_timezone(cls, v):
        """Fix datetime timezone format from PostgreSQL"""
        if v == '' or v is None:
            return None

        if isinstance(v, str):
            import re
            pattern = r'([+-]\d{2})$'
            match = re.search(pattern, v)
            if match:
                v = v + ':00'

        return v


class AttendanceSession(AttendanceSessionInDB):
    pass


class AttendanceEventBase(BaseModel):
    ae_session_id: int
    ae_user_id: int
    ae_site_id: str
    ae_event_type: Literal["checkin", "checkout"]
    ae_occurred_at: datetime
    ae_token_jti: str
    ae_lat: Optional[float] = None
    ae_lon: Optional[float] = None
    ae_device_id: Optional[str] = None


class AttendanceEventInDB(AttendanceEventBase):
    model_config = ConfigDict(from_attributes=True)
    
    ae_id: int
    ae_created_at: datetime
    ae_updated_at: Optional[datetime] = None

    @field_validator('ae_occurred_at', 'ae_updated_at', 'ae_created_at', mode='before')
    @classmethod
    def fix_datetime_timezone(cls, v):
        """Fix datetime timezone format from PostgreSQL"""
        if v == '' or v is None:
            return None

        if isinstance(v, str):
            import re
            pattern = r'([+-]\d{2})$'
            match = re.search(pattern, v)
            if match:
                v = v + ':00'

        return v


class AttendanceEvent(AttendanceEventInDB):
    pass


# Request/Response schemas for API endpoints
class ScanRequest(BaseModel):
    """Request schema for attendance scan endpoint"""
    token: str  # JWT from QR code
    ae_lat: Optional[float] = None
    ae_lon: Optional[float] = None
    ae_device_id: Optional[str] = None


class ScanResponse(BaseModel):
    """Response schema for attendance scan endpoint"""
    as_status: Literal["checked-in", "checked-out"]
    si_id: str
    as_id: int
    timestamp: datetime
    message: str


class RollingTokenResponse(BaseModel):
    """Response schema for rolling token endpoint"""
    token: str
    slot: int
    expires_in: int


class SessionTodayResponse(BaseModel):
    """Response schema for today's session"""
    as_id: Optional[int] = None
    as_status: Optional[Literal["open", "closed"]] = None
    si_id: Optional[str] = None
    as_checkin_at: Optional[datetime] = None
    as_checkout_at: Optional[datetime] = None