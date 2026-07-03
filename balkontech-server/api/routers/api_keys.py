"""
API key management endpoints — admin only (no auth required).
These are mounted at /admin/keys, not under /api/v1/.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies import get_api_key_store
from storage.api_key_store import ApiKeyStore

router = APIRouter(prefix="/admin/keys", tags=["Admin — API Keys"])


class CreateKeyRequest(BaseModel):
    name: str


@router.post("", status_code=201)
def create_key(
    req: CreateKeyRequest,
    store: ApiKeyStore = Depends(get_api_key_store),
):
    """Create a new API key. The raw key is returned only once — save it immediately."""
    if not req.name.strip():
        raise HTTPException(400, "Key name cannot be empty.")
    raw = store.create(req.name)
    return {"raw_key": raw, "message": "Save this key — it will not be shown again."}


@router.get("")
def list_keys(store: ApiKeyStore = Depends(get_api_key_store)):
    return store.list_keys()


@router.delete("/{key_id}", status_code=204)
def delete_key(
    key_id: str,
    store: ApiKeyStore = Depends(get_api_key_store),
):
    if not store.delete(key_id):
        raise HTTPException(404, f"Key '{key_id}' not found.")
