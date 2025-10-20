from fastapi import APIRouter
from app.api.v1.endpoints import sites, attendance

api_router = APIRouter()

# Register attendance routes
api_router.include_router(sites.router, prefix="/sites", tags=["Sites"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
