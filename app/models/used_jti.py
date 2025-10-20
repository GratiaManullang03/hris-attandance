"""
Used JTI Model - Anti-replay token tracking
"""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from atams.db import Base


class UsedJti(Base):
    """Used JTI model for hris schema - Table: hris.used_jti"""
    __tablename__ = "used_jti"
    __table_args__ = {"schema": "hris"}

    uj_jti = Column(String(64), primary_key=True, index=True)  # JWT ID
    uj_used_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)