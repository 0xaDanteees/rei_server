# Inventory Microservice (FastAPI)

Version: 0.1.0

This microservice provides product catalog, user inventory, and purchase management APIs: product CRUD, user inventory tracking, product bundles, purchase transactions, and refund processing. It is designed to run alongside other services (e.g., Auth, Partners) on the same Postgres database while keeping migrations independent per service.

Status: MVP ready with comprehensive test coverage and migration infrastructure.

## Key Features

- Product catalog with categories, rarities, and acquisition methods
- User inventory management with usage tracking and metadata
- Product bundles with discount pricing
- Purchase flow with simulated payment processing (ready for real payment integration)
- Refund system with automatic inventory removal
- Flexible pricing supporting free, purchasable, and earnable items
- Comprehensive error handling and validation
- Async SQLAlchemy + asyncpg (PostgreSQL)
- Alembic migrations (per-service) with isolation on shared DB

## Project Layout

``` markdown
services/inventory/
  ├── app/
  │   ├── main.py                # FastAPI app, global handlers, CORS, router includes
  │   ├── db.py                  # Async engine/session factory, FastAPI dependency helpers
  │   ├── settings.py            # Configuration (env-driven)
  │   ├── models.py              # SQLAlchemy models: Product, UserInventory, ProductBundle, UserPurchase
  │   ├── index.html             # Service landing page
  │   ├── security.py            # JWT dependency (imported from auth conventions)
  │   └── routers/
  │       ├── products.py        # /api/products catalog management
  │       ├── inventory.py       # /api/inventory user inventory management
  │       ├── bundles.py         # /api/bundles product bundle management
  │       └── purchases.py       # /api/purchases transaction management
  ├── migrations/                # Alembic migrations (versions/ and env config)
  └── requirements.txt           # Python dependencies for this microservice
```

## Database Overview

- `products`
  - id (uuid, pk)
  - name, description, product_type, category, rarity
  - price_usd, acquisition_method, status
  - attributes (jsonb), image_url, preview_url, tags (jsonb)
  - availability windows: available_from, available_until
  - created_at, updated_at
- `user_inventories`
  - id (uuid, pk)
  - user_id (uuid, fk users.id, indexed, ondelete=CASCADE)
  - product_id (uuid, fk products.id, ondelete=CASCADE)
  - acquired_via, acquired_at, is_equipped, usage_count, last_used_at
  - item_metadata (jsonb) - custom data per user
- `product_bundles`
  - id (uuid, pk)
  - name, description, price_usd, discount_percentage
  - image_url, tags (jsonb), status
  - availability windows: available_from, available_until
  - created_at, updated_at
- `product_bundle_items`
  - id (uuid, pk)
  - bundle_id (uuid, fk product_bundles.id)
  - product_id (uuid, fk products.id)
  - quantity, is_featured
- `user_purchases`
  - id (uuid, pk)
  - user_id (uuid, fk users.id, ondelete=CASCADE)
  - product_id/bundle_id (nullable fks)
  - amount_usd, currency, payment_method, transaction_id
  - status (pending/completed/failed/refunded)
  - purchased_at, processed_at

Relations:

- Products belong to the catalog and can be owned by users via UserInventory
- Bundles contain multiple products via ProductBundleItems
- Purchases track user transactions for products or bundles
- User inventory tracks ownership with acquisition metadata

## API Summary

- `/api/products` GET list, POST create (admin)
- `/api/products/{id}` GET one, PATCH update (admin), DELETE delete (admin)
- `/api/products/categories/list` GET available categories
- `/api/inventory` GET user inventory, POST add item (admin)
- `/api/inventory/{id}` GET one, PATCH update, DELETE remove (admin)
- `/api/inventory/grant/{user_id}/{product_id}` POST grant product to user (admin)
- `/api/bundles` GET list, POST create (admin)
- `/api/bundles/{id}` GET one, PATCH update (admin), DELETE delete (admin)
- `/api/purchases` GET purchase history, POST purchase product/bundle
- `/api/purchases/{id}` GET one purchase, POST refund
- `/api/purchases/product/{product_id}` POST purchase single product
- `/api/purchases/bundle/{bundle_id}` POST purchase product bundle

Responses follow the repo's standard envelope `{status, message, payload}` via global handlers.

## Environment & Settings

- Configure via `services/inventory/app/settings.py` (e.g., `POSTGRES_DSN`, `JWT_SECRET`, CORS origins).
- Typical `.env` variables (example):

``` shell
POSTGRES_DSN=postgresql+asyncpg://user:pass@localhost:5432/db
JWT_SECRET=supersecret
CORS_ORIGINS=["*"]
```

## Local Development

- Install dependencies:

``` shell
pip install -r requirements.txt
```

- Run migrations (shared DB best practice):

``` shell
# Ensure Auth is at head first so `users` exists
make auth-up
# Inventory migrations
make inventory-up
```

- Start the service:

``` shell
uvicorn services.inventory.app.main:app --reload --port 8400
```

- Visit: <http://127.0.0.1:8400/inventory/docs> for Swagger UI

## Testing

- Run tests:

``` shell
pytest services/inventory/app/main_test.py -v
```

- Comprehensive test coverage including:
  - Health endpoint validation
  - Product catalog CRUD operations
  - User inventory management
  - Bundle creation and management
  - Purchase flow (products and bundles)
  - Refund processing
  - Authentication and authorization
  - Edge cases and error handling

## Migrations Workflow (Shared DB, per-service isolation)

- Inventory Alembic env:
  - Uses its own version table `alembic_version_inventory`.
  - Includes a metadata-only dummy `users(id)` so Alembic can resolve the FK to Auth without generating DDL for `users`.
- Makefile targets from repo root:

``` makefile
make inventory-rev m="describe change"   # autogenerate revision from models
make inventory-up                        # apply to head
make inventory-down                      # step back one revision
make inventory-stamp                     # mark current schema as head
```

## Production (Vercel)

- Deployed routes (assuming reicam-server.vercel.app):

``` shell
Landing: https://reicam-server.vercel.app/inventory
Swagger: https://reicam-server.vercel.app/inventory/docs
OpenAPI: https://reicam-server.vercel.app/inventory/openapi.json
Health:  https://reicam-server.vercel.app/inventory/health
```

## Product Types & Categories

- **Appearance**: hair_color, skin_tone, eye_color, body_shape, face_shape
- **Clothing**: tops, bottoms, dresses, shoes, underwear, outerwear
- **Accessories**: piercings, tattoos, jewelry, makeup
- **Personality**: single_trait, trait_pack, personality_preset
- **Consumable**: gift_box, boost_pack

## Acquisition Methods

- **Free**: Available from start
- **Purchase**: Buy with real money
- **Earn**: Unlock through gameplay
- **Gift**: Received as gift/reward
- **Random Drop**: Random loot box/gacha

## Rarity System

- **Common**: Basic items
- **Uncommon**: Slightly rare items
- **Rare**: Hard to find items
- **Epic**: Very rare items
- **Legendary**: Extremely rare items

## Notes for Production

- Integrate with real payment processors (Stripe, PayPal, etc.)
- Implement proper inventory validation and anti-cheat measures
- Add rate limiting and audit logging for purchase endpoints
- Consider moving to schema isolation (`auth` schema, `inventory` schema) if you need stronger boundaries
- Implement proper error recovery for failed payment transactions
- Add inventory analytics and reporting capabilities

## Auth & Permissions

- JWT verification follows the conventions from the Auth service via `services/inventory/app/security.py`.
- Most read endpoints require an authenticated user; write/admin endpoints require an admin flag/role per the Auth service.
- Admin-only endpoints (examples):
  - `POST /api/products`, `PATCH /api/products/{id}`, `DELETE /api/products/{id}`
  - `POST /api/inventory` (grant item), `DELETE /api/inventory/{id}`
  - `POST /api/bundles`, `PATCH /api/bundles/{id}`, `DELETE /api/bundles/{id}`

## Response Envelope

All endpoints return a normalized envelope:

``` json
{ "status": <http_status_int>, "message": <string>, "payload": <object|array> }
```

Errors are mapped into the same envelope by global exception handlers in `app/main.py`.

## Example Requests (local)

Assuming services are running locally and you have a valid Bearer token.

Create a product (admin):

```bash
curl -X POST "http://127.0.0.1:8400/api/products" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Red Dress",
    "description": "Elegant outfit",
    "product_type": "clothing",
    "category": "dresses",
    "rarity": "rare",
    "price_usd": 9.99,
    "acquisition_method": "purchase",
    "status": "active"
  }'
```

List bundles:

```bash
curl -H "Authorization: Bearer $JWT" \
  "http://127.0.0.1:8400/api/bundles?limit=20&offset=0"
```

Purchase a product:

```bash
curl -X POST "http://127.0.0.1:8400/api/purchases/product/$PRODUCT_ID" \
  -H "Authorization: Bearer $JWT"
```

Refund a purchase:

```bash
curl -X POST "http://127.0.0.1:8400/api/purchases/$PURCHASE_ID/refund" \
  -H "Authorization: Bearer $JWT"
```

## Local Endpoints Summary

- Landing: <http://127.0.0.1:8400/>
- Swagger: <http://127.0.0.1:8400/inventory/docs>
- OpenAPI: <http://127.0.0.1:8400/inventory/openapi.json>
- Health:  <http://127.0.0.1:8400/inventory/health>

## Environment Variables (expanded)

```env
POSTGRES_DSN=postgresql+asyncpg://user:pass@localhost:5432/db
JWT_SECRET=supersecret
JWT_ISSUER=waifu_solutions.auth
CORS_ORIGINS=["*"]
LOG_LEVEL=info
```

## Testing Commands

- Run the inventory test suite from repo root:

```bash
python -m pytest services/inventory/app/main_test.py -v
```

- Run a single test:

```bash
python -m pytest services/inventory/app/main_test.py::test_bundle_management_flow -v
```

## Troubleshooting / Known Notes

- Bundle serialization: responses for bundles manually serialize `bundle_items` to include product details (name, rarity, category, price) to avoid Pydantic model validation issues when loading from SQLAlchemy relationships.
- If autogenerate migrations include cross-service tables, verify Alembic env filtering and target metadata.
- Ensure `auth` migrations are applied first on a fresh shared DB so `users` exists.

## Security

- Restrict CORS in production.
- Store secrets in environment variables or managed secret stores (not in code).
- Add rate limiting and audit logging for purchase/refund endpoints.
