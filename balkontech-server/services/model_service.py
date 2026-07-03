"""
ModelService — orchestrates model bootstrapping and registry access.

Single responsibility: answer questions about models and ensure they exist.
Depends on ModelRegistryProtocol and ModelBootstrapper — not on concrete types.
"""

from pathlib import Path
from typing import List, Optional

from core.interfaces import ModelRegistryProtocol
from schemas.models import ModelInfo
from storage.model_bootstrapper import ModelBootstrapper


class ModelService:
    def __init__(
        self,
        registry: ModelRegistryProtocol,
        bootstrapper: ModelBootstrapper,
    ) -> None:
        self._registry = registry
        self._bootstrapper = bootstrapper

    def initialize(self) -> None:
        """Run at startup: ensure defaults exist, then index all models."""
        self._bootstrapper.bootstrap()
        self._registry.scan()

    def list_models(self) -> List[ModelInfo]:
        return self._registry.list_models()

    def get_model(self, name: str) -> Optional[ModelInfo]:
        return self._registry.get_model(name)

    def get_detector_path(self, name: str) -> Optional[Path]:
        return self._registry.get_detector_path(name)

    def get_reid_path(self, name: str) -> Optional[Path]:
        return self._registry.get_reid_path(name)
