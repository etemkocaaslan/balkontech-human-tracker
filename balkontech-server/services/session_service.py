"""
SessionService — session lifecycle management.

Responsibilities: create, list, and delete sessions.
Inference is handled by TrackingService; this service only manages state.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import List

from core.interfaces import ModelRegistryProtocol, SessionStoreProtocol
from core.tracker import SUPPORTED_TRACKERS, build_tracker, load_detector
from schemas.sessions import SessionCreateRequest, SessionInfo

logger = logging.getLogger(__name__)

_MODELS_DIR = Path(os.getenv("MODELS_DIR", Path(__file__).resolve().parents[1] / "models"))


class SessionService:
    def __init__(
        self,
        session_store: SessionStoreProtocol,
        model_registry: ModelRegistryProtocol,
    ) -> None:
        self._store = session_store
        self._registry = model_registry

    def create(self, req: SessionCreateRequest) -> SessionInfo:
        """
        Resolve the detector model, build the requested tracker, and create a session.
        Raises ValueError if the model or tracker type cannot be resolved.
        """
        # ── Detector ──────────────────────────────────────────────────────────
        model_path = self._registry.get_detector_path(req.detector_model)
        if model_path is None:
            raise ValueError(
                f"Detector model '{req.detector_model}' not found. "
                "Place it in models/detectors/ or provide an absolute path."
            )

        # ── Tracker type validation ────────────────────────────────────────────
        tracker_key = req.tracker_type.lower()
        if tracker_key not in SUPPORTED_TRACKERS:
            raise ValueError(
                f"Unsupported tracker '{req.tracker_type}'. "
                f"Supported: {SUPPORTED_TRACKERS}"
            )

        # ── ReID weights (required for appearance-based trackers) ──────────────
        reid_weights: Path | None = None
        if req.reid_model:
            reid_weights = _MODELS_DIR / "reid" / req.reid_model
            if not reid_weights.exists():
                # Auto-download if it's a known catalog model
                from storage.reid_catalog import CATALOG_BY_NAME
                from storage.model_bootstrapper import ModelBootstrapper
                if req.reid_model in CATALOG_BY_NAME:
                    logger.info("ReID model '%s' not found locally — downloading…", req.reid_model)
                    bootstrapper = ModelBootstrapper(models_dir=_MODELS_DIR)
                    bootstrapper._download_reid(req.reid_model, reid_weights)
                if not reid_weights.exists():
                    raise ValueError(
                        f"ReID model '{req.reid_model}' not found. "
                        "Use 'Download' in the Models tab or POST /models/reid/{name}/download."
                    )

        # ── Build tracker ──────────────────────────────────────────────────────
        detector = load_detector(model_path)
        tracker = build_tracker(
            tracker_type=tracker_key,
            device=req.device,
            reid_weights=reid_weights,
            per_class=req.tracker_params.per_class,
        )

        session_id = str(uuid.uuid4())
        self._store.create(session_id, detector, tracker, req)
        logger.info(
            "Session created: %s | model=%s | tracker=%s | device=%s",
            session_id[:8], req.detector_model, req.tracker_type, req.device,
        )

        return SessionInfo(
            session_id=session_id,
            detector_model=req.detector_model,
            tracker_type=req.tracker_type,
            device=req.device,
            target_classes=req.target_classes,
        )

    def get_session_ids(self) -> List[str]:
        return self._store.list_ids()

    def list_sessions(self) -> List[SessionInfo]:
        """Return full SessionInfo for every active session."""
        result = []
        for sid in self._store.list_ids():
            session = self._store.get(sid)
            if session is None:
                continue
            cfg = session.config
            result.append(SessionInfo(
                session_id=sid,
                detector_model=cfg.detector_model,
                tracker_type=cfg.tracker_type,
                device=cfg.device,
                target_classes=cfg.target_classes,
                status=session.video_pipeline_status,
            ))
        return result

    def exists(self, session_id: str) -> bool:
        return self._store.get(session_id) is not None

    def delete(self, session_id: str) -> bool:
        return self._store.delete(session_id)

    def set_display_options(self, session_id: str, *, show_id: bool) -> bool:
        if not self.exists(session_id):
            return False
        self._store.set_display_options(session_id, show_id=show_id)
        return True
