from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import httpx
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configure logging
logger = logging.getLogger(__name__)

sentry_sdk.init(
    dsn="https://REDACTED@o0.ingest.sentry.io/0",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
    # Enable sending logs to Sentry
    enable_logs=True,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    traces_sample_rate=1.0,
    # Set profile_session_sample_rate to 1.0 to profile 100%
    # of profile sessions.
    profile_session_sample_rate=1.0,
    # Set profile_lifecycle to "trace" to automatically
    # run the profiler on when there is an active transaction
    profile_lifecycle="trace",
    # Explicitly enable FastAPI and Starlette integrations
    integrations=[
        FastApiIntegration(),
        StarletteIntegration(),
    ],
    # Important for serverless: ensure events are sent before function terminates
    shutdown_timeout=2,  # Wait up to 2 seconds on shutdown
    debug=True,  # Enable debug mode to see Sentry logs in Vercel
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"], headers_enabled=True)

app = FastAPI(
    title="API Gateway",
    version="0.2.0",
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
    swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}})

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Note: Do NOT mount StaticFiles at "/api" or it will overshadow dynamic routes like /api/health on Vercel.

# Serve global assets (e.g., /assets/img/miku.png)
assets_dir = (Path(__file__).resolve().parent.parent / "assets").resolve()
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets-static")

@app.get("/", response_class=HTMLResponse)
def read_root():
    logger.info("API Gateway root accessed")
    index_path = Path(__file__).parent / "index.html"
    try:
        return index_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to load index.html: {e}")
        # Fallback minimal page if the file is not found in some environments
        return "<html><body><h1>Waifu Solutions Backend</h1><p>Landing page unavailable.</p></body></html>"

@app.get("/sentry-debug")
@limiter.limit("5/minute")  # Strict limit for debug endpoint
async def trigger_error(request: Request):
    """Sentry debug endpoint - triggers an error for testing"""
    logger.info("Sentry debug endpoint triggered")
    
    # Capture exception explicitly and flush
    try:
        raise Exception("Sentry test error from API Gateway")
    except Exception as e:
        sentry_sdk.capture_exception(e)
        sentry_sdk.flush(timeout=2.0)  # Wait up to 2 seconds for events to send
        raise  # Re-raise so FastAPI returns 500

@app.get("/api/health")
@limiter.limit("200/minute")  # Higher limit for health checks
async def health_check(request: Request, response: Response):
    logger.info("Health check requested")
    base = str(request.base_url).rstrip("/")
    results = {
        "api": {"status": "ok"},
        "auth": {"status": "down"},
        "partners": {"status": "down"},
        "inventory": {"status": "down"},
        "rag": {"status": "down"},
    }

    async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
        # Check if running locally (development)
        is_local = "localhost" in base or "127.0.0.1" in base
        
        if is_local:
            # Local development: use separate ports
            endpoints = {
                "auth": "http://127.0.0.1:8200/auth/health",
                "partners": "http://127.0.0.1:8300/partners/health",
                "inventory": "http://127.0.0.1:8400/inventory/health",
                "rag": "http://127.0.0.1:8500/rag/health",
            }
        else:
            # Production (Vercel): use same-deployment relative URLs
            endpoints = {
                "auth": f"{base}/auth/health",
                "partners": f"{base}/partners/health",
                "inventory": f"{base}/inventory/health",
                "rag": f"{base}/rag/health",
            }

        for svc, url in endpoints.items():
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    results[svc] = {"status": "ok", **({"db": data.get("db")} if isinstance(data, dict) else {})}
                else:
                    results[svc] = {"status": "down", "code": r.status_code}
            except Exception as e:
                results[svc] = {"status": "down", "error": str(e)}

    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    