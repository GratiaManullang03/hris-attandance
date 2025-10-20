"""
Site Service - Business logic for site management
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.repositories.site_repository import SiteRepository
from app.schemas.site import SiteCreate, SiteUpdate, Site
from atams.exceptions import (
    NotFoundException,
    BadRequestException,
    ConflictException,
)


class SiteService:
    def __init__(self) -> None:
        self.repo = SiteRepository()

    def list_sites(self, db: Session, search: str = "", skip: int = 0, limit: int = 100) -> List[Site]:
        sites = self.repo.get_sites_with_search(db, search=search, skip=skip, limit=limit)
        return [Site.model_validate(s) for s in sites]

    def count_sites(self, db: Session, search: str = "") -> int:
        return self.repo.count_sites_with_search(db, search=search)

    def get_site(self, db: Session, si_id: str) -> Site:
        site = self.repo.get_by_id(db, si_id)
        if not site:
            raise NotFoundException("Site not found")
        return Site.model_validate(site)

    def create_site(self, db: Session, payload: SiteCreate, geofence_required: bool = True) -> Site:
        # validations
        if geofence_required and payload.si_geo_fence is None:
            raise BadRequestException("si_geo_fence is required when geofence is enforced")
        if len(payload.si_id) > 50:
            raise BadRequestException("si_id max length is 50")
        if self.repo.check_site_exists(db, payload.si_id):
            raise ConflictException("Site with this ID already exists")

        obj = self.repo.create(db, {
            "si_id": payload.si_id,
            "si_name": payload.si_name,
            "si_geo_fence": payload.si_geo_fence.model_dump() if payload.si_geo_fence else None,
        })
        return Site.model_validate(obj)

    def update_site(self, db: Session, si_id: str, payload: SiteUpdate) -> Site:
        obj = self.repo.get_by_id(db, si_id)
        if not obj:
            raise NotFoundException("Site not found")
        update_data = payload.model_dump(exclude_unset=True)
        if "si_geo_fence" in update_data and update_data["si_geo_fence"] is not None:
            update_data["si_geo_fence"] = payload.si_geo_fence.model_dump()
        obj = self.repo.update(db, obj, update_data)
        return Site.model_validate(obj)

    def delete_site(self, db: Session, si_id: str) -> None:
        # rely on FK constraints to prevent deletion if referenced
        deleted = self.repo.delete_by_id(db, si_id)
        if not deleted:
            raise NotFoundException("Site not found")
        return None
