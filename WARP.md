# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

HRIS Attendance is an AURA application built with the ATAMS toolkit. It provides QR-based attendance tracking with JWT rolling tokens, geofence validation, and Atlas SSO integration.

## Commands

### Development

```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Run development server
uvicorn app.main:app --reload

# Access API
# - Interactive docs: http://localhost:8000/docs
# - Health check: http://localhost:8000/health
# - Root endpoint: http://localhost:8000/
```

### Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

### Code Generation

ATAMS provides a CLI for generating CRUD resources:

```bash
# Generate complete CRUD scaffold for a resource
atams generate <resource_name>

# Example: Generate department resource
atams generate department
```

This creates:
- Model in `app/models/`
- Schema in `app/schemas/`
- Repository in `app/repositories/`
- Service in `app/services/`
- Router in `app/api/v1/endpoints/`

### Testing

Note: Test infrastructure exists in `tests/` directory but no test files are currently implemented. When adding tests, use pytest:

```bash
pytest tests/
```

## Architecture

### Core Technology Stack

- **Framework**: FastAPI with SQLAlchemy ORM
- **Database**: PostgreSQL with connection pooling
- **Authentication**: Atlas SSO (external microservice)
- **Deployment**: Vercel-ready (vercel.json) or Docker

### ATAMS Toolkit

This application is built on the ATAMS toolkit (`atams>=1.0.0`), which provides:

- **Database**: `atams.db` - Base models, session management, and init_database()
- **Authentication**: `atams.sso` - Atlas SSO client and auth dependency factories
- **Encryption**: `atams.encryption` - AES encryption for GET responses
- **Exceptions**: `atams.exceptions` - Standardized exception classes (NotFoundException, BadRequestException, ForbiddenException, ConflictException)
- **Middleware**: `atams.middleware` - RequestIDMiddleware for request tracking
- **Logging**: `atams.logging` - Centralized logging setup
- **API Utilities**: `atams.api` - Health check router

### Layer Architecture

```
app/
├── core/           # Configuration (AtamsBaseSettings)
├── db/             # Database session management
├── models/         # SQLAlchemy models (hris schema)
├── schemas/        # Pydantic request/response schemas
├── repositories/   # Data access layer (DB operations)
├── services/       # Business logic layer
└── api/
    └── v1/
        └── endpoints/  # FastAPI routers
```

**Data Flow**: Endpoint → Service → Repository → Database

### Key Models

All models use the `hris` PostgreSQL schema:

- **AttendanceSession** (`hris.attendance_sessions`) - Daily check-in/check-out sessions
- **AttendanceEvent** (`hris.attendance_events`) - Audit trail of all attendance actions
- **Site** (`hris.sites`) - Physical locations with geofence data (JSONB circle)
- **UsedJti** (`hris.used_jti`) - JWT anti-replay protection (per-user token tracking)

### Authentication & Authorization

Uses ATAMS factory pattern from `app/api/deps.py`:

```python
from app.api.deps import require_auth, require_min_role_level

# Basic auth (any authenticated user)
@router.get("/endpoint", dependencies=[Depends(require_auth)])

# Role-based auth (minimum role level)
@router.get("/admin", dependencies=[Depends(require_min_role_level(50))])
```

**Role Levels**:
- `>= 1`: Regular users (employees)
- `>= 50`: Administrators

User authentication is validated against Atlas SSO. The `current_user` dict contains:
- `user_id`: Integer ID from pt_atams_indonesia.users
- `role_level`: Integer role level
- Other user metadata from Atlas SSO

### QR Token System

**Rolling JWT Tokens** for QR display:
- Generated via `/api/v1/attendance/sites/{si_id}/rolling-token`
- Requires `X-Display-Key` header matching `DISPLAY_API_KEY`
- Token rotation: 10 seconds (configurable via `QR_ROTATION_SECONDS`)
- Grace period: 2 seconds (configurable via `QR_EXPIRE_GRACE_SECONDS`)
- Total expiry: ~12 seconds

**Token Structure**:
```json
{
  "iss": "hris-attendance",
  "aud": "site:{si_id}",
  "si_id": "SITE001",
  "slot": 1698765432,
  "jti": "uuid-v4",
  "iat": 1698765432,
  "exp": 1698765444,
  "mode": "AUTO"
}
```

**Anti-Replay Protection**:
- Each token has unique JTI (JWT ID)
- Per-user anti-replay: same token can be used by multiple users, but only once per user
- JTI stored in `hris.used_jti` table with `uj_user_id` + `uj_jti` unique constraint
- Old JTI records cleaned up via GitHub Actions workflow (daily at 02:00 WIB)

### Attendance Logic

**Time-based Auto-Detection** (Jakarta timezone, WIB = UTC+7):
- **Before 13:00 WIB**: Always CHECK-IN
- **After 13:00 WIB**: Always CHECK-OUT

**Scan Workflow** (`/api/v1/attendance/scan`):
1. Verify JWT token from QR code
2. Validate geofence (if enabled and coordinates provided)
3. Check anti-replay (mark JTI as used for this user)
4. Determine action based on Jakarta time
5. Create/close attendance session
6. Log attendance event

**Geofence Validation**:
- Site geofence stored as JSONB: `{"type": "circle", "center": [lat, lon], "radius_m": 100}`
- Haversine formula calculates distance between user and site center
- Configurable via `GEOFENCE_ENFORCED` and `DEFAULT_GEOFENCE_RADIUS_M`

### Response Encryption

GET endpoints support optional AES encryption via ATAMS encryption module:

```python
from atams.encryption import encrypt_response_data

response = DataResponse(success=True, data=data)
return encrypt_response_data(response, settings)
```

Enable via `.env`:
```bash
ENCRYPTION_ENABLED=true
ENCRYPTION_KEY=<32-char-hex>  # openssl rand -hex 16
ENCRYPTION_IV=<16-char-hex>   # openssl rand -hex 8
```

### Database Connection Pool

Critical for production deployment (especially limited connection services like Aiven free tier):

```bash
# .env configuration
DB_POOL_SIZE=3           # Core persistent connections
DB_MAX_OVERFLOW=5        # Additional connections under load
DB_POOL_RECYCLE=3600     # Recycle connections after 1 hour
DB_POOL_TIMEOUT=30       # Connection timeout in seconds
DB_POOL_PRE_PING=true    # Test connections before use
```

**Formula**: Total Connections = (DB_POOL_SIZE + DB_MAX_OVERFLOW) × Number of App Instances

### Maintenance

**JTI Cleanup**: GitHub Actions workflow (`.github/workflows/`) runs daily at 02:00 WIB to clean up old JTI records via `/api/v1/maintenance/cleanup-jti?days_old=7`. Requires GitHub Secrets: `API_BASE_URL` and `ADMIN_TOKEN`.

## Important Configuration

### Environment Variables

Key settings from `.env.example`:

- **Database**: `DATABASE_URL`, connection pool settings
- **Atlas SSO**: `ATLAS_SSO_URL`, `ATLAS_APP_CODE`, encryption keys
- **QR JWT**: `QR_JWT_SECRET`, `QR_JWT_ALG`, rotation timings
- **Display Auth**: `DISPLAY_API_KEY` (for QR display endpoints)
- **Geofence**: `GEOFENCE_ENFORCED`, `DEFAULT_GEOFENCE_RADIUS_M`
- **Rate Limiting**: `RATE_LIMIT_SCAN_PER_MIN` for scan endpoint

### CORS Configuration

In production mode (`DEBUG=false`), CORS is restricted to `*.atamsindonesia.com` domains by default. Override via `CORS_ORIGINS` in `.env`.

In debug mode (`DEBUG=true`), CORS allows all origins.

## Patterns and Conventions

### Repository Pattern

Repositories inherit from ATAMS `BaseRepository` and provide both ORM and native SQL methods:

```python
from atams.repositories import BaseRepository

class MyRepository(BaseRepository[MyModel, int]):
    def custom_query(self, db: Session, param: str) -> List[MyModel]:
        # Custom query logic
        pass
```

### Service Layer

Services contain business logic and orchestrate multiple repositories:

```python
class MyService:
    def __init__(self):
        self.repo = MyRepository()
        
    def process(self, db: Session, data: dict) -> Result:
        # Business logic with proper transaction handling
        try:
            result = self.repo.create(db, data)
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise
```

### Error Handling

Use ATAMS exceptions for consistent error responses:

```python
from atams.exceptions import NotFoundException, BadRequestException, ForbiddenException, ConflictException

# These are automatically handled by setup_exception_handlers(app)
raise NotFoundException("Resource not found")
raise BadRequestException("Invalid input")
raise ForbiddenException("Access denied")
raise ConflictException("Duplicate entry")
```

### Schema Naming

Follow SQLAlchemy model naming conventions:
- Table prefix based on entity: `as_` (attendance_session), `ae_` (attendance_event), `si_` (site)
- Primary key: `{prefix}_id`
- Foreign keys: `{prefix}_{related_entity}_id`
- Timestamps: `{prefix}_created_at`, `{prefix}_updated_at`

### Datetime Handling

PostgreSQL datetime fields with timezone require special handling in Pydantic schemas:

```python
@field_validator('datetime_field', mode='before')
@classmethod
def fix_datetime_timezone(cls, v):
    """Fix datetime timezone format from PostgreSQL"""
    if v == '' or v is None:
        return None
    if isinstance(v, str):
        import re
        pattern = r'([+-]\d{2})$'
        match = re.search(pattern, v)
        if match:
            v = v + ':00'
    return v
```

## External Dependencies

- **Atlas SSO**: External microservice for user authentication (configured via `ATLAS_SSO_URL`)
- **PostgreSQL**: Requires `hris` schema with proper table structure
- Users table: `pt_atams_indonesia.users` (external schema, read-only reference via `u_id`)
