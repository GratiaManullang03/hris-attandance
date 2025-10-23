"""
Attendance Service - Main business logic for attendance operations
"""
import math
from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.repositories.site_repository import SiteRepository
from app.repositories.attendance_session_repository import AttendanceSessionRepository
from app.repositories.attendance_event_repository import AttendanceEventRepository
from app.repositories.used_jti_repository import UsedJtiRepository
from app.services.jwt_service import JwtService
from app.schemas.attendance import (
    AttendanceSession,
    AttendanceEvent,
    ScanRequest,
    ScanResponse,
    RollingTokenResponse,
    SessionTodayResponse
)
from app.core.config import settings
from atams.exceptions import (
    NotFoundException,
    BadRequestException,
    ForbiddenException,
    ConflictException
)


class AttendanceService:
    def __init__(self) -> None:
        self.site_repo = SiteRepository()
        self.session_repo = AttendanceSessionRepository()
        self.event_repo = AttendanceEventRepository()
        self.jti_repo = UsedJtiRepository()
        self.jwt_service = JwtService()

    def generate_rolling_token(self, db: Session, site_id: str) -> RollingTokenResponse:
        """
        Generate rolling token for QR display
        
        Args:
            db: Database session
            site_id: Site ID to generate token for
            
        Returns:
            RollingTokenResponse: Token data
            
        Raises:
            NotFoundException: If site not found
        """
        # Verify site exists
        if not self.site_repo.check_site_exists(db, site_id):
            raise NotFoundException("Site not found")
        
        token_data = self.jwt_service.generate_rolling_token(site_id)
        
        return RollingTokenResponse(
            token=token_data["token"],
            slot=token_data["slot"],
            expires_in=token_data["expires_in"]
        )

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two coordinates using Haversine formula
        
        Returns:
            float: Distance in meters
        """
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c

    def _validate_geofence(self, db: Session, site_id: str, user_lat: float, user_lon: float) -> None:
        """
        Validate user location against site geofence
        
        Args:
            db: Database session
            site_id: Site ID
            user_lat: User latitude
            user_lon: User longitude
            
        Raises:
            ForbiddenException: If user is outside geofence
            NotFoundException: If site not found
        """
        if not settings.GEOFENCE_ENFORCED:
            return
            
        site = self.site_repo.get_by_id(db, site_id)
        if not site:
            raise NotFoundException("Site not found")
            
        if not site.si_geo_fence:
            # No geofence defined, use default
            raise ForbiddenException("Geofence not configured for this site")
            
        geo_fence = site.si_geo_fence
        if geo_fence["type"] != "circle":
            raise BadRequestException("Unsupported geofence type")
            
        center = geo_fence["center"]  # [lat, lon]
        radius_m = geo_fence["radius_m"]
        
        distance = self._calculate_distance(
            center[0], center[1],  # Site coordinates
            user_lat, user_lon     # User coordinates
        )
        
        if distance > radius_m:
            raise ForbiddenException(f"Out of geofence (distance: {distance:.0f}m, allowed: {radius_m}m)")

    def scan_attendance(self, db: Session, user_id: int, request: ScanRequest) -> ScanResponse:
        """
        Process attendance scan with full validation
        
        Args:
            db: Database session
            user_id: Current user ID from auth
            request: Scan request data
            
        Returns:
            ScanResponse: Scan result
            
        Raises:
            BadRequestException: Invalid token or data
            ForbiddenException: Geofence or permission issues
            ConflictException: Replay detected
        """
        # 1. Verify and decode JWT token
        try:
            token_payload = self.jwt_service.verify_token(request.token)
        except BadRequestException as e:
            raise BadRequestException(f"Token validation failed: {str(e)}")
        
        site_id = token_payload["si_id"]
        jti = token_payload["jti"]
        
        # 2. Geofence validation (BEFORE marking JTI as used)
        if request.ae_lat is not None and request.ae_lon is not None:
            self._validate_geofence(db, site_id, request.ae_lat, request.ae_lon)
        else:
            if settings.GEOFENCE_ENFORCED:
                raise BadRequestException("Location coordinates required for geofence validation")
        
        # 3. Anti-replay protection (AFTER all validations pass)
        if not self.jti_repo.mark_jti_as_used(db, jti):
            raise ConflictException("Replay detected")
        
        # 4. Determine action: check-in or check-out
        now = datetime.utcnow()
        today = date.today()
        existing_session = self.session_repo.get_open_session_today(db, user_id, today)
        
        if existing_session is None:
            # Check-in: Create new session
            session_data = {
                "as_user_id": user_id,
                "as_site_id": site_id,
                "as_checkin_at": now,
                "as_status": "open"
            }
            db_session = self.session_repo.create(db, session_data)
            
            # Create check-in event
            event_data = {
                "ae_session_id": db_session.as_id,
                "ae_user_id": user_id,
                "ae_site_id": site_id,
                "ae_event_type": "checkin",
                "ae_occurred_at": now,
                "ae_token_jti": jti,
                "ae_lat": request.ae_lat,
                "ae_lon": request.ae_lon,
                "ae_device_id": request.ae_device_id
            }
            self.event_repo.create_event(db, event_data)
            
            return ScanResponse(
                as_status="checked-in",
                si_id=site_id,
                as_id=db_session.as_id,
                timestamp=now,
                message=f"Hadir ✔ {now.strftime('%H:%M')}"
            )
        else:
            # Check-out: Close existing session
            update_data = {
                "as_checkout_at": now,
                "as_status": "closed"
            }
            db_session = self.session_repo.update(db, existing_session, update_data)
            
            # Create check-out event
            event_data = {
                "ae_session_id": existing_session.as_id,
                "ae_user_id": user_id,
                "ae_site_id": site_id,
                "ae_event_type": "checkout",
                "ae_occurred_at": now,
                "ae_token_jti": jti,
                "ae_lat": request.ae_lat,
                "ae_lon": request.ae_lon,
                "ae_device_id": request.ae_device_id
            }
            self.event_repo.create_event(db, event_data)
            
            return ScanResponse(
                as_status="checked-out",
                si_id=site_id,
                as_id=existing_session.as_id,
                timestamp=now,
                message=f"Pulang ✔ {now.strftime('%H:%M')}"
            )

    def get_session_today(self, db: Session, user_id: int) -> SessionTodayResponse:
        """Get user's session for today"""
        today = date.today()
        session = self.session_repo.get_session_today(db, user_id, today)
        
        if not session:
            return SessionTodayResponse()
        
        return SessionTodayResponse(
            as_id=session.as_id,
            as_status=session.as_status,
            si_id=session.as_site_id,
            as_checkin_at=session.as_checkin_at,
            as_checkout_at=session.as_checkout_at
        )

    def get_user_events(
        self,
        db: Session,
        user_id: int,
        target_date: date = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[AttendanceEvent]:
        """Get user's attendance events"""
        if target_date is None:
            target_date = date.today()
            
        events = self.event_repo.get_user_events(db, user_id, target_date, skip, limit)
        return [AttendanceEvent.model_validate(e) for e in events]

    def get_sessions_admin(
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
        """Get attendance sessions for admin (with filters)"""
        sessions = self.session_repo.get_sessions_with_filters(
            db, user_id, site_id, date_from, date_to, status, skip, limit, sort
        )
        return [AttendanceSession.model_validate(s) for s in sessions]

    def count_sessions_admin(
        self,
        db: Session,
        user_id: int = None,
        site_id: str = None,
        date_from: date = None,
        date_to: date = None,
        status: str = None
    ) -> int:
        """Count attendance sessions for admin (with filters)"""
        return self.session_repo.count_sessions_with_filters(
            db, user_id, site_id, date_from, date_to, status
        )