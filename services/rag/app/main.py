# main.py from rag service

from fastapi import FastAPI, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from fastapi.responses import HTMLResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from sqlalchemy import text
from .db import init_db, close_db, is_db_enabled, get_engine
from .settings import settings
from .routers import chat as chat_router
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
    release="rag-service@0.1.0",
    integrations=[
        FastApiIntegration(),
        StarletteIntegration(),
    ],
    shutdown_timeout=2,
    debug=True,
)

# Initialize rate limiter - Lower limit for RAG due to expensive LLM calls
limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"], headers_enabled=True)

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/rag/docs",
    redoc_url=None,
    openapi_url="/rag/openapi.json",
    swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}},
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Serve global assets (e.g., /assets/img/auth-waifu.jpg) and API static (for favicon) for local dev parity
try:
    repo_root = Path(__file__).resolve().parents[3]
    assets_dir = (repo_root / "assets").resolve()
    api_dir = (repo_root / "api").resolve()
    if assets_dir.exists() and assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets-static")
    if api_dir.exists() and api_dir.is_dir():
        app.mount("/api", StaticFiles(directory=str(api_dir)), name="api-static")
except Exception:
    # Vercel deployment may not have these directories
    pass

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router.router, prefix="/rag/chat", tags=["chat"])

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"status": 404, "message": "Not Found", "payload": {}},
    )

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
    logger.info("RAG service starting up")
    try:
        await init_db()
        logger.info("RAG service started successfully")
    except Exception as e:
        logger.warning(f"RAG service started without DB: {e}")
        # DB may not be available in stateless Vercel environment
        pass

@app.on_event("shutdown")
async def shutdown():
    logger.info("RAG service shutting down")
    try:
        await close_db()
    except Exception:
        pass

@app.get("/rag/health")
@limiter.limit("200/minute")
async def health(request: Request, response: Response):
    logger.info("RAG health check requested")
    db_status = "down"
    if is_db_enabled():
        try:
            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "up"
            logger.info("RAG service healthy - DB connected")
        except Exception as e:
            logger.error(f"RAG service DB connection failed: {e}")
            db_status = "down"
    return {"status": "ok", "db": db_status}

@app.get("/rag/sentry-debug")
async def trigger_error():
    """Sentry debug endpoint - triggers an error for testing"""
    logger.info("RAG Sentry debug endpoint triggered")
    
    # Capture exception explicitly and flush
    try:
        raise Exception("Sentry test error from RAG Service")
    except Exception as e:
        sentry_sdk.capture_exception(e)
        sentry_sdk.flush(timeout=2.0)
        raise

# Serve a simple landing page for RAG at both "/" (local) and "/rag" (Vercel)
def _read_rag_index() -> str:
    index_path = Path(__file__).parent / "index.html"
    try:
        return index_path.read_text(encoding="utf-8")
    except Exception:
        return "<html><body><h1>RAG Service</h1><p>Landing page unavailable.</p></body></html>"

@app.get("/", include_in_schema=False, response_class=HTMLResponse)
async def rag_root_index():
    return _read_rag_index()

@app.get("/rag", include_in_schema=False, response_class=HTMLResponse)
async def rag_prefixed_index():
    return _read_rag_index()
