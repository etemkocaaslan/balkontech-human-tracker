from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_model_service
from schemas.models import ModelInfo
from services.model_service import ModelService

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("", response_model=List[ModelInfo])
def list_models(service: ModelService = Depends(get_model_service)):
    return service.list_models()


@router.get("/{name}", response_model=ModelInfo)
def get_model(name: str, service: ModelService = Depends(get_model_service)):
    info = service.get_model(name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found.")
    return info
