# 1) Skema Database

> Skema: `hris` (ikuti contoh users)
> Konvensi prefix kolom:
>
> * **sites** → `si_*`
> * **attendance_sessions** → `as_*`
> * **attendance_events** → `ae_*`
> * **used_jti** → `uj_*`

```sql
-- =========================================
-- Users (tabel yang memang sudah ada)
-- =========================================
CREATE TABLE pt_atams_indonesia.users (
	u_id bigserial NOT NULL,
	u_username varchar(100) NOT NULL,
	u_email varchar(255) NOT NULL,
	u_password_hash varchar(255) NOT NULL,
	u_full_name varchar(255) NULL,
	u_status varchar(20) DEFAULT 'active'::character varying NULL,
	u_email_verified bool DEFAULT false NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp NULL,
	CONSTRAINT users_pkey PRIMARY KEY (u_id),
	CONSTRAINT users_u_email_key UNIQUE (u_email),
	CONSTRAINT users_u_status_check CHECK (((u_status)::text = ANY (ARRAY[('active'::character varying)::text, ('inactive'::character varying)::text, ('pending_verification'::character varying)::text]))),
	CONSTRAINT users_u_username_key UNIQUE (u_username)
);

-- =========================================
-- 1) Sites (lokasi absensi)
-- =========================================
CREATE TABLE hris.sites (
    si_id              varchar(50) PRIMARY KEY,
    si_name            varchar(255) NOT NULL,
    -- geofence simple: circle { "center": [lat, lon], "radius_m": 150 }
    si_geo_fence       jsonb NULL,
    si_created_at      timestamp DEFAULT CURRENT_TIMESTAMP NULL,
    si_updated_at      timestamp NULL
);

-- =========================================
-- 2) Attendance Sessions (1 sesi = check-in → check-out)
-- =========================================
CREATE TABLE hris.attendance_sessions (
    as_id              bigserial PRIMARY KEY,
    as_user_id         bigint NOT NULL REFERENCES,
    as_site_id         varchar(50) NOT NULL REFERENCES hris.sites(si_id),
    as_checkin_at      timestamp NOT NULL,
    as_checkout_at     timestamp NULL,
    as_status          varchar(10) NOT NULL DEFAULT 'open',
    as_created_at      timestamp DEFAULT CURRENT_TIMESTAMP NULL,
    as_updated_at      timestamp NULL,
    CONSTRAINT attendance_sessions_as_status_check
        CHECK (as_status IN ('open','closed'))
);

-- Satu sesi 'open' per user per hari
CREATE UNIQUE INDEX attendance_sessions_one_open_per_day
    ON hris.attendance_sessions (as_user_id, (DATE(as_checkin_at)))
    WHERE as_status = 'open';

-- =========================================
-- 3) Attendance Events (audit trail setiap aksi)
-- =========================================
CREATE TABLE hris.attendance_events (
    ae_id              bigserial PRIMARY KEY,
    ae_session_id      bigint NOT NULL REFERENCES hris.attendance_sessions(as_id),
    ae_user_id         bigint NOT NULL REFERENCES,
    ae_site_id         varchar(50) NOT NULL REFERENCES hris.sites(si_id),
    ae_event_type      varchar(10) NOT NULL,      -- 'checkin' | 'checkout'
    ae_occurred_at     timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ae_token_jti       varchar(64) NOT NULL,
    ae_lat             double precision NULL,
    ae_lon             double precision NULL,
    ae_device_id       varchar(255) NULL,
    ae_created_at      timestamp DEFAULT CURRENT_TIMESTAMP NULL,
    ae_updated_at      timestamp NULL,
    CONSTRAINT attendance_events_ae_event_type_check
        CHECK (ae_event_type IN ('checkin','checkout'))
);

CREATE INDEX attendance_events_user_time_idx
    ON hris.attendance_events (ae_user_id, ae_occurred_at DESC);

-- =========================================
-- 4) Used JTI (anti-replay token, wajib)
-- =========================================
CREATE TABLE hris.used_jti (
    uj_jti             varchar(64) PRIMARY KEY,
    uj_used_at         timestamp DEFAULT CURRENT_TIMESTAMP NULL
);
```

> **Catatan konsistensi**:
>
> * Semua kolom pakai prefix tabel (`si_`, `as_`, `ae_`, `uj_`).
> * Timestamps: `*_created_at`, `*_updated_at` seperti tabel `users`-mu.
> * FK ke `pt_atams_indonesia.users(u_id)`.

---

# 2) Pembagian Proses: Sinkron vs Asinkron (Wajib Ada)

## Sinkron (request–response HTTP, jalan di API)

1. **Generate Rolling Token QR** (untuk display): `GET /api/v1/attendance/sites/{si_id}/rolling-token`

   * Buat JWT dengan exp pendek (≤ 12s), embed `si_id`, `slot`, `jti`.

2. **Scan & Verifikasi**: `POST /api/v1/attendance/scan`

   * Verifikasi JWT (signature, exp, aud/site)
   * **Anti-replay**: tulis ke `used_jti` (INSERT; jika konflik → tolak)
   * Buat/tutup sesi + catat event audit.

3. **Query status** (untuk UI & admin): sesi hari ini, riwayat, dsb (lihat endpoints).

## Asinkron (background job/service terpisah, tetap **wajib**)

1. **Auto-checkout** harian (mis. 18:00):

   * Menutup semua `attendance_sessions` yang masih `open`.
   * Menambahkan event `checkout` otomatis untuk audit.
2. **Pembersihan `used_jti`**:

   * Hapus record lebih lama dari **1 hari** (atau 7 hari jika mau jejak replay lebih panjang).
   * Menjaga tabel tetap ramping.

> Implementasi job bebas (cron, APScheduler, worker) — tapi **harus ada** karena diwajibkan.

---

# 3) ENV (disusun rapi)

```
APP_ENV=production

# DB
DATABASE_URL=postgresql+psycopg://<user>:<pass>@<host>:<port>/pt_atams_indonesia

# JWT untuk QR (server-signed)
QR_JWT_SECRET=change-this
QR_JWT_ALG=HS256
QR_ROTATION_SECONDS=10
QR_EXPIRE_GRACE_SECONDS=2   # total valid window ≈ 12s

# Display auth (untuk ambil rolling-token)
DISPLAY_API_KEY=display-secret-123

# Auto-checkout
AUTO_CHECKOUT_CRON=0 18 * * *      # jam 18:00 server time
AUTO_CHECKOUT_REASON=auto-policy

# Geofence (server-side, data ambil dari si_geo_fence per site)
GEOFENCE_ENFORCED=true
DEFAULT_GEOFENCE_RADIUS_M=150

# Rate limit scan (implementasi di layer service/repo)
RATE_LIMIT_SCAN_PER_MIN=30
```

---

# 4) Rancangan Endpoint (backend-only)

> Base path: `/api/v1`
> Semua respons konsisten: `{ "success": true|false, "data"?: any, "error"?: string }`

## 📍 Sites

### GET /api/v1/sites

**Deskripsi**: Daftar site untuk admin.
**Query**:

* `search` (opsional)
  **Response**:

```json
{
  "success": true,
  "data": [
    {
      "si_id": "HQ1",
      "si_name": "Headquarters",
      "si_geo_fence": { "type":"circle", "center":[-6.2,106.8], "radius_m":150 }
    }
  ]
}
```

### GET /api/v1/sites/:si_id

**Deskripsi**: Detail satu site.
**Response**:

```json
{
  "success": true,
  "data": {
    "si_id": "HQ1",
    "si_name": "Headquarters",
    "si_geo_fence": { "type":"circle", "center":[-6.2,106.8], "radius_m":150 },
    "si_created_at": "2025-10-20T02:00:00Z",
    "si_updated_at": "2025-10-20T02:00:00Z"
  }
}
```

### POST /api/v1/sites

**Deskripsi**: Buat site.
**Body**:

```json
{
  "si_id": "HQ1",
  "si_name": "Headquarters",
  "si_geo_fence": { "type":"circle", "center":[-6.2,106.8], "radius_m":150 }
}
```

**Validasi**:

* `si_id`: required, unique, max 50
* `si_name`: required
* `si_geo_fence`: required (type circle; wajib ada saat `GEOFENCE_ENFORCED=true`)
  **Response**: `201 Created`

### PUT /api/v1/sites/:si_id

**Deskripsi**: Update site.
**Body**: kolom yang boleh diubah: `si_name`, `si_geo_fence`
**Response**: `200 OK`

### DELETE /api/v1/sites/:si_id

**Deskripsi**: Hapus site jika belum dipakai sesi (jika ada relasi, tolak).
**Response**: `200 OK` atau error dependensi.

---

## 🖥️ Display (Rolling Token)

### GET /api/v1/attendance/sites/:si_id/rolling-token

**Headers**: `X-Display-Key: <DISPLAY_API_KEY>`
**Deskripsi**: Menghasilkan **JWT** untuk QR (berlaku ~`QR_ROTATION_SECONDS + GRACE`).
**Response**:

```json
{
  "success": true,
  "data": {
    "token": "<JWT-string>",
    "slot": 123456789,
    "expires_in": 12
  }
}
```

**Aturan**:

* JWT payload minimal: `iss`, `aud: "site:<si_id>"`, `si_id`, `slot`, `jti`, `iat`, `exp`, `mode:"AUTO"`.

---

## 📱 Scanner (Absensi)

### POST /api/v1/attendance/scan

**Headers**: `Authorization: Bearer <user-jwt>`
**Deskripsi**: Verifikasi token QR, tulis sesi/event, anti-replay via `used_jti`.
**Body**:

```json
{
  "token": "<JWT-from-QR>",
  "ae_lat": -6.2,
  "ae_lon": 106.8,
  "ae_device_id": "Mozilla/5.0 (Linux; Android 14; ...)"
}
```

**Langkah server (sinkron & wajib):**

1. Decode & verifikasi JWT (signature, `exp`, `aud=site:<si_id>`, `si_id`, `jti`).
2. **Anti-replay**: `INSERT INTO used_jti(uj_jti) VALUES ($jti)`

   * Jika **conflict PK** → **409** `"Replay detected"`.
3. **Geofence** (karena wajib): baca `si_geo_fence` → cek radius. Jika gagal → **403**.
4. Tentukan sesi:

   * Jika **belum ada** sesi `open` **hari ini** → buat **check-in**:

     * INSERT `attendance_sessions` (`as_status='open'`, `as_checkin_at=now()`).
     * INSERT `attendance_events` (`ae_event_type='checkin'`, simpan `ae_token_jti`, lat/lon/device).
   * Jika **sudah ada** sesi `open` → lakukan **check-out**:

     * UPDATE `attendance_sessions` (`as_status='closed'`, `as_checkout_at=now()`).
     * INSERT `attendance_events` (`ae_event_type='checkout'`, simpan `jti`, lat/lon/device).

**Response (contoh – check-in):**

```json
{
  "success": true,
  "data": {
    "as_status": "checked-in",
    "si_id": "HQ1",
    "as_id": 123,
    "timestamp": "2025-10-20T01:59:20Z",
    "message": "Hadir ✔ 08:59"
  }
}
```

**Error standar**:

```json
{ "success": false, "error": "Token invalid/expired" }
{ "success": false, "error": "Replay detected" }
{ "success": false, "error": "Out of geofence" }
{ "success": false, "error": "Not allowed" }
```

---

## 👤 Session & History

### GET /api/v1/attendance/sessions/me/today

**Deskripsi**: Status sesi user hari ini.
**Response**:

```json
{
  "success": true,
  "data": {
    "as_id": 123,
    "as_status": "open",
    "si_id": "HQ1",
    "as_checkin_at": "2025-10-20T01:59:20Z",
    "as_checkout_at": null
  }
}
```

### GET /api/v1/attendance/events/me

**Query**:

* `date` (YYYY-MM-DD) – default: hari ini
* `limit` (default 50), `offset`
  **Response**:

```json
{
  "success": true,
  "data": [
    {
      "ae_id": 999,
      "ae_event_type": "checkin",
      "ae_occurred_at": "2025-10-20T01:59:20Z",
      "si_id": "HQ1"
    }
  ]
}
```

### GET /api/v1/attendance/sessions

**Deskripsi**: Admin – list sesi (filterable).
**Query**:

* `user_id`, `si_id`, `date_from`, `date_to`, `status` (`open|closed`), `limit`, `offset`, `sort`
  **Response**: daftar ringkas sesi.

---

## 🧹 Maintenance (Asinkron – Wajib)

### Job: Auto-Checkout (harian 18:00)

**Logic**:

* Tutup semua sesi yang masih `open` di hari berjalan atau melewati jam kebijakan.
* Tambahkan `attendance_events` dengan `ae_event_type='checkout'` dan `ae_device_id='system:auto-checkout'`.

### Job: Purge used_jti

**Logic**:

* `DELETE FROM hris.used_jti WHERE uj_used_at < NOW() - INTERVAL '1 day';`

---

# 5) Respons Konsisten & Validasi Penting

* Selalu balas `{ "success": true|false, ... }`.
* **Idempotensi per token** dijamin lewat `used_jti` (PK).
* **Race condition** saat dua scan cepat:

  * PK `used_jti` memblokir replay.
  * Unique index `attendance_sessions_one_open_per_day` menjamin maksimum 1 sesi `open` per hari; jika clash, tangani pada aplikasi (retry baca status lalu check-out).
* **Geofence**: wajib ON; `si_geo_fence` harus diisi saat create site.
