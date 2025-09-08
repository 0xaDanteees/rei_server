# Waifu Solutions Backend Monorepo

This repository hosts multiple Python microservices (FastAPI-based) and an API gateway layer. It is designed for incremental growth: clear folder structure, shared conventions, consistent error envelopes, and easy local/dev deployment.

Version: 0.1.0

## Repository Structure
```
.
├── api/
│   └── main.py                  # Entry point for deployment status quick check
├── services/
│   └── auth/                    # Auth microservice (see services/auth/README.md)
│       ├── app/                 # Application code
│       ├── migrations/          # Database migrations
│       └── requirements.txt     # Service-specific dependencies
├── data/
│   └── avatars/                 # Local avatar storage for dev
├── vercel.json                  # Vercel deployment configuration for api and auth
├── requirements.txt             # Root development requirements (tests, etc.)
└── README.md                    # This file :3 >w<
```

## Shared Conventions
- **Language & Framework:** Python 3.9+, FastAPI
- **Async DB:** SQLAlchemy 2 + asyncpg (PostgreSQL)
- **Error Envelope:** Every response conforms to `{status, message, payload}`. Global exception handlers normalize HTTP errors and validation errors.
- **Routers:** Organized under `app/routers/*.py` per microservice.
- **Schemas:** Pydantic v2 models in `app/schemas.py` define request/response contracts.
- **Settings:** `app/settings.py` pulls environment variables (e.g., DSN, secrets, CORS).
- **Database Migrations:** Alembic per service under `services/<svc>/migrations/`.
- **Testing:** `pytest` with `fastapi.testclient.TestClient`.

## How to Create a New Microservice
Use `services/auth` as a reference. A new service should mirror:
```
services/<service_name>/
  ├── app/
  │   ├── main.py          # FastAPI app + exception handlers + router includes
  │   ├── db.py            # Engine/session + FastAPI dependencies
  │   ├── settings.py      # Service-specific settings
  │   ├── models.py        # SQLAlchemy models
  │   ├── schemas.py       # Pydantic schemas
  │   ├── security.py      # Optional: auth helpers/passwords/JWT (if needed)
  │   └── routers/
  │       └── <feature>.py # One or more routers grouped by feature
  ├── migrations/          # Alembic migrations for this service
  └── requirements.txt     # Service-specific dependencies
```

### Minimal FastAPI Skeleton (example)
Create `services/foo/app/main.py`:
```python
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.requests import Request

app = FastAPI(title="Foo Service", version="0.1.0")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    msg = exc.detail if isinstance(exc.detail, str) else "Error"
    return JSONResponse(status_code=exc.status_code, content={"status": exc.status_code, "message": msg, "payload": {}})

@app.get("/health")
async def health():
    return {"status": "ok"}
```

Add `services/foo/requirements.txt` (example):
```
fastapi
uvicorn
pydantic
pydantic-settings
sqlalchemy[asyncio]
asyncpg
python-jose[cryptography]
passlib[bcrypt]
python-multipart
email-validator
alembic
httpx
pytest
```

You can later add `db.py`, `models.py`, `schemas.py`, `routers/`, and `migrations/` as the service evolves.

## Deployment with Vercel (Python)
The `vercel.json` is configured to deploy both `api/main.py` and `services/<service_name>/app/main.py`. Routes are split so that `/<service_name>/(.*)` goes to the `<service_name>` microservice, and everything else hits the `api` entry point.

`vercel.json` (excerpt):
```json
{
  "builds": [
    { "src": "api/main.py", "use": "@vercel/python" },
    { "src": "services/<service_name>/app/main.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/<service_name>/(.*)", "dest": "/services/<service_name>/app/main.py" },
    { "src": "/(.*)", "dest": "/api/main.py" }
  ]
}
```

Notes:
- For an additional microservice (e.g., `foo`), add another build and route block, for example:
```json
{ "src": "services/foo/app/main.py", "use": "@vercel/python" }
```
And route:
```json
{ "src": "/foo/(.*)", "dest": "/services/foo/app/main.py" }
```
- This setup focuses on application startup; database connectivity for production should be configured via environment variables and secured secrets.

## Local Development Workflow
- Create and isolate environments as needed (virtualenv/pyenv).
- Install dependencies:
```
pip install -r requirements.txt
```
- Start the API gateway:
```
uvicorn api.main:app --reload --port 8000
```
- Start a microservice (e.g., auth):
```
uvicorn services.auth.app.main:app --reload --port 8200
```
- Visit Swagger UIs:
```
http://127.0.0.1:8000/docs
http://127.0.0.1:8200/docs
```

# Database and migrations

- Generate migrations folder:
```
alembic -c services/<service_name>/app/alembic.ini init migrations
```

- Run migrations:
```
alembic -c services/<service_name>/app/alembic.ini upgrade head
```

## Best Practices
- **Keep routers small** and focused by domain.
- **Add global exception handlers** early to standardize error envelopes.
- **Validate inputs** at the boundary with Pydantic and service-level validators.
- **Add DB indexes** for frequently queried columns (unique, search, foreign keys).
- **Write tests** for happy paths and edge cases (status codes, envelopes, and content).
- **Run Alembic migrations** per service. Do not share migrations across services.
- **Security:** rotate secrets, restrict CORS in production, consider rate limiting, and centralize auth concerns.

## Roadmap
- Additional microservices (e.g., inventory, billing, rag, <waifu>) can follow the same scaffolding.
- Central API gateway can route to services and perform cross-cutting concerns.
- Shared libraries (DTOs, middleware) can be extracted as internal packages if needed.
