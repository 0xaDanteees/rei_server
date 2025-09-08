# Partners Microservice (FastAPI)

Version: 0.1.0

This microservice provides partner (NPC) management APIs: CRUD on partners, clothing catalog and partner equipment, accessories (piercings, tattoos), and presets to quickly generate partners. It is designed to run alongside other services (e.g., Auth) on the same Postgres database while keeping migrations independent per service.

NOTE: This module remains pending for proper testing and implementation.

## Key Features
- Partner CRUD with ownership checks (JWT required)
- Clothing catalog + partner clothing (equip/unequip)
- Accessories: piercings and tattoos
- Presets to bootstrap partners
- Async SQLAlchemy + asyncpg (PostgreSQL)
- Alembic migrations (per-service) with isolation on shared DB

## Project Layout
```
services/partners/
  ├── app/
  │   ├── main.py                # FastAPI app, global handlers, CORS, router includes
  │   ├── db.py                  # Async engine/session factory, FastAPI dependency helpers
  │   ├── settings.py            # Configuration (env-driven)
  │   ├── models.py              # SQLAlchemy models: Partner, ClothingItem, PartnerClothing, PartnerPiercing, PartnerTattoo
  │   ├── routers/
  │   │   ├── partner.py         # /partner CRUD + search
  │   │   ├── clothing.py        # /clothing catalog + partner clothing
  │   │   └── accesories.py      # /accesories piercings & tattoos
  │   └── security.py            # JWT dependency (imported from auth conventions)
  ├── migrations/                # Alembic migrations (versions/ and env config)
  └── requirements.txt           # Python dependencies for this microservice
```

## Database Overview
- `partners`
  - id (uuid, pk)
  - user_id (uuid, fk users.id, indexed, ondelete=CASCADE)
  - name (varchar)
  - gender, age, appearance traits (enums/strings)
  - created_at, updated_at
- `clothing_items`
  - id (uuid, pk)
  - name, category, sub_category, color, size, price, flags (available/premium/gift/bought)
  - created_at, updated_at, bought_at, dropped_at, gifted_at
- `partner_clothing`
  - id (uuid, pk)
  - partner_id (uuid, fk partners.id)
  - clothing_item_id (uuid, fk clothing_items.id)
  - slot, is_equipped
- `partner_piercings`
  - id (uuid, pk)
  - partner_id (uuid, fk partners.id)
  - location, jewelry_type/material/color, size
- `partner_tattoos`
  - id (uuid, pk)
  - partner_id (uuid, fk partners.id)
  - location, tattoo_type/style/color, size, image_url

Relations:
- A Partner belongs to a User (Auth service), via `user_id`.
- Clothing, piercings, tattoos belong to a Partner.

## API Summary
- `/partner` GET list, POST create
- `/partner/{id}` GET one, PATCH update, DELETE delete
- `/partner/search` GET filtered list
- `/clothing/catalog` GET items
- `/clothing/partner/{partner_id}` GET, POST (equip)
- `/clothing/{partner_clothing_id}` PATCH, DELETE
- `/accesories/piercings/{partner_id}` GET, POST
- `/accesories/piercings/{piercing_id}` PATCH, DELETE
- `/accesories/tattoos/{partner_id}` GET, POST
- `/accesories/tattoos/{tattoo_id}` PATCH, DELETE
- `/presets` GET list
- `/presets/apply/{preset_key}` POST create from preset

Responses follow the repo’s standard envelope `{status, message, payload}` via global handlers.

## Environment & Settings
- Configure via `services/partners/app/settings.py` (e.g., `POSTGRES_DSN`, `JWT_SECRET`, CORS origins, directories).
- Typical `.env` variables (example):
```
POSTGRES_DSN=postgresql+asyncpg://user:pass@localhost:5432/db
JWT_SECRET=supersecret
CORS_ORIGINS=["*"]
```

## Local Development
- Install dependencies:
```
pip install -r requirements.txt
```
- Run migrations (shared DB best practice):
```
# Ensure Auth is at head first so `users` exists
make auth-up
# Partners migrations
make partners-up
```
- Start service locally:
```
uvicorn services.partners.app.main:app --reload --port 8300
```
- Visit landing page and Swagger UI:
```
Landing: http://127.0.0.1:8300/ (also at http://127.0.0.1:8300/partners)
Swagger: http://127.0.0.1:8300/partners/docs
OpenAPI: http://127.0.0.1:8300/partners/openapi.json
Health:  http://127.0.0.1:8300/partners/health
```

## Migrations Workflow (Shared DB, per-service isolation)
- Partners Alembic env:
  - Uses a service-only include filter so autogenerate touches only Partners tables.
  - Uses its own version table `alembic_version_partners`.
  - Includes a metadata-only dummy `users(id)` so Alembic can resolve the FK to Auth without generating DDL for `users`.
- Makefile targets from repo root:
```
make partners-rev m="describe change"   # autogenerate revision from models
make partners-up                         # apply to head
make partners-down                       # step back one revision
make partners-stamp                      # mark current schema as head
```

## Production (Vercel)
- Deployed routes (assuming reicam-server.vercel.app):
```
Landing: https://reicam-server.vercel.app/partners
Swagger: https://reicam-server.vercel.app/partners/docs
OpenAPI: https://reicam-server.vercel.app/partners/openapi.json
Health:  https://reicam-server.vercel.app/partners/health
```

## Testing
- Run all tests from repo root:
```
pytest -q
```

## Notes for Production
- Tune DB pool in `db.get_engine()` (pool_size, max_overflow, timeouts) and consider PgBouncer.
- Lock down CORS in production.
- Add rate limiting and audit logging for sensitive operations.
- Consider moving to schema isolation (`auth` schema, `partners` schema) if you need stronger boundaries while sharing a DB.
