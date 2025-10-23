"""
Cleanup Service - Maintenance operations for database hygiene
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text


class CleanupService:
    def cleanup_old_jti(self, db: Session, days_old: int = 7) -> int:
        """
        Delete old JTI records to prevent table bloat
        
        Args:
            db: Database session
            days_old: Delete records older than this many days (default: 7)
            
        Returns:
            int: Number of records deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days_old)
        
        result = db.execute(
            text("DELETE FROM hris.used_jti WHERE uj_created_at < :cutoff"),
            {"cutoff": cutoff}
        )
        db.commit()
        
        return result.rowcount
