"""
API key middleware — protects all /api/v1/* routes.

Admin routes (/ and /docs etc.) are unprotected.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from storage.api_key_store import ApiKeyStore


class ApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, key_store: ApiKeyStore) -> None:
        super().__init__(app)
        self._store = key_store

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/v1/"):
            return await call_next(request)

        raw_key = (
            request.headers.get("X-API-Key") or
            request.query_params.get("api_key")
        )

        if not raw_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing API key. Provide X-API-Key header."},
            )

        if not self._store.validate(raw_key):
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid API key."},
            )

        return await call_next(request)
