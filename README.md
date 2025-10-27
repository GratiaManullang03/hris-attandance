# HRIS Attendance System

QR code-based attendance system built with ATAMS toolkit. This application supports check-in/check-out with geofence validation, rolling QR tokens, and replay attack protection.

## Table of Contents

- [Key Features](#key-features)
- [Setup](#setup)
- [Architecture](#architecture)
- [API Endpoints](#api-endpoints)
  - [Sites Management](#sites-management)
  - [Attendance Operations](#attendance-operations)
- [Business Logic](#business-logic)
- [Security](#security)
- [Testing](#testing)

## Key Features

- **QR-based Attendance**: Rolling JWT tokens to prevent replay attacks
- **Geofence Validation**: User location validation using Haversine formula
- **Session Management**: One active session per user per day
- **Atlas SSO Integration**: Authentication via Atlas Single Sign-On
- **Response Encryption**: Encrypted sensitive data on GET endpoints
- **Audit Trail**: Complete logging for every attendance event

## Setup

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with database and Atlas SSO configuration
```

### 2. Database Configuration

This project uses PostgreSQL with `hris` schema. Ensure the database is created and connection pool is configured in `.env`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=your_database
DB_POOL_SIZE=3
DB_MAX_OVERFLOW=5
```

### 3. Run Application

```bash
uvicorn app.main:app --reload
```

**Access Points:**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Architecture

### Database Schema

Schema: `hris`

**Tables:**

1. **sites** - Office locations with geofence
   - `si_id` (PK): Unique site identifier
   - `si_name`: Location name
   - `si_geo_fence`: JSON geofence config `{"type":"circle", "center":[lat,lon], "radius_m":150}`

2. **attendance_sessions** - Check-in/check-out sessions
   - `as_id` (PK): Auto-increment ID
   - `as_user_id`: User ID from Atlas SSO
   - `as_site_id` (FK): Reference to sites
   - `as_check_in_at`: Check-in timestamp
   - `as_check_out_at`: Check-out timestamp (null if still open)
   - `as_status`: "open" or "closed"
   - **Constraint**: One open session per user per day (unique index)

3. **attendance_events** - Audit log
   - `ae_id` (PK): Auto-increment ID
   - `ae_session_id` (FK): Reference to attendance_sessions
   - `ae_event_type`: "check-in" or "check-out"
   - `ae_location`: JSON user location `{"lat":x, "lon":y}`

4. **used_jti** - Anti-replay protection
   - `uj_jti` (PK): JWT ID from QR token
   - `uj_used_at`: Timestamp when token was used
   - **Constraint**: PK prevents token reuse

### Layered Architecture

```
API Layer (endpoints/)       → Business Logic (services/)       → Data Access (repositories/)       → Database
     ↓                                  ↓                                  ↓
  FastAPI                          Validation                         SQLAlchemy
  Authorization                    Geofence Check                     ORM/Raw SQL
  Response Encryption              Session Management                 Transaction
```

## API Endpoints

### Sites Management

**Base Path:** `/api/v1/sites`  
**Authorization:** Admin only (role level >= 50)

#### GET /api/v1/sites
List all sites with pagination and search.

**Query Parameters:**
- `search`: Filter by site name (optional)
- `skip`: Offset pagination (default: 0)
- `limit`: Records per page (1-1000, default: 100)

**Response:** Encrypted pagination response with list of sites

#### GET /api/v1/sites/{si_id}
Get single site details by ID.

**Response:** Encrypted site data

#### POST /api/v1/sites
Create new site.

**Request Body:**
```json
{
  "si_id": "JKT-HQ",
  "si_name": "Jakarta Headquarters",
  "si_geo_fence": {
    "type": "circle",
    "center": [-6.2088, 106.8456],
    "radius_m": 150
  }
}
```

**Validation:**
- `si_id`: Required, unique, max 50 characters
- `si_name`: Required
- `si_geo_fence`: Required if `GEOFENCE_ENFORCED=true`

#### PUT /api/v1/sites/{si_id}
Update existing site. Updatable fields: `si_name`, `si_geo_fence`.

#### DELETE /api/v1/sites/{si_id}
Delete site.

**Constraint:** Fails if site is referenced by attendance sessions.

---

### Attendance Operations

**Base Path:** `/api/v1/attendance`

#### GET /api/v1/attendance/sites/{si_id}/rolling-token
Generate rolling JWT token for QR display.

**Authorization:** Display API Key (header `X-Display-Key`)

**Response:**
```json
{
  "token": "eyJhbGc...",
  "slot": 1734933600,
  "expires_in": 12
}
```

**Logic:**
- Token expires every ~12 seconds
- Uses slot-based timestamp for synchronization
- Token contains: `si_id`, `slot`, `jti` (unique identifier)

**Validation:**
- Header `X-Display-Key` must match `DISPLAY_API_KEY` in settings
- Site must exist in database

#### POST /api/v1/attendance/scan
Scan QR code for check-in or check-out.

**Authorization:** User authentication (role level >= 1)

**Request Body:**
```json
{
  "qr_token": "eyJhbGc...",
  "location": {
    "lat": -6.2088,
    "lon": 106.8456
  }
}
```

**Response:**
```json
{
  "as_status": "checked-in",
  "session": { ... },
  "message": "Successfully checked in at Jakarta HQ"
}
```

**Logic:**
1. **Token Validation**: Verify JWT signature, expiry, and audience
2. **Anti-Replay**: Insert `jti` to `used_jti` table (409 if already exists)
3. **Geofence Check**: Calculate Haversine distance between user location and site geofence
   - Fails if distance > `radius_m` and `GEOFENCE_ENFORCED=true`
4. **Session Logic**:
   - No open session today → Create new session + check-in event
   - Has open session → Close session + check-out event
5. **Audit Trail**: Record attendance event with location

**Errors:**
- 400: Invalid/expired token, missing location
- 403: Outside geofence
- 409: Replay detected (token already used)

#### GET /api/v1/attendance/sessions/me/today
Check current user's attendance session status for today.

**Authorization:** User authentication (role level >= 1)

**Response:**
```json
{
  "session": { ... },  // null if not checked in
  "is_checked_in": true
}
```

#### GET /api/v1/attendance/events/me
Get user's attendance events history.

**Authorization:** User authentication (role level >= 1)

**Query Parameters:**
- `date`: Filter by date (YYYY-MM-DD, default: today)
- `limit`: Max records (1-100, default: 50)
- `offset`: Skip records (default: 0)

**Response:** Encrypted pagination response with list of events

#### GET /api/v1/attendance/sessions
List attendance sessions (Admin only).

**Authorization:** Admin (role level >= 50)

**Query Parameters:**
- `user_id`: Filter by user
- `site_id`: Filter by site
- `date_from`, `date_to`: Date range (YYYY-MM-DD)
- `status`: Filter "open" or "closed"
- `limit`: Max records (1-1000, default: 100)
- `offset`: Skip records
- `sort`: "asc" or "desc" (default: desc)

**Response:** Encrypted pagination response with list of sessions

## Business Logic

### Geofence Validation

**Haversine Formula** to calculate distance between two coordinates:

```python
def _calculate_distance(lat1, lon1, lat2, lon2) -> float:
    R = 6371000  # Earth radius in meters
    φ1 = radians(lat1)
    φ2 = radians(lat2)
    Δφ = radians(lat2 - lat1)
    Δλ = radians(lon2 - lon1)
    
    a = sin(Δφ/2)**2 + cos(φ1) * cos(φ2) * sin(Δλ/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c
```

Validation fails if `distance > si_geo_fence.radius_m` and `GEOFENCE_ENFORCED=true`.

### Session Management

**Constraint:** One open session per user per day
- Enforced by unique index: `attendance_sessions_one_open_per_day`
- Index on: `(as_user_id, DATE(as_check_in_at), as_status)` WHERE `as_status = 'open'`

**Flow:**
- First scan today → Create new session (status: open)
- Second scan today → Close open session (set `as_check_out_at`, status: closed)
- Third scan onwards → Error because no open session exists

### Anti-Replay Protection

**JWT Token ID (jti):**
- Each token has unique `jti`
- During scan, `jti` is inserted to `used_jti` table
- Primary key constraint prevents duplicate inserts
- 409 Conflict if token was already used

**Cleanup:** Background job needs to delete `used_jti` records older than token expiry (e.g., 1 day).

## Security

### Authentication & Authorization

**Atlas SSO Integration:**
- User JWT is validated via Atlas SSO on every request
- Token contains: `user_id`, `role_level`, etc.
- Dependency injection: `require_auth` and `require_min_role_level(N)`

**Two-Level Authorization:**
1. **Route Level**: FastAPI dependency `require_min_role_level(50)`
2. **Service Level**: Additional validation in service layer

**Display Authentication:**
- Endpoint `/rolling-token` uses API key
- Header: `X-Display-Key` must match `DISPLAY_API_KEY`

### Response Encryption

**GET endpoints** return encrypted response when `ENCRYPTION_ENABLED=true`:
- Uses AES encryption
- Key: `ENCRYPTION_KEY`, IV: `ENCRYPTION_IV` from settings
- Data wrapped in encrypted response format

### Environment Variables

**Critical secrets** that must not be committed:
- `DB_PASSWORD`: Database password
- `ATLAS_ENCRYPTION_KEY`, `ATLAS_ENCRYPTION_IV`: Atlas SSO keys
- `QR_JWT_SECRET`: JWT signing key
- `DISPLAY_API_KEY`: Display authentication
- `ENCRYPTION_KEY`, `ENCRYPTION_IV`: Response encryption

## Testing

### Database Pool Tuning

For Aiven free tier (20 connections max):
```env
DB_POOL_SIZE=3
DB_MAX_OVERFLOW=5
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Generate CRUD Resources

ATAMS CLI to generate boilerplate:

```bash
atams generate <resource_name>
```

Example:
```bash
atams generate department
# Generates: model, schema, repository, service, endpoints
```

## Project Structure

```
hris-attendance/
├── app/
│   ├── core/
│   │   └── config.py          # Settings & configuration
│   ├── db/
│   │   └── session.py         # Database session management
│   ├── models/                # SQLAlchemy ORM models
│   │   ├── site.py
│   │   ├── attendance_session.py
│   │   └── attendance_event.py
│   ├── schemas/               # Pydantic schemas
│   │   ├── site.py
│   │   └── attendance.py
│   ├── repositories/          # Data access layer
│   │   ├── site_repository.py
│   │   └── attendance_repository.py
│   ├── services/              # Business logic
│   │   ├── site_service.py
│   │   ├── attendance_service.py
│   │   └── jwt_service.py
│   └── api/
│       ├── deps.py            # Dependencies (auth, db)
│       └── v1/endpoints/
│           ├── sites.py       # Sites CRUD endpoints
│           └── attendance.py  # Attendance endpoints
├── .env.example               # Environment template
├── requirements.txt           # Python dependencies
├── WARP.md                    # Development guide
└── MANUAL_TESTING_GUIDE.md    # Testing scenarios
```

## Background Jobs (TODO)

Needs to be implemented using APScheduler or cron:

2. **JTI Cleanup Job**
   - Schedule: Daily
   - Task: Delete `used_jti` records older than token expiry (1-7 days)
