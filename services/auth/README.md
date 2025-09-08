# Auth Microservice (FastAPI)

Version: 0.1.0

This microservice provides user authentication and account management APIs, including registration, login/logout, password reset/change, profile and avatar management, and account state transitions (deactivate/reactivate/nuke). It is designed for a service-oriented backend and follows consistent response envelopes and error handling.

## Key Features
- Soft delete support (is_nuked) with reusable email after nuke
- Password policy enforcement (min length + complexity)
- JWT access tokens with revocation table
- Avatar upload/replace/delete and retrieval
- Unified response envelope: `{status, message, payload}`
- Async SQLAlchemy + asyncpg (PostgreSQL)
- Alembic migrations

## Project Layout
```
services/auth/
  ├── app/
  │   ├── main.py                # FastAPI app init, global exception handlers, CORS, router includes
  │   ├── db.py                  # Async engine/session factory, FastAPI dependency helpers
  │   ├── settings.py            # Configuration (env-driven)
  │   ├── models.py              # SQLAlchemy models: User, Avatar, RevokedToken, PasswordResetToken
  │   ├── schemas.py             # Pydantic schemas for request/response
  │   ├── security.py            # Password hashing/verify, JWT create/decode, password strength validation
  │   └── routers/
  │       ├── auth.py            # /auth: register/login/logout/forgot/reset/change-password
  │       ├── user.py            # /user: me (+include=avatar), avatar upload/get/delete
  │       └── account.py         # /account: deactivate/reactivate/nuke (with password confirmation)
  ├── migrations/                # Alembic migrations (versions/ and env config)
  └── requirements.txt           # Python dependencies for this microservice
```

## Database (ERP-style summary)
- `users`
  - id (uuid, pk)
  - email (varchar, case-insensitive uniqueness for NOT is_nuked via partial index)
  - password_hash (varchar)
  - is_active (bool, default true)
  - is_nuked (bool, default false)
  - created_at, updated_at (timestamptz, server defaults)
  - Indexes:
    - `idx_users_email_lower_active` unique on lower(email) where NOT is_nuked
    - `idx_users_created_at` (desc)
- `avatars`
  - id (uuid, pk)
  - user_id (uuid, fk users.id, unique)
  - path (varchar)
  - mime_type (varchar)
- `revoked_tokens`
  - id (uuid, pk)
  - user_id (uuid, fk users.id)
  - jti (text)
  - expires_at (timestamptz)
- `password_reset_tokens`
  - id (uuid, pk)
  - user_id (uuid, fk users.id)
  - token (text)
  - expires_at (timestamptz)
  - consumed (bool)

Relations:
- One `User` has zero or one `Avatar` (1:1)
- `RevokedToken` and `PasswordResetToken` link to `User` via `user_id`

## API Summary
- `/auth/register` POST (201): Create a user. Enforces password policy and unique active email.
- `/auth/login` POST (200): Returns JWT access token or 400 on invalid credentials.
- `/auth/logout` POST (200): Revokes current token if provided; idempotent response otherwise.
- `/auth/forgot-password` POST (202): Issues a reset token (in dev it returns the token in payload).
- `/auth/reset-password` POST (200): Consumes reset token and sets a new password.
- `/auth/change-password` POST (200): Authenticated; body includes `current_password` and `new_password`.
- `/user/me` GET (200): Returns current user info; `?include=avatar` adds `avatar_url`.
- `/user/avatar` POST (201): Uploads/replaces avatar (PNG/JPG). GET (200/404). DELETE (200).
- `/account/deactivate` POST (200): Requires password; sets `is_active=false`.
- `/account/reactivate` POST (200): Requires password; allowed only if not nuked.
- `/account/nuke` DELETE (200): Requires password; soft delete `is_nuked=true` and `is_active=false`.

Responses use envelope `{status, message, payload}` consistently. Errors are normalized by the global exception handlers in `app/main.py`.

## Password Policy
Enforced in `security.validate_password_strength` and applied at:
- `POST /auth/register` for new users.
- `POST /auth/change-password` when changing passwords.

Rules:
- At least 8 characters
- At least one uppercase, one lowercase, one digit, and one special character

Existing users are not impacted until they change their password (only admin exists rn)

## Environment & Settings
- Configure via `services/auth/app/settings.py` (e.g., `POSTGRES_DSN`, `JWT_SECRET`, CORS origins, avatar directory, size limits).
- Typical `.env` variables (example):
```
POSTGRES_DSN=postgresql+asyncpg://user:pass@localhost:5432/db
JWT_SECRET=supersecret
CORS_ORIGINS=["*"] # TODO: change this after backend completion
AVATAR_DIR=data/avatars # TODO: change this after backend completion
MAX_AVATAR_MB=2 # TODO: change this after backend completion
```

## Local Development
- Install dependencies:
```
pip install -r requirements.txt
```
- Run migrations:
```
alembic -c services/auth/alembic.ini upgrade head
```
- Start service locally:
```
uvicorn services.auth.app.main:app --reload --port 8200
```
- Visit landing page and Swagger UI:
```
Landing: http://127.0.0.1:8200/ (also at http://127.0.0.1:8200/auth)
Swagger: http://127.0.0.1:8200/auth/docs
OpenAPI: http://127.0.0.1:8200/auth/openapi.json
Health:  http://127.0.0.1:8200/auth/health
```

## Production (Vercel)

- Deployed routes (assuming reicam-server.vercel.app):
```
Landing: https://reicam-server.vercel.app/auth
Swagger: https://reicam-server.vercel.app/auth/docs
OpenAPI: https://reicam-server.vercel.app/auth/openapi.json
Health:  https://reicam-server.vercel.app/auth/health
```

## Testing
- Run all tests from repo root:
```
pytest -q
```
The test suite covers: registration, login/logout, forgot/reset-password, profile/avatar flows, account state actions, and change-password including password policy and should cover all the main functionality if anything is missing please let me know or add it :3

## Notes for Production
- Deploy with multiple workers (e.g., gunicorn + uvicorn workers) and tune DB pool in `db.get_engine()` (pool_size, max_overflow, timeout, recycle).
- Consider PgBouncer for connection pooling.
- Store avatars in object storage (e.g., S3) and serve via CDN. Rumble we familiar with but is shit lol.
- Add rate-limiting and lockout strategies for login endpoints.
- Add token cleanup job for expired revoked tokens.
- is_nuked users clean up and/or quick data transfer to another service for data retention/analysis