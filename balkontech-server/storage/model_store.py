"""
ModelStore — file-based model registry.

Scans the models directory on startup and builds an in-memory index.
Accepts model names (looked up in the registry) or absolute file paths.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from schemas.models import ModelInfo

logger = logging.getLogger(__name__)


class ModelStore:

    _PROJECT_ROOT = Path(__file__).resolve().parent.parent

    # Filename substrings that identify a ReID model
    _REID_KEYWORDS = ("reid", "osnet", "clip_", "lmbn", "hacnn", "mlfn")

    def __init__(self, models_dir: Optional[Path] = None) -> None:
        env_dir = os.getenv("MODELS_DIR")
        default = Path(env_dir) if env_dir else (self._PROJECT_ROOT / "models")
        self._models_dir = models_dir or default
        self._registry: Dict[str, ModelInfo] = {}

    # ── ModelRegistryProtocol ─────────────────────────────────────────────────

    def scan(self) -> None:
        """Re-scan the models directory and refresh the index."""
        self._registry.clear()

        # Conventional subdirectories
        for model_type, subdir in [("detector", "detectors"), ("reid", "reid")]:
            folder = self._models_dir / subdir
            if not folder.exists():
                continue
            for pt_file in folder.glob("*.pt"):
                self._register(pt_file, model_type)

        # Root of models dir (no subdirectory required)
        if self._models_dir.exists():
            for pt_file in self._models_dir.glob("*.pt"):
                if pt_file.name not in self._registry:
                    self._register(pt_file, self._classify(pt_file.name))

        logger.info("ModelStore: indexed %d model(s): %s", len(self._registry), list(self._registry.keys()))

    def list_models(self) -> List[ModelInfo]:
        return list(self._registry.values())

    def get_model(self, name: str) -> Optional[ModelInfo]:
        return self._registry.get(name)

    def get_detector_path(self, name: str) -> Optional[Path]:
        """
        Return the path for a detector model.
        Accepts a registered model name or an absolute path to a .pt file.
        """
        info = self._registry.get(name)
        if info and info.type == "detector":
            return Path(info.path)
        p = Path(name)
        if p.exists() and p.suffix == ".pt":
            return p.resolve()
        return None

    def get_reid_path(self, name: str) -> Optional[Path]:
        info = self._registry.get(name)
        if info and info.type == "reid":
            return Path(info.path)
        p = Path(name)
        if p.exists() and p.suffix == ".pt":
            return p.resolve()
        return None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _register(self, pt_file: Path, model_type: str) -> None:
        size_mb = round(pt_file.stat().st_size / (1024 * 1024), 2)
        self._registry[pt_file.name] = ModelInfo(
            name=pt_file.name,
            type=model_type,
            size_mb=size_mb,
            path=str(pt_file.resolve()),
        )

    def _classify(self, filename: str) -> str:
        low = filename.lower()
        return "reid" if any(k in low for k in self._REID_KEYWORDS) else "detector"
