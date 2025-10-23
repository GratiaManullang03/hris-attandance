from fastapi import APIRouter
from app.api.v1.endpoints import sites, attendance, maintenance

api_router = APIRouter()

# Register routes
api_router.include_router(sites.router, prefix="/sites", tags=["Sites"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
api_router.include_router(maintenance.router, prefix="/maintenance", tags=["Maintenance"])
