"""
Maintenance Endpoints - System maintenance and cleanup operations
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.cleanup_service import CleanupService
from app.schemas import DataResponse
from app.api.deps import require_min_role_level
from pydantic import BaseModel

router = APIRouter()
cleanup_service = CleanupService()


class CleanupResult(BaseModel):
    """Cleanup operation result"""
    deleted_count: int
    message: str


@router.post(
    "/cleanup-jti",
    response_model=DataResponse[CleanupResult],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_min_role_level(50))]
)
async def cleanup_jti(
    days_old: int = Query(7, ge=1, le=30, description="Delete JTI records older than this many days"),
    db: Session = Depends(get_db)
):
    """
    Clean up old JTI records from used_jti table
    
    **Authorization:**
    - Requires role level >= 50 (Admin or above)
    
    **Parameters:**
    - days_old: Delete records older than X days (default: 7, max: 30)
    
    **Use case:**
    - Prevent database bloat from JTI anti-replay tokens
    - Should be run daily via scheduled job (GitHub Actions)
    """
    deleted_count = cleanup_service.cleanup_old_jti(db, days_old=days_old)
    
    result = CleanupResult(
        deleted_count=deleted_count,
        message=f"Successfully deleted {deleted_count} JTI records older than {days_old} days"
    )
    
    response = DataResponse(
        success=True,
        message="JTI cleanup completed",
        data=result
    )
    
    return response
