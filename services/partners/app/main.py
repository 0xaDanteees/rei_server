# main.py from partners service

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from fastapi.responses import HTMLResponse

from sqlalchemy import text
from .db import init_db, close_db, is_db_enabled, get_engine
from .settings import settings
from .routers.partner import router as partner_router
from .routers.clothing import router as clothing_router
from .routers.accesories import router as accesories_router
from .routers.presets import router as presets_router
from .routers.personality import router as personality_router
from .routers.avatars import router as avatars_router
from .websocket import websocket_endpoint
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
    release="partners-service@0.1.0",
    integrations=[
        FastApiIntegration(),
        StarletteIntegration(),
    ],
)

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/partners/docs",
    redoc_url=None,
    openapi_url="/partners/openapi.json",
    swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}},
)

# Serve global assets (e.g., /assets/img/auth-waifu.jpg) and API static (for favicon) for local dev parity
repo_root = Path(__file__).resolve().parents[3]
assets_dir = (repo_root / "assets").resolve()
api_dir = (repo_root / "api").resolve()
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets-static")
if api_dir.exists():
    app.mount("/api", StaticFiles(directory=api_dir), name="api-static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(partner_router, prefix="/partner", tags=["partner"])
app.include_router(clothing_router, prefix="/clothing", tags=["clothing"])
app.include_router(accesories_router, prefix="/accesories", tags=["accesories"])
app.include_router(presets_router, prefix="/presets", tags=["presets"])
app.include_router(personality_router, prefix="/partners/personality", tags=["personality"])
app.include_router(avatars_router, prefix="/partners", tags=["avatars"])

# WebSocket endpoint for avatar reactions
@app.websocket("/partners/ws/{partner_id}")
async def websocket_avatar_endpoint(websocket, partner_id: str):
    await websocket_endpoint(websocket, partner_id)

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
    logger.info("Partners service starting up")
    await init_db()
    logger.info("Partners service started successfully")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Partners service shutting down")
    await close_db()

@app.get("/partners/health")
async def health():
    logger.info("Partners health check requested")
    db_status = "down"
    if is_db_enabled():
        try:
            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "up"
            logger.info("Partners service healthy - DB connected")
        except Exception as e:
            logger.error(f"Partners service DB connection failed: {e}")
            db_status = "down"
    return {"status": "ok", "db": db_status}

@app.get("/partners/sentry-debug")
async def trigger_error():
    """Sentry debug endpoint - triggers an error for testing"""
    logger.info("Partners Sentry debug endpoint triggered")
    raise Exception("Sentry test error from Partners Service")

# Serve a simple landing page for Partners at both "/" (local) and "/partners" (Vercel)
def _read_partners_index() -> str:
    index_path = Path(__file__).parent / "index.html"
    try:
        return index_path.read_text(encoding="utf-8")
    except Exception:
        return "<html><body><h1>Partners Service</h1><p>Landing page unavailable.</p></body></html>"

@app.get("/", include_in_schema=False, response_class=HTMLResponse)
async def partners_root_index():
    return _read_partners_index()

@app.get("/partners", include_in_schema=False, response_class=HTMLResponse)
async def partners_prefixed_index():
    return _read_partners_index()
