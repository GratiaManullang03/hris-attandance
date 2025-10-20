"""
Sites Endpoints - CRUD operations for site management
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.site_service import SiteService
from app.schemas import Site, SiteCreate, SiteUpdate, DataResponse, PaginationResponse
from app.api.deps import require_auth, require_min_role_level
from app.core.config import settings
from atams.encryption import encrypt_response_data

router = APIRouter()
site_service = SiteService()


@router.get(
    "/",
    response_model=PaginationResponse[Site],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_min_role_level(50))]
)
async def list_sites(
    search: str = Query("", description="Search sites by name"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Get list of sites with pagination and search
    
    **Authorization:**
    - Requires role level >= 50 (Admin or above)
    """
    sites = site_service.list_sites(db, search=search, skip=skip, limit=limit)
    total = site_service.count_sites(db, search=search)

    response = PaginationResponse(
        success=True,
        message="Sites retrieved successfully",
        data=sites,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )

    return encrypt_response_data(response, settings)


@router.get(
    "/{si_id}",
    response_model=DataResponse[Site],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_min_role_level(50))]
)
async def get_site(
    si_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Get single site by ID
    
    **Authorization:**
    - Requires role level >= 50 (Admin or above)
    """
    site = site_service.get_site(db, si_id)

    response = DataResponse(
        success=True,
        message="Site retrieved successfully",
        data=site
    )

    return encrypt_response_data(response, settings)


@router.post(
    "/",
    response_model=DataResponse[Site],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_min_role_level(50))]
)
async def create_site(
    site: SiteCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Create new site
    
    **Authorization:**
    - Requires role level >= 50 (Admin or above)
    
    **Validation:**
    - si_id: required, unique, max 50 characters
    - si_name: required
    - si_geo_fence: required if GEOFENCE_ENFORCED=true
    """
    new_site = site_service.create_site(
        db, 
        site, 
        geofence_required=settings.GEOFENCE_ENFORCED
    )

    response = DataResponse(
        success=True,
        message="Site created successfully",
        data=new_site
    )
    
    return encrypt_response_data(response, settings)


@router.put(
    "/{si_id}",
    response_model=DataResponse[Site],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_min_role_level(50))]
)
async def update_site(
    si_id: str,
    site: SiteUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Update existing site
    
    **Authorization:**
    - Requires role level >= 50 (Admin or above)
    
    **Updateable fields:**
    - si_name: Site name
    - si_geo_fence: Geofence configuration
    """
    updated_site = site_service.update_site(db, si_id, site)

    response = DataResponse(
        success=True,
        message="Site updated successfully",
        data=updated_site
    )
    
    return encrypt_response_data(response, settings)


@router.delete(
    "/{si_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_min_role_level(50))]
)
async def delete_site(
    si_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Delete site
    
    **Authorization:**
    - Requires role level >= 50 (Admin or above)
    
    **Note:**
    - Deletion will fail if site is referenced by attendance sessions
    """
    site_service.delete_site(db, si_id)
    
    # 204 returns no content
    return None