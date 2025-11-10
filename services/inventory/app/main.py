# main.py file for inventory service

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from fastapi.responses import HTMLResponse

from sqlalchemy import text
from .db import init_db, close_db, is_db_enabled, get_engine
from .settings import settings
from .routers.products import router as products_router
from .routers.inventory import router as inventory_router
from .routers.bundles import router as bundles_router
from .routers.purchases import router as purchases_router
from pathlib import Path
from fastapi.staticfiles import StaticFiles
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Sentry
sentry_sdk.init(
    dsn="https://REDACTED@o0.ingest.sentry.io/0",
    send_default_pii=True,
    enable_logs=True,
    traces_sample_rate=1.0,
    profile_session_sample_rate=1.0,
    profile_lifecycle="trace",
    environment="production",
    release="inventory-service@0.1.0",
    integrations=[
        FastApiIntegration(),
        StarletteIntegration(),
    ],
    shutdown_timeout=2,
    debug=True,
)

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/inventory/docs",
    redoc_url=None,
    openapi_url="/inventory/openapi.json",
    swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}},
)

# Serve global assets (e.g., /assets/img/auth-waifu.jpg) and API static (for favicon) for local dev parity
repo_root = Path(__file__).resolve().parents[3]
assets_dir = (repo_root / "assets").resolve()
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets-static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static HTML pages first (before routers that might conflict)
@app.get("/", include_in_schema=False, response_class=HTMLResponse)
async def inventory_root_index():
    return _read_inventory_index()

@app.get("/inventory", include_in_schema=False, response_class=HTMLResponse)
async def inventory_prefixed_index():
    return _read_inventory_index()

# Include routers with API prefixes to avoid conflicts
app.include_router(products_router, prefix="/api/products", tags=["products"])
app.include_router(inventory_router, prefix="/api/inventory", tags=["inventory"])
app.include_router(bundles_router, prefix="/api/bundles", tags=["bundles"])
app.include_router(purchases_router, prefix="/api/purchases", tags=["purchases"])

# Global error handlers to enforce {status, message, payload}
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Error"
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": exc.status_code, "message": message, "payload": {}},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "status": status.HTTP_400_BAD_REQUEST,
            "message": "Validation error",
            "payload": {"errors": exc.errors()},
        },
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "Internal Server Error",
            "payload": {},
        },
    )

@app.on_event("startup")
async def startup():
    logger.info("Inventory service starting up")
    await init_db()
    logger.info("Inventory service started successfully")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Inventory service shutting down")
    await close_db()

@app.get("/inventory/health")
async def health():
    logger.info("Inventory health check requested")
    db_status = "down"
    if is_db_enabled():
        try:
            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "up"
            logger.info("Inventory service healthy - DB connected")
        except Exception as e:
            logger.error(f"Inventory service DB connection failed: {e}")
            db_status = "down"
    return {"status": "ok", "db": db_status}

@app.get("/inventory/sentry-debug")
async def trigger_error():
    """Sentry debug endpoint - triggers an error for testing"""
    logger.info("Inventory Sentry debug endpoint triggered")
    
    # Capture exception explicitly and flush
    try:
        raise Exception("Sentry test error from Inventory Service")
    except Exception as e:
        sentry_sdk.capture_exception(e)
        sentry_sdk.flush(timeout=2.0)
        raise

# Serve a simple landing page for Inventory at both "/" (local) and "/inventory" (Vercel)
def _read_inventory_index() -> str:
    index_path = Path(__file__).parent / "index.html"
    try:
        return index_path.read_text(encoding="utf-8")
    except Exception:
        return "<html><body><h1>Inventory Service</h1><p>Landing page unavailable.</p></body></html>"
