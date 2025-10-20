"""
Site Repository - Data access layer for sites
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from atams.db import BaseRepository
from app.models.site import Site


class SiteRepository(BaseRepository[Site]):
    def __init__(self):
        super().__init__(Site)

    def get_by_id(self, db: Session, site_id: str) -> Optional[Site]:
        """Get site by ID using ORM"""
        return db.query(Site).filter(Site.si_id == site_id).first()

    def get_sites_with_search(self, db: Session, search: str = "", skip: int = 0, limit: int = 100) -> List[Site]:
        """Get sites with optional search filter using ORM"""
        query = db.query(Site)
        
        if search:
            query = query.filter(Site.si_name.ilike(f"%{search}%"))
        
        return query.offset(skip).limit(limit).all()

    def count_sites_with_search(self, db: Session, search: str = "") -> int:
        """Count sites with optional search filter using native SQL"""
        if search:
            query = """
                SELECT COUNT(*) 
                FROM hris.sites 
                WHERE si_name ILIKE :search
            """
            return self.execute_raw_sql_scalar(db, query, {"search": f"%{search}%"})
        else:
            query = "SELECT COUNT(*) FROM hris.sites"
            return self.execute_raw_sql_scalar(db, query)

    def check_site_exists(self, db: Session, site_id: str) -> bool:
        """Check if site exists using native SQL"""
        query = "SELECT 1 FROM hris.sites WHERE si_id = :site_id LIMIT 1"
        result = self.execute_raw_sql_scalar(db, query, {"site_id": site_id})
        return result is not None

    def delete_by_id(self, db: Session, site_id: str) -> bool:
        """Delete site by ID and return success status"""
        site = self.get_by_id(db, site_id)
        if site:
            db.delete(site)
            db.commit()
            return True
        return False