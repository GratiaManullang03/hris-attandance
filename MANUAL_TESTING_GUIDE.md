# Manual Testing Guide - HRIS Attendance API

## Prerequisites

1. Make sure your API server is running
2. Have access to:
   - Admin user with role level >= 50 (for Sites endpoints)
   - Regular user with role level >= 1 (for Attendance endpoints)
   - Display API Key (for rolling token)
3. Use tools like:
   - **Postman** (recommended)
   - **curl** commands
   - **HTTPie**
   - **Thunder Client** (VS Code extension)

## Authentication Setup

For all endpoints that require authentication, you need to include the JWT token in the Authorization header:

```
Authorization: Bearer YOUR_JWT_TOKEN
```

## Sites Endpoints Testing

### 1. POST /api/v1/sites/ - Create Site

**Prerequisites:** Admin authentication (role level >= 50)

```bash
curl -X POST "http://localhost:8000/api/v1/sites/" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "si_id": "OFFICE_JKT",
    "si_name": "Jakarta Office",
    "si_geo_fence": {
      "type": "circle",
      "center": [-6.2088, 106.8456],
      "radius_m": 100
    }
  }'
```

**Expected Response (201):**
```json
{
  "success": true,
  "message": "Site created successfully",
  "data": {
    "si_id": "OFFICE_JKT",
    "si_name": "Jakarta Office",
    "si_geo_fence": {
      "type": "circle",
      "center": [-6.2088, 106.8456],
      "radius_m": 100
    },
    "si_created_at": "2025-10-20T16:47:09.587802+00:00",
    "si_updated_at": null
  }
}
```

### 2. PUT /api/v1/sites/{si_id} - Update Site

```bash
curl -X PUT "http://localhost:8000/api/v1/sites/OFFICE_JKT" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "si_name": "Jakarta Head Office",
    "si_geo_fence": {
      "type": "circle",
      "center": [-6.2088, 106.8456],
      "radius_m": 150
    }
  }'
```

**Expected Response (200):**
```json
{
  "success": true,
  "message": "Site updated successfully",
  "data": {
    "si_id": "OFFICE_JKT",
    "si_name": "Jakarta Head Office",
    "si_geo_fence": {
      "type": "circle",
      "center": [-6.2088, 106.8456],
      "radius_m": 150
    },
    "si_created_at": "2025-10-20T16:47:09.587802+00:00",
    "si_updated_at": "2025-10-20T17:00:00.000000+00:00"
  }
}
```

### 3. GET /api/v1/sites/ - List Sites

```bash
curl -X GET "http://localhost:8000/api/v1/sites/?search=Jakarta&skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN"
```

**Expected Response (200):**
```json
{
  "success": true,
  "message": "Sites retrieved successfully",
  "data": [
    {
      "si_id": "OFFICE_JKT",
      "si_name": "Jakarta Head Office",
      "si_geo_fence": {
        "type": "circle",
        "center": [-6.2088, 106.8456],
        "radius_m": 150
      },
      "si_created_at": "2025-10-20T16:47:09.587802+00:00",
      "si_updated_at": "2025-10-20T17:00:00.000000+00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

### 4. GET /api/v1/sites/{si_id} - Get Single Site

```bash
curl -X GET "http://localhost:8000/api/v1/sites/OFFICE_JKT" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN"
```

### 5. DELETE /api/v1/sites/{si_id} - Delete Site

```bash
curl -X DELETE "http://localhost:8000/api/v1/sites/OFFICE_JKT" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN"
```

**Expected Response (204):** No content

---

## Attendance Endpoints Testing

### 1. GET /api/v1/attendance/sites/{si_id}/rolling-token - Get Rolling Token

**Prerequisites:** Display API Key (no user auth required)

```bash
curl -X GET "http://localhost:8000/api/v1/attendance/sites/OFFICE_JKT/rolling-token" \
  -H "X-Display-Key: YOUR_DISPLAY_API_KEY"
```

**Expected Response (200):**
```json
{
  "success": true,
  "message": "Rolling token generated successfully",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "slot_timestamp": "2025-10-20T17:00:00Z",
    "expires_in": 12
  }
}
```

### 2. POST /api/v1/attendance/scan - Scan Attendance

**Prerequisites:** User authentication (role level >= 1)

**Step 1:** Get a rolling token first (from step 1)
**Step 2:** Use the token to scan

```bash
curl -X POST "http://localhost:8000/api/v1/attendance/scan" \
  -H "Authorization: Bearer YOUR_USER_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "qr_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user_location": {
      "latitude": -6.2088,
      "longitude": 106.8456
    }
  }'
```

**Expected Response - Check In (200):**
```json
{
  "success": true,
  "message": "Attendance scanned successfully",
  "data": {
    "as_status": "checked-in",
    "session": {
      "as_id": "uuid-here",
      "as_user_id": 123,
      "as_si_id": "OFFICE_JKT",
      "as_check_in": "2025-10-20T17:00:00+00:00",
      "as_check_out": null,
      "as_status": "open"
    },
    "message": "Successfully checked in at Jakarta Head Office"
  }
}
```

**Expected Response - Check Out (200):**
```json
{
  "success": true,
  "message": "Attendance scanned successfully",
  "data": {
    "as_status": "checked-out",
    "session": {
      "as_id": "uuid-here",
      "as_user_id": 123,
      "as_si_id": "OFFICE_JKT",
      "as_check_in": "2025-10-20T17:00:00+00:00",
      "as_check_out": "2025-10-20T18:00:00+00:00",
      "as_status": "closed"
    },
    "message": "Successfully checked out from Jakarta Head Office"
  }
}
```

### 3. GET /api/v1/attendance/sessions/me/today - Get My Today's Session

```bash
curl -X GET "http://localhost:8000/api/v1/attendance/sessions/me/today" \
  -H "Authorization: Bearer YOUR_USER_JWT_TOKEN"
```

**Expected Response (200):**
```json
{
  "success": true,
  "message": "Today's session retrieved successfully",
  "data": {
    "session": {
      "as_id": "uuid-here",
      "as_user_id": 123,
      "as_si_id": "OFFICE_JKT",
      "as_check_in": "2025-10-20T17:00:00+00:00",
      "as_check_out": null,
      "as_status": "open"
    },
    "site_name": "Jakarta Head Office"
  }
}
```

### 4. GET /api/v1/attendance/events/me - Get My Events

```bash
curl -X GET "http://localhost:8000/api/v1/attendance/events/me?date=2025-10-20&limit=10&offset=0" \
  -H "Authorization: Bearer YOUR_USER_JWT_TOKEN"
```

**Expected Response (200):**
```json
{
  "success": true,
  "message": "Events retrieved successfully",
  "data": [
    {
      "ae_id": "uuid-here",
      "ae_as_id": "session-uuid",
      "ae_type": "check-in",
      "ae_timestamp": "2025-10-20T17:00:00+00:00",
      "ae_location": {
        "latitude": -6.2088,
        "longitude": 106.8456
      }
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

### 5. GET /api/v1/attendance/sessions - Get Sessions (Admin)

**Prerequisites:** Admin authentication (role level >= 50)

```bash
curl -X GET "http://localhost:8000/api/v1/attendance/sessions?user_id=123&site_id=OFFICE_JKT&date_from=2025-10-20&date_to=2025-10-20&status=open&limit=10&offset=0&sort=desc" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN"
```

**Expected Response (200):**
```json
{
  "success": true,
  "message": "Sessions retrieved successfully",
  "data": [
    {
      "as_id": "uuid-here",
      "as_user_id": 123,
      "as_si_id": "OFFICE_JKT",
      "as_check_in": "2025-10-20T17:00:00+00:00",
      "as_check_out": null,
      "as_status": "open",
      "as_created_at": "2025-10-20T17:00:00+00:00",
      "as_updated_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

---

## Testing Scenarios

### Complete Attendance Flow Test

1. **Create a site** (POST /sites/)
2. **Get rolling token** (GET /attendance/sites/{si_id}/rolling-token)
3. **Check in** (POST /attendance/scan) - use token from step 2
4. **Verify today's session** (GET /attendance/sessions/me/today)
5. **Check my events** (GET /attendance/events/me)
6. **Get new rolling token** (GET /attendance/sites/{si_id}/rolling-token)
7. **Check out** (POST /attendance/scan) - use new token from step 6
8. **Verify session is closed** (GET /attendance/sessions/me/today)
9. **Admin check sessions** (GET /attendance/sessions)

### Error Testing Scenarios

1. **Invalid token** - Use expired or invalid JWT token
2. **Geofence violation** - Use location outside geofence radius
3. **Replay attack** - Use same QR token twice
4. **Missing auth** - Call protected endpoints without auth
5. **Insufficient role** - User trying to access admin endpoints

---

## Postman Collection

Create a Postman collection with:

1. **Environment Variables:**
   - `base_url`: http://localhost:8000
   - `admin_token`: YOUR_ADMIN_JWT_TOKEN
   - `user_token`: YOUR_USER_JWT_TOKEN
   - `display_key`: YOUR_DISPLAY_API_KEY
   - `site_id`: OFFICE_JKT

2. **Pre-request Scripts** (for auth headers):
```javascript
pm.request.headers.add({
  key: 'Authorization',
  value: 'Bearer {{admin_token}}'
});
```

3. **Test Scripts** (for response validation):
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has success field", function () {
    pm.expect(pm.response.json()).to.have.property('success');
});
```

---

## Common Issues & Solutions

1. **401 Unauthorized**: Check JWT token validity and authorization header
2. **403 Forbidden**: Check user role level or display API key
3. **400 Bad Request**: Check request body format and required fields
4. **409 Conflict**: Token already used (QR replay protection)
5. **Geofence Error**: Ensure location is within site geofence radius

---

## Environment Configuration

Make sure your `.env` file includes:
```env
DISPLAY_API_KEY=your-display-key
GEOFENCE_ENFORCED=true
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```