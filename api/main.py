from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(
    title="API Gateway",
    version="0.2.0",
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
    swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}})

# Note: Do NOT mount StaticFiles at "/api" or it will overshadow dynamic routes like /api/health on Vercel.

# Serve global assets (e.g., /assets/img/miku.png)
assets_dir = (Path(__file__).resolve().parent.parent / "assets").resolve()
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets-static")

@app.get("/", response_class=HTMLResponse)
def read_root():
    index_path = Path(__file__).parent / "index.html"
    try:
        return index_path.read_text(encoding="utf-8")
    except Exception:
        # Fallback minimal page if the file is not found in some environments
        return "<html><body><h1>Waifu Solutions Backend</h1><p>Landing page unavailable.</p></body></html>"

@app.get("/api/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    