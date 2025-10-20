"""
Site Schemas for request/response validation
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class GeoFence(BaseModel):
    """Geofence data structure"""
    type: str = "circle"
    center: List[float]  # [latitude, longitude]
    radius_m: int


class SiteBase(BaseModel):
    si_name: str
    si_geo_fence: Optional[GeoFence] = None


class SiteCreate(SiteBase):
    si_id: str


class SiteUpdate(BaseModel):
    si_name: Optional[str] = None
    si_geo_fence: Optional[GeoFence] = None


class SiteInDB(SiteBase):
    model_config = ConfigDict(from_attributes=True)
    
    si_id: str
    si_created_at: datetime
    si_updated_at: Optional[datetime] = None

    @field_validator('si_updated_at', 'si_created_at', mode='before')
    @classmethod
    def fix_datetime_timezone(cls, v):
        """
        Fix datetime timezone format from PostgreSQL
        PostgreSQL returns: '2025-10-01 09:17:39.587802+00'
        Pydantic expects: '2025-10-01 09:17:39.587802+00:00'
        """
        if v == '' or v is None:
            return None

        # Fix timezone format: +00 -> +00:00, +07 -> +07:00
        if isinstance(v, str):
            # Pattern: ends with +XX or -XX (without colon)
            import re
            # Match timezone like +00, +07, -05 at the end
            pattern = r'([+-]\d{2})$'
            match = re.search(pattern, v)
            if match:
                v = v + ':00'

        return v


class Site(SiteInDB):
    pass