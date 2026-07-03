"""
SessionService — session lifecycle management.

Responsibilities: create, list, and delete sessions.
Inference is handled by TrackingService; this service only manages state.
"""

import logging
import uuid

from typing import List

from core.interfaces import ModelRegistryProtocol, SessionStoreProtocol
from core.tracker import build_bytetrack, load_detector
from schemas.sessions import SessionCreateRequest, SessionInfo

logger = logging.getLogger(__name__)


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
        Resolve the detector model, build a ByteTrack instance, and create a session.
        Raises ValueError if the model cannot be found.
        """
        model_path = self._registry.get_detector_path(req.detector_model)
        if model_path is None:
            raise ValueError(
                f"Detector model '{req.detector_model}' not found. "
                "Place it in models/ or provide an absolute path."
            )

        if req.tracker_type != "bytetrack":
            raise ValueError(f"Unsupported tracker type: '{req.tracker_type}'. Supported: bytetrack")

        detector = load_detector(model_path)
        p = req.tracker_params
        tracker = build_bytetrack(
            track_buffer=p.track_buffer,
            frame_rate=p.frame_rate,
            max_age=p.max_age,
            track_thresh=p.track_thresh,
            min_conf=p.min_conf,
            match_thresh=p.match_thresh,
            min_hits=p.min_hits,
            iou_threshold=p.iou_threshold,
            per_class=p.per_class,
        )

        session_id = str(uuid.uuid4())
        self._store.create(session_id, detector, tracker, req)
        logger.info("Session created: %s | model=%s | device=%s", session_id[:8], req.detector_model, req.device)

        return SessionInfo(
            session_id=session_id,
            detector_model=req.detector_model,
            tracker_type=req.tracker_type,
            device=req.device,
            target_classes=req.target_classes,
        )

    def get_session_ids(self) -> List[str]:
        return self._store.list_ids()

    def exists(self, session_id: str) -> bool:
        return self._store.get(session_id) is not None

    def delete(self, session_id: str) -> bool:
        return self._store.delete(session_id)
