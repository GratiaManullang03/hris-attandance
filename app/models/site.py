"""
Site Model - Locations for attendance
"""
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from atams.db import Base


class Site(Base):
    """Site model for hris schema - Table: hris.sites"""
    __tablename__ = "sites"
    __table_args__ = {"schema": "hris"}

    si_id = Column(String(50), primary_key=True, index=True)
    si_name = Column(String(255), nullable=False)
    si_geo_fence = Column(JSON, nullable=True)  # {"type":"circle", "center":[-6.2,106.8], "radius_m":150}
    si_created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    si_updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)