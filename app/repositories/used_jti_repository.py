"""
Used JTI Repository - Data access layer for anti-replay token tracking
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from atams.db import BaseRepository
from app.models.used_jti import UsedJti


class UsedJtiRepository(BaseRepository[UsedJti]):
    def __init__(self):
        super().__init__(UsedJti)

    def mark_jti_as_used(self, db: Session, user_id: int, jti: str) -> bool:
        """
        Mark JTI as used for anti-replay protection (per user).
        Returns True if successfully marked, False if already exists (replay detected).
        
        This allows multiple users to scan the same QR code,
        but prevents a single user from scanning the same token twice.
        """
        try:
            db_jti = UsedJti(uj_user_id=user_id, uj_jti=jti)
            db.add(db_jti)
            db.commit()
            return True
        except IntegrityError:
            # JTI already used by this user - replay detected
            db.rollback()
            return False

    def is_jti_used(self, db: Session, user_id: int, jti: str) -> bool:
        """Check if JTI has been used by specific user (for debugging/verification)"""
        return db.query(UsedJti).filter(
            UsedJti.uj_user_id == user_id,
            UsedJti.uj_jti == jti
        ).first() is not None

    def cleanup_old_jtis(self, db: Session, older_than_days: int = 1) -> int:
        """
        Clean up JTIs older than specified days using native SQL.
        Returns count of deleted records.
        """
        cutoff_time = datetime.now() - timedelta(days=older_than_days)
        
        # Get count first
        count_query = """
            SELECT COUNT(*) 
            FROM hris.used_jti 
            WHERE uj_used_at < :cutoff_time
        """
        count = self.execute_raw_sql_scalar(db, count_query, {"cutoff_time": cutoff_time})
        
        # Delete old records
        delete_query = """
            DELETE FROM hris.used_jti 
            WHERE uj_used_at < :cutoff_time
        """
        self.execute_raw_sql(db, delete_query, {"cutoff_time": cutoff_time})
        
        return count