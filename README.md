# hris_attendance

AURA Application built with ATAMS toolkit.

## Setup

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run application:
   ```bash
   uvicorn app.main:app --reload
   ```

5. Access API:
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health
   - Example Users API: http://localhost:8000/api/v1/users

## Example Endpoints

This project includes a complete working example (Users CRUD) that demonstrates:
- Complete CRUD operations (GET, POST, PUT, DELETE)
- Two-level authorization (Route + Service)
- Atlas SSO authentication
- Response encryption for GET endpoints
- ORM and Native SQL examples in BaseRepository
- Proper commit/rollback handling
- Proper error handling

**Available endpoints:**
- GET /api/v1/users - List all users (requires role level >= 50)
- GET /api/v1/users/{id} - Get single user (requires role level >= 10)
- POST /api/v1/users - Create user (requires role level >= 50)
- PUT /api/v1/users/{id} - Update user (requires role level >= 10)
- DELETE /api/v1/users/{id} - Delete user (requires role level >= 50)

## Generate CRUD

```bash
atams generate <resource_name>
```

Example:
```bash
atams generate department
```

## Project Structure

```
hris-attendance/
├── app/
│   ├── core/           # Configuration
│   ├── db/             # Database setup
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic schemas
│   ├── repositories/   # Data access layer
│   ├── services/       # Business logic layer
│   └── api/            # API endpoints
├── tests/              # Test files
├── .env.example        # Environment template
└── requirements.txt    # Dependencies
```

## Documentation

See ATAMS documentation for more information.
