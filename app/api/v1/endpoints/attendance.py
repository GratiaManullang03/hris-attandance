"""
Attendance Endpoints - QR token generation, scanning, and history
"""
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.db.session import get_db
from app.services.attendance_service import AttendanceService
from app.schemas import (
    ScanRequest, 
    ScanResponse,
    RollingTokenResponse,
    SessionTodayResponse,
    AttendanceSession,
    AttendanceEvent,
    DataResponse, 
    PaginationResponse
)
from app.api.deps import require_auth, require_min_role_level
from app.core.config import settings
from atams.encryption import encrypt_response_data
from atams.exceptions import ForbiddenException

router = APIRouter()
attendance_service = AttendanceService()


@router.get(
    "/sites/{si_id}/rolling-token",
    response_model=DataResponse[RollingTokenResponse],
    status_code=status.HTTP_200_OK
)
async def get_rolling_token(
    si_id: str,
    x_display_key: str = Header(..., alias="X-Display-Key"),
    db: Session = Depends(get_db)
):
    """
    Generate rolling JWT token for QR display
    
    **Authentication:**
    - Requires X-Display-Key header matching DISPLAY_API_KEY
    
    **Response:**
    - JWT token with ~12s expiry
    - Slot timestamp for tracking
    - Expires_in seconds remaining
    """
    # Validate display API key
    if x_display_key != settings.DISPLAY_API_KEY:
        raise ForbiddenException("Invalid display API key")
    
    token_response = attendance_service.generate_rolling_token(db, si_id)
    
    return DataResponse(
        success=True,
        message="Rolling token generated successfully",
        data=token_response
    )


@router.post(
    "/scan",
    response_model=DataResponse[ScanResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_min_role_level(1))]
)
async def scan_attendance(
    request: ScanRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Process attendance scan (check-in/check-out)
    
    **Authentication:**
    - Requires valid user authentication (role level >= 1)
    
    **Process:**
    1. Verify JWT token from QR code
    2. Anti-replay protection via used_jti table
    3. Geofence validation (if enabled)
    4. Create/close attendance session
    5. Log attendance event
    
    **Response:**
    - as_status: "checked-in" or "checked-out"
    - Attendance session details
    - User-friendly message
    
    **Errors:**
    - 400: Invalid token, expired, or missing location
    - 403: Outside geofence
    - 409: Replay detected (token already used)
    """
    user_id = current_user["user_id"]
    
    scan_response = attendance_service.scan_attendance(db, user_id, request)
    
    return DataResponse(
        success=True,
        message="Attendance scanned successfully",
        data=scan_response
    )


@router.get(
    "/sessions/me/today",
    response_model=DataResponse[SessionTodayResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_min_role_level(1))]
)
async def get_my_session_today(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Get current user's attendance session for today
    
    **Authentication:**
    - Requires valid user authentication (role level >= 1)
    
    **Response:**
    - Session details if exists
    - Empty response if no session today
    """
    user_id = current_user["user_id"]
    
    session_data = attendance_service.get_session_today(db, user_id)
    
    response = DataResponse(
        success=True,
        message="Today's session retrieved successfully",
        data=session_data
    )
    
    return encrypt_response_data(response, settings)


@router.get(
    "/events/me",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_min_role_level(1))]
)
async def get_my_events(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (default: today)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Get current user's attendance events
    
    **Authentication:**
    - Requires valid user authentication (role level >= 1)
    
    **Query Parameters:**
    - date: YYYY-MM-DD format (optional, default today)
    - limit: Max records (1-100, default 50)
    - offset: Skip records (default 0)
    """
    user_id = current_user["user_id"]
    
    # Parse date if provided
    target_date = None
    if date:
        try:
            from datetime import date as dt
            target_date = dt.fromisoformat(date)
        except ValueError:
            from atams.exceptions import BadRequestException
            raise BadRequestException("Invalid date format. Use YYYY-MM-DD")
    
    events = attendance_service.get_user_events(
        db, user_id, target_date, offset, limit
    )
    
    response = PaginationResponse(
        success=True,
        message="Events retrieved successfully",
        data=events,
        total=len(events),  # Simple count for user's own events
        page=offset // limit + 1,
        size=limit,
        pages=1  # Simplified pagination for user events
    )
    
    return encrypt_response_data(response, settings)


@router.get(
    "/sessions",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_min_role_level(50))]
)
async def get_sessions_admin(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    site_id: Optional[str] = Query(None, description="Filter by site ID"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status (open/closed)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    sort: str = Query("desc", regex="^(asc|desc)$", description="Sort order by check-in time"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Get attendance sessions (Admin only)
    
    **Authentication:**
    - Requires role level >= 50 (Admin or above)
    
    **Query Parameters:**
    - user_id: Filter by specific user
    - site_id: Filter by specific site
    - date_from/date_to: Date range filter (YYYY-MM-DD)
    - status: open or closed
    - limit: Max records (1-1000, default 100)
    - offset: Skip records (default 0)
    - sort: asc or desc (default desc)
    """
    # Parse dates if provided
    parsed_date_from = None
    parsed_date_to = None
    
    if date_from:
        try:
            from datetime import date as dt
            parsed_date_from = dt.fromisoformat(date_from)
        except ValueError:
            from atams.exceptions import BadRequestException
            raise BadRequestException("Invalid date_from format. Use YYYY-MM-DD")
            
    if date_to:
        try:
            from datetime import date as dt
            parsed_date_to = dt.fromisoformat(date_to)
        except ValueError:
            from atams.exceptions import BadRequestException
            raise BadRequestException("Invalid date_to format. Use YYYY-MM-DD")
    
    sessions = attendance_service.get_sessions_admin(
        db, user_id, site_id, parsed_date_from, parsed_date_to, status, offset, limit, sort
    )
    
    total = attendance_service.count_sessions_admin(
        db, user_id, site_id, parsed_date_from, parsed_date_to, status
    )
    
    response = PaginationResponse(
        success=True,
        message="Sessions retrieved successfully",
        data=sessions,
        total=total,
        page=offset // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )
    
    return encrypt_response_data(response, settings)