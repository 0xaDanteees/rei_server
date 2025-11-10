from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import httpx

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
async def health_check(request: Request):
    base = str(request.base_url).rstrip("/")
    results = {
        "api": {"status": "ok"},
        "auth": {"status": "down"},
        "partners": {"status": "down"},
        "inventory": {"status": "down"},
        "rag": {"status": "down"},
    }

    async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
        # Try same-deployment relative URLs first (Vercel)
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
                # Local dev fallback to ports if host is localhost/127.0.0.1
                host = request.client.host if request.client else "127.0.0.1"
                if host in ("127.0.0.1", "localhost"):
                    fallback = {
                        "auth": "http://127.0.0.1:8200/auth/health",
                        "partners": "http://127.0.0.1:8300/partners/health",
                        "inventory": "http://127.0.0.1:8400/inventory/health",
                        "rag": "http://127.0.0.1:8500/rag/health",
                    }
                    try:
                        r2 = await client.get(fallback[svc])
                        if r2.status_code == 200:
                            data2 = r2.json()
                            results[svc] = {"status": "ok", **({"db": data2.get("db")} if isinstance(data2, dict) else {})}
                        else:
                            results[svc] = {"status": "down", "code": r2.status_code}
                    except Exception as e2:
                        results[svc] = {"status": "down", "error": str(e2)}
                else:
                    results[svc] = {"status": "down", "error": str(e)}

    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    