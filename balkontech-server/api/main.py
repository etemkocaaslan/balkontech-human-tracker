from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.dependencies import get_model_service, get_api_key_store
from api.middleware import ApiKeyMiddleware
from api.routers import models, sessions, stream, ui, zones
from api.routers.api_keys import router as api_keys_router
from api.routers.zone_editor import router as zone_editor_router
from api.v1 import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_model_service().initialize()
    yield


app = FastAPI(
    title="Balkontech Human Tracker",
    version="1.0.0",
    description="Human tracking service with zone management.",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(ApiKeyMiddleware, key_store=get_api_key_store())

# ── Admin routes (no auth) ────────────────────────────────────────────────────
app.include_router(ui.router)           # GET /   GET /ui
app.include_router(api_keys_router)     # GET/POST/DELETE /admin/keys
app.include_router(zone_editor_router)  # GET /zone-editor

# Legacy direct routes (admin use, no auth) — keep for admin panel compatibility
app.include_router(models.router)
app.include_router(sessions.router)
app.include_router(stream.router)
app.include_router(zones.router)

# ── Public API (X-API-Key required via middleware) ────────────────────────────
app.include_router(v1_router)           # /api/v1/*


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "version": "1.0.0"}
