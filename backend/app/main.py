import asyncio
import contextlib
import hashlib
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .config import get_settings
from .sync import sync_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per Fitness First request is noise

# Fitness First only reports check-ins. A check-in younger than this counts as
# "in the gym right now": shown as live if SHOW_LIVE, otherwise held back
# until it's old enough not to reveal where I am.
LIVE_WINDOW = timedelta(hours=2)

CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; connect-src 'self'; font-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    with db.connect(settings.db_path):
        pass  # create schema
    task = asyncio.create_task(sync_loop(settings)) if settings.sync_enabled else None
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Gym Wall of Shame", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp: Response = await call_next(request)
    resp.headers["Content-Security-Policy"] = CSP
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/assets/"):
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif "Cache-Control" not in resp.headers:
        resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/healthz")
def healthz():
    return {"ok": True}


def build_dashboard() -> dict:
    settings = get_settings()
    zone = settings.zone
    now = datetime.now(zone)
    with db.connect(settings.db_path) as conn:
        visits = db.all_visits(conn)
        sync = db.get_meta(conn, "sync") or {}

    sessions, live = [], None
    since = settings.data_start_date
    for v in visits:
        start = v.checkin.astimezone(zone)
        if since and start.date() < since:
            continue
        if v.checkout is None and now - start < LIVE_WINDOW:
            if settings.show_live:
                live = {"since": start.replace(tzinfo=None).isoformat()}
            continue
        end = v.checkout.astimezone(zone) if v.checkout else None
        s = {
            "start": start.replace(tzinfo=None).isoformat(),
            "end": end.replace(tzinfo=None).isoformat() if end else None,
            "minutes": round((end - start).total_seconds() / 60) if end and end > start else None,
        }
        if settings.show_studios and v.studio:
            s["studio"] = v.studio
        sessions.append(s)

    return {
        "title": settings.site_title,
        "timezone": settings.tz,
        "weeklyGoal": settings.weekly_goal,
        "now": now.replace(tzinfo=None, microsecond=0).isoformat(),
        "live": live,
        "sync": {k: sync.get(k) for k in ("state", "last_ok", "next_at")},
        "sessions": sessions,
    }


@app.get("/api/dashboard")
def dashboard(request: Request):
    payload = build_dashboard()
    # The clock ticks every request, so leave it out of the ETag.
    body = json.dumps(payload, separators=(",", ":"))
    etag = '"' + hashlib.sha256(json.dumps({**payload, "now": None}).encode()).hexdigest()[:20] + '"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return Response(body, media_type="application/json", headers={"ETag": etag})


# --- the built Svelte app -------------------------------------------------
_static = get_settings().static_dir
if (_static / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="assets")


@app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
def spa(path: str):
    if path.startswith("api/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    candidate = (_static / path).resolve()
    if path and candidate.is_file() and candidate.is_relative_to(_static.resolve()):
        return FileResponse(candidate)
    index = _static / "index.html"
    if index.is_file():
        return FileResponse(index)
    return JSONResponse({"detail": "frontend not built"}, status_code=404)
