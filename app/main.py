"""
hris_attendance - AURA Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from atams.db import init_database
from atams.logging import setup_logging_from_settings
from atams.middleware import RequestIDMiddleware
from atams.exceptions import setup_exception_handlers
from atams.api import health_router

from app.core.config import settings
from app.api.v1.api import api_router

# Setup logging
setup_logging_from_settings(settings)

# Initialize database with connection pool settings
init_database(
    settings.DATABASE_URL,
    settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=settings.DB_POOL_PRE_PING
)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="AURA Application with Atlas SSO Integration",
    swagger_ui_parameters={
        "persistAuthorization": True,
    },
)

# CORS middleware
if settings.DEBUG == True:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.cors_methods_list,
        allow_headers=settings.cors_headers_list,
    )

# Request ID middleware
app.add_middleware(RequestIDMiddleware)

# Exception handlers
setup_exception_handlers(app)

# Mount static files (HTML pages)
app.mount("/pwa", StaticFiles(directory=".", html=True), name="static")

# Include routers
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    """API Root - Basic information"""
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION}
