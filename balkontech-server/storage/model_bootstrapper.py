"""
ModelBootstrapper

Runs at service startup. For each model category (detectors, reid):
  1. Checks if the directory is empty.
  2. If empty (or a named model is missing), downloads the defaults.

Detector downloads  → Ultralytics auto-download (YOLO("yolov8n.pt") pulls from hub)
ReID downloads      → BoxMOT's TRAINED_URLS registry + gdown

Usage:
    from storage.model_bootstrapper import ModelBootstrapper

    bootstrapper = ModelBootstrapper()
    bootstrapper.bootstrap()          # call once at startup
"""

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import os

# ── Default models downloaded when directories are empty ──────────────────────

DEFAULT_DETECTOR = "yolov8n.pt"          # smallest YOLO — always a safe fallback
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

    # Override these to change which defaults get pulled on first boot
    default_detectors: List[str] = field(default_factory=lambda: [DEFAULT_DETECTOR])
    default_reid: List[str]      = field(default_factory=lambda: [DEFAULT_REID])

    # Set to False to skip a category entirely
    ensure_detectors: bool = True
    ensure_reid: bool      = True

    # ── Public entry point ────────────────────────────────────────────────────

    def bootstrap(self) -> None:
        """Check both model dirs and download anything missing."""
        self.models_dir.mkdir(parents=True, exist_ok=True)

        if self.ensure_detectors:
            self._ensure_detectors()

        if self.ensure_reid:
            self._ensure_reid()

    # ── Detectors ─────────────────────────────────────────────────────────────

    def _ensure_detectors(self) -> None:
        dest_dir = self.models_dir / "detectors"
        dest_dir.mkdir(parents=True, exist_ok=True)

        for model_name in self.default_detectors:
            dest = dest_dir / model_name
            if dest.exists():
                print(f"[Bootstrapper] Detector already present: {model_name}")
                continue
            self._download_detector(model_name, dest)

    def _download_detector(self, model_name: str, dest: Path) -> None:
        """
        Ultralytics YOLO auto-downloads to its cache when instantiated.
        We locate the cached file and copy it to our models dir.
        """
        print(f"[Bootstrapper] Downloading detector: {model_name} ...")
        try:
            from ultralytics import YOLO
            from ultralytics.utils import WEIGHTS_DIR

            # Instantiating triggers download to ultralytics cache
            model = YOLO(model_name)

            # Find the downloaded file — ultralytics puts it in cwd or WEIGHTS_DIR
            candidates = [
                Path(model_name),              # cwd
                Path.cwd() / model_name,
                WEIGHTS_DIR / model_name,
            ]
            # Also check wherever ultralytics actually stored it
            if hasattr(model, "ckpt_path") and model.ckpt_path:
                candidates.insert(0, Path(model.ckpt_path))

            source: Optional[Path] = None
            for c in candidates:
                if c.exists():
                    source = c
                    break

            if source is None:
                print(f"[Bootstrapper] Warning: could not locate downloaded {model_name} — skipping copy.")
                return

            shutil.copy2(source, dest)
            print(f"[Bootstrapper] Detector saved: {dest}")

        except Exception as e:
            print(f"[Bootstrapper] Failed to download detector '{model_name}': {e}")

    # ── ReID models ───────────────────────────────────────────────────────────

    def _ensure_reid(self) -> None:
        dest_dir = self.models_dir / "reid"
        dest_dir.mkdir(parents=True, exist_ok=True)

        for model_name in self.default_reid:
            dest = dest_dir / model_name
            if dest.exists():
                print(f"[Bootstrapper] ReID already present: {model_name}")
                continue
            self._download_reid(model_name, dest)

    def _download_reid(self, model_name: str, dest: Path) -> None:
        """
        Uses BoxMOT's TRAINED_URLS registry to resolve the Google Drive URL,
        then downloads with gdown.
        """
        print(f"[Bootstrapper] Downloading ReID model: {model_name} ...")
        try:
            from boxmot.reid.core.config import TRAINED_URLS
            import gdown

            url = TRAINED_URLS.get(model_name)
            if url is None:
                print(
                    f"[Bootstrapper] '{model_name}' not found in BoxMOT TRAINED_URLS.\n"
                    f"  Available: {list(TRAINED_URLS.keys())}"
                )
                return

            gdown.download(url, str(dest), quiet=False)

            if dest.exists():
                print(f"[Bootstrapper] ReID saved: {dest}")
            else:
                print(f"[Bootstrapper] Warning: gdown finished but file not found at {dest}")

        except Exception as e:
            print(f"[Bootstrapper] Failed to download ReID model '{model_name}': {e}")
