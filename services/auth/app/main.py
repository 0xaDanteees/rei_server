# main.py from auth service

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from fastapi.responses import HTMLResponse

from .db import init_db, close_db
from .settings import settings
from .routers.auth import router as auth_router
from .routers.user import router as user_router
from .routers.account import router as account_router
from pathlib import Path
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/auth/docs",
    redoc_url=None,
    openapi_url="/auth/openapi.json",
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(user_router, prefix="/user", tags=["user"])
app.include_router(account_router, prefix="/account", tags=["account"])

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
    await init_db()

@app.on_event("shutdown")
async def shutdown():
    await close_db()

@app.get("/auth/health")
async def health():
    return {"status": "ok"}


# Serve a simple landing page for Auth at both "/" (local) and "/auth" (Vercel)
def _read_auth_index() -> str:
    index_path = Path(__file__).parent / "index.html"
    try:
        return index_path.read_text(encoding="utf-8")
    except Exception:
        return "<html><body><h1>Auth Service</h1><p>Landing page unavailable.</p></body></html>"


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
async def auth_root_index():
    return _read_auth_index()


@app.get("/auth", include_in_schema=False, response_class=HTMLResponse)
async def auth_prefixed_index():
    return _read_auth_index()
