"""
ModelBootstrapper — downloads default models on first boot.

Detector downloads  → Ultralytics auto-download (YOLO("yolov8n.pt") pulls from hub)
ReID downloads      → BoxMOT's TRAINED_URLS registry + gdown
Custom models       → Hugging Face Hub (set HF_MODEL_REPO env var)
"""

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import os

logger = logging.getLogger(__name__)

# ── Default models downloaded when directories are empty ──────────────────────

DEFAULT_DETECTOR = "yolov8n.pt"             # smallest YOLO — always a safe fallback
DEFAULT_REID     = "osnet_x0_25_msmt17.pt"  # smallest OSNet, motion-only trackers skip this

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ModelBootstrapper:
    models_dir: Path = field(
        default_factory=lambda: (
            Path(os.getenv("MODELS_DIR")) if os.getenv("MODELS_DIR")
            else _PROJECT_ROOT / "models"
        )
    )

    default_detectors: List[str] = field(default_factory=lambda: [DEFAULT_DETECTOR])
    default_reid: List[str]      = field(default_factory=lambda: [DEFAULT_REID])
    ensure_detectors: bool = True
    ensure_reid: bool      = True

    # Custom models pulled from Hugging Face Hub.
    # HF_MODEL_REPO=<owner>/<repo>   — the HF dataset/model repo
    # HF_MODELS=file1.pt,file2.pt    — comma-separated list of filenames to download
    hf_repo_id: Optional[str] = field(
        default_factory=lambda: os.getenv("HF_MODEL_REPO")
    )
    hf_models: List[str] = field(
        default_factory=lambda: (
            [m.strip() for m in os.getenv("HF_MODELS", "").split(",") if m.strip()]
        )
    )

    # ── Public entry point ────────────────────────────────────────────────────

    def bootstrap(self) -> None:
        """Check both model dirs and download anything missing."""
        self.models_dir.mkdir(parents=True, exist_ok=True)

        if self.ensure_detectors:
            self._ensure_detectors()

        if self.ensure_reid:
            self._ensure_reid()

        if self.hf_repo_id and self.hf_models:
            self._ensure_hf_models()

    # ── Detectors ─────────────────────────────────────────────────────────────

    def _ensure_detectors(self) -> None:
        dest_dir = self.models_dir / "detectors"
        dest_dir.mkdir(parents=True, exist_ok=True)

        for model_name in self.default_detectors:
            dest = dest_dir / model_name
            if dest.exists():
                logger.info("Detector already present: %s", model_name)
                continue
            self._download_detector(model_name, dest)

    def _download_detector(self, model_name: str, dest: Path) -> None:
        """
        Ultralytics YOLO auto-downloads to its cache when instantiated.
        We locate the cached file and copy it to our models dir.
        """
        logger.info("Downloading detector: %s", model_name)
        try:
            from ultralytics import YOLO
            from ultralytics.utils import WEIGHTS_DIR

            # Instantiating YOLO triggers download to the ultralytics cache directory
            model = YOLO(model_name)

            # Locate the downloaded file — ultralytics may put it in cwd or WEIGHTS_DIR
            candidates = [
                Path(model_name),
                Path.cwd() / model_name,
                WEIGHTS_DIR / model_name,
            ]
            if hasattr(model, "ckpt_path") and model.ckpt_path:
                candidates.insert(0, Path(model.ckpt_path))

            source: Optional[Path] = None
            for c in candidates:
                if c.exists():
                    source = c
                    break

            if source is None:
                logger.warning("Could not locate downloaded %s — skipping copy.", model_name)
                return

            shutil.copy2(source, dest)
            logger.info("Detector saved: %s", dest)

        except Exception as e:
            logger.error("Failed to download detector '%s': %s", model_name, e)

    # ── ReID models ───────────────────────────────────────────────────────────

    def _ensure_reid(self) -> None:
        dest_dir = self.models_dir / "reid"
        dest_dir.mkdir(parents=True, exist_ok=True)

        for model_name in self.default_reid:
            dest = dest_dir / model_name
            if dest.exists():
                logger.info("ReID model already present: %s", model_name)
                continue
            self._download_reid(model_name, dest)

    def _download_reid(self, model_name: str, dest: Path) -> None:
        """
        Uses BoxMOT's TRAINED_URLS registry to resolve the Google Drive URL,
        then downloads with gdown.
        """
        logger.info("Downloading ReID model: %s", model_name)
        try:
            from boxmot.reid.core.config import TRAINED_URLS
            import gdown

            url = TRAINED_URLS.get(model_name)
            if url is None:
                logger.warning(
                    "'%s' not found in BoxMOT TRAINED_URLS. Available: %s",
                    model_name, list(TRAINED_URLS.keys()),
                )
                return

            gdown.download(url, str(dest), quiet=False)

            if dest.exists():
                logger.info("ReID model saved: %s", dest)
            else:
                logger.warning("gdown completed but file not found at %s", dest)

        except Exception as e:
            logger.error("Failed to download ReID model '%s': %s", model_name, e)

    # ── Hugging Face custom models ────────────────────────────────────────────

    def _ensure_hf_models(self) -> None:
        dest_dir = self.models_dir / "detectors"
        dest_dir.mkdir(parents=True, exist_ok=True)

        for model_name in self.hf_models:
            dest = dest_dir / model_name
            if dest.exists():
                logger.info("Custom model already present: %s", model_name)
                continue
            self._download_from_hf(model_name, dest)

    def _download_from_hf(self, model_name: str, dest: Path) -> None:
        """Download a file from Hugging Face Hub into our detectors directory."""
        logger.info("Downloading custom model from HF Hub: %s/%s", self.hf_repo_id, model_name)
        try:
            from huggingface_hub import hf_hub_download

            cached = hf_hub_download(
                repo_id=self.hf_repo_id,
                filename=model_name,
            )
            shutil.copy2(cached, dest)
            logger.info("Custom model saved: %s", dest)

        except Exception as e:
            logger.error(
                "Failed to download '%s' from HF Hub repo '%s': %s",
                model_name, self.hf_repo_id, e,
            )
