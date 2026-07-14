from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.dependencies import get_model_service
from schemas.models import ModelInfo
from services.model_service import ModelService

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("", response_model=List[ModelInfo])
def list_models(service: ModelService = Depends(get_model_service)):
    return service.list_models()


@router.get("/reid/catalog", response_model=List[Dict[str, Any]])
def list_reid_catalog(service: ModelService = Depends(get_model_service)):
    """Return all known ReID models with download status."""
    return service.list_reid_catalog()


@router.post("/reid/{name}/download", status_code=202)
def download_reid_model(
    name: str,
    background_tasks: BackgroundTasks,
    service: ModelService = Depends(get_model_service),
):
    """
    Trigger background download of a ReID model into models/reid/.
    Returns 202 immediately; poll GET /models/reid/catalog to check completion.
    """
    try:
        background_tasks.add_task(service.download_reid_model, name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "downloading", "name": name}


@router.get("/{name}", response_model=ModelInfo)
def get_model(name: str, service: ModelService = Depends(get_model_service)):
    info = service.get_model(name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found.")
    return info
