# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

HRIS Attendance is an AURA Application built with the **ATAMS toolkit** - a FastAPI-based framework that provides Atlas SSO authentication, database abstractions, encryption, and standardized patterns for enterprise applications.

## Commands

### Setup & Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Then edit .env with your configuration

# Run application
uvicorn app.main:app --reload

# Generate CRUD resources (ATAMS CLI)
atams generate <resource_name>
```

### Access Points
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Root: http://localhost:8000/

### Database
This project uses PostgreSQL with connection pooling. Database initialization happens automatically in `app/main.py` via `atams.db.init_database()`. Connection pool settings are configured in `.env` (see `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, etc.).

**Important**: Tune pool settings based on your database connection limits. Example for Aiven free tier (20 connections): `DB_POOL_SIZE=3`, `DB_MAX_OVERFLOW=5`.

### Testing
There is no automated test suite. See `MANUAL_TESTING_GUIDE.md` for comprehensive API testing scenarios using curl/Postman.

## Architecture

### ATAMS Framework Patterns

This codebase follows **ATAMS conventions** throughout:

1. **Layered Architecture** (strict separation):
   - **Models** (`app/models/`) - SQLAlchemy ORM models
   - **Schemas** (`app/schemas/`) - Pydantic validation/serialization
   - **Repositories** (`app/repositories/`) - Data access layer (extends `atams.db.BaseRepository`)
   - **Services** (`app/services/`) - Business logic layer
   - **API** (`app/api/`) - FastAPI endpoints

2. **Authentication/Authorization**:
   - Uses **Atlas SSO** via `atams.sso` module
   - Auth dependencies created in `app/api/deps.py` using `create_auth_dependencies()` factory
   - Endpoints use `require_min_role_level(N)` for authorization checks
   - Two-level authorization: route-level + service-level validation

3. **Repository Pattern**:
   - All repositories inherit from `atams.db.BaseRepository[Model]`
   - Supports both **ORM queries** (recommended) and **raw SQL** via `execute_raw_sql_scalar()` / `execute_raw_sql_dict()`
   - Database session management handled by ATAMS dependency injection

4. **Response Encryption**:
   - GET endpoints can return encrypted responses when `ENCRYPTION_ENABLED=true`
   - Uses `ENCRYPTION_KEY` and `ENCRYPTION_IV` from settings

5. **Exception Handling**:
   - Use ATAMS exceptions: `NotFoundException`, `BadRequestException`, `ForbiddenException`, `ConflictException`
   - Centralized handler via `setup_exception_handlers(app)`

### Database Schema

Schema: `hris` (all tables use schema-qualified names)

**Column Naming Convention** (prefix-based):
- **sites** → `si_*`
- **attendance_sessions** → `as_*` 
- **attendance_events** → `ae_*`
- **used_jti** → `uj_*`

**Key Tables**:
- `hris.sites` - Office locations with geofence (JSON: circle with center lat/lon + radius)
- `hris.attendance_sessions` - Check-in to check-out sessions (one open session per user per day - enforced by unique index)
- `hris.attendance_events` - Audit trail for all check-in/checkout actions
- `hris.used_jti` - Anti-replay protection for JWT tokens (primary key on jti prevents reuse)

All tables follow the same timestamp pattern: `*_created_at`, `*_updated_at`.

### Core Business Logic

**Attendance Flow** (in `attendance_service.py`):

1. **Rolling Token Generation** (`/rolling-token` endpoint):
   - Display screens fetch time-based JWT tokens every ~10 seconds
   - Token contains: `si_id`, `slot`, `jti`, expiry
   - Protected by `DISPLAY_API_KEY` header

2. **Attendance Scan** (`/scan` endpoint):
   - Validates JWT token (signature, expiry, audience)
   - **Anti-replay**: Inserts `jti` into `used_jti` table (PK conflict = replay detected → 409 error)
   - **Geofence validation**: Calculates Haversine distance between user location and site's `si_geo_fence`
   - **Session logic**:
     - No open session today → Create new session + check-in event
     - Open session exists → Close session + check-out event
   - Creates `attendance_events` record for audit trail

3. **Geofence Enforcement**:
   - Configured via `GEOFENCE_ENFORCED` setting
   - Site's `si_geo_fence` defines circle: `{"type": "circle", "center": [lat, lon], "radius_m": 150}`
   - Uses Haversine formula in `_calculate_distance()`

### Configuration

Settings inherit from `atams.AtamsBaseSettings` which provides:
- Database configuration
- Atlas SSO settings
- Response encryption settings
- CORS configuration
- Rate limiting
- Logging configuration

Project-specific settings in `app/core/config.py`:
- QR JWT settings (rolling token parameters)
- Display authentication
- Auto-checkout cron settings
- Geofence enforcement flags
- Scan rate limiting

### Key Integration Points

**Atlas SSO**:
- Client initialized via `create_atlas_client(settings)` in `app/api/deps.py`
- Environment requires: `ATLAS_SSO_URL`, `ATLAS_APP_CODE`, `ATLAS_ENCRYPTION_KEY`, `ATLAS_ENCRYPTION_IV`
- User JWT validated on each protected endpoint

**JWT Service** (`app/services/jwt_service.py`):
- Generates rolling tokens with slot-based expiry
- Validates QR tokens with anti-replay check
- Uses `QR_JWT_SECRET` and `QR_JWT_ALG` settings

### Important Constraints

1. **One open session per user per day** - enforced by unique index: `attendance_sessions_one_open_per_day`
2. **Token replay protection** - enforced by primary key on `used_jti.uj_jti`
3. **Geofence validation** - mandatory when `GEOFENCE_ENFORCED=true`
4. **Foreign key relationships** - Cannot delete site if referenced by sessions/events

### Background Jobs (Required)

While not currently implemented in code, the design requires:
1. **Auto-checkout job** (daily at `AUTO_CHECKOUT_CRON` time) - closes all open sessions
2. **JTI cleanup job** - purges old `used_jti` records (older than 1-7 days)

These should be implemented using APScheduler or cron.

## Development Guidelines

### Adding New Resources

Use the ATAMS CLI to generate CRUD boilerplate:
```bash
atams generate department  # Creates model, schema, repository, service, endpoints
```

This follows the established pattern and maintains consistency.

### Authorization Levels

When implementing endpoints, follow the existing role level pattern:
- Level 1-9: Basic user access
- Level 10-49: Regular operations
- Level 50+: Administrative operations

Example: `require_min_role_level(50)` for admin-only endpoints.

### Database Queries

Prefer ORM queries for readability, but use raw SQL for complex aggregations or performance-critical queries:

```python
# ORM (preferred)
session = db.query(AttendanceSession).filter(AttendanceSession.as_user_id == user_id).first()

# Raw SQL (when needed)
result = self.execute_raw_sql_scalar(db, "SELECT COUNT(*) FROM hris.attendance_sessions WHERE as_user_id = :uid", {"uid": user_id})
```

### Error Handling

Always use ATAMS exceptions for consistent API responses:
```python
from atams.exceptions import NotFoundException, BadRequestException

if not site:
    raise NotFoundException("Site not found")
if invalid_data:
    raise BadRequestException("Invalid geofence format")
```

### Security Considerations

- Never commit secrets to `.env` file
- Use `DISPLAY_API_KEY` for display endpoints (no user auth)
- All scan endpoints must validate geofence when `GEOFENCE_ENFORCED=true`
- JWT tokens are single-use only (enforced by `used_jti`)

## API Reference

See `MANUAL_TESTING_GUIDE.md` for complete endpoint documentation with curl examples.

**Main Endpoint Groups**:
- `/api/v1/sites` - Site management (admin, role >= 50)
- `/api/v1/attendance/sites/{si_id}/rolling-token` - QR token generation (display key auth)
- `/api/v1/attendance/scan` - Attendance scanning (user auth)
- `/api/v1/attendance/sessions` - Session queries (user + admin)
- `/api/v1/attendance/events` - Event history (user + admin)
