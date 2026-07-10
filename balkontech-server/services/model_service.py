"""
ModelService — orchestrates model bootstrapping and registry access.

Single responsibility: answer questions about models and ensure they exist.
Depends on ModelRegistryProtocol and ModelBootstrapper — not on concrete types.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.interfaces import ModelRegistryProtocol
from schemas.models import ModelInfo
from storage.model_bootstrapper import ModelBootstrapper
from storage.reid_catalog import CATALOG_BY_NAME, REID_CATALOG

_MODELS_DIR = Path(os.getenv("MODELS_DIR", Path(__file__).resolve().parents[1] / "models"))


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

    # ── ReID catalog ──────────────────────────────────────────────────────────

    def list_reid_catalog(self) -> List[Dict[str, Any]]:
        """Return the full ReID catalog with a 'downloaded' flag for each entry."""
        reid_dir = _MODELS_DIR / "reid"
        result = []
        for entry in REID_CATALOG:
            item = dict(entry)
            item["downloaded"] = (reid_dir / entry["name"]).exists()
            result.append(item)
        return result

    def download_reid_model(self, name: str) -> None:
        """
        Download a named ReID model into models/reid/.
        Raises ValueError for unknown names; logs (does not raise) on download failure
        so that FastAPI BackgroundTasks does not crash the ASGI worker.
        """
        import logging
        log = logging.getLogger(__name__)

        if name not in CATALOG_BY_NAME:
            raise ValueError(
                f"Unknown ReID model '{name}'. "
                f"Available: {sorted(CATALOG_BY_NAME)}"
            )
        dest = _MODELS_DIR / "reid" / name
        if dest.exists():
            return  # already downloaded
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._bootstrapper._download_reid(name, dest)
        except Exception as exc:
            log.error("ReID download failed for '%s': %s", name, exc)
            return
        if not dest.exists():
            log.error("Download of '%s' completed but file not found at %s", name, dest)
