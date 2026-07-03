"""
/api/v1/ — Public API router.

All existing routers are re-mounted here with the /api/v1 prefix.
Access requires X-API-Key header (enforced by ApiKeyMiddleware in main.py).
"""

from fastapi import APIRouter

from api.routers import models, sessions, stream, zones

# Aggregate all public routers under /api/v1
router = APIRouter(prefix="/api/v1")

router.include_router(models.router)
router.include_router(sessions.router)
router.include_router(stream.router)
router.include_router(zones.router)


@router.get("/health", tags=["Health"])
def api_health():
    return {"status": "ok", "version": "1.0.0"}
