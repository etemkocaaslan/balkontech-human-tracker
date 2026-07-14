import base64
from collections import defaultdict
from typing import Dict, List, Optional

import cv2
import numpy as np

from core.interfaces import SessionStoreProtocol
from core.tracker import yolo_to_boxmot
from core.viz import draw_tracks, draw_zones, encode_jpeg
from core.zone import compute_zone_membership
from schemas.sessions import TrackResponse, TrackedObject


class TrackingService:
    def __init__(
        self,
        session_store: SessionStoreProtocol,
        zone_service=None,
    ) -> None:
        self._store = session_store
        self._zone_svc = zone_service

    def process_frame(
        self,
        session_id: str,
        frame_b64: str,
        video_id: Optional[str] = None,
    ) -> TrackResponse:
        session = self._store.get(session_id)
        if session is None:
            raise KeyError(f"Session '{session_id}' not found.")

        # 1) Decode — real dimensions here
        frame = self._decode_frame(frame_b64)
        h, w = frame.shape[:2]
        cfg = session.config

        # 2) Detect
        results = session.detector.predict(
            source=frame,
            conf=cfg.conf_threshold,
            iou=cfg.nms_iou_threshold,
            imgsz=cfg.imgsz,
            device=cfg.device,
            classes=cfg.target_classes,
            verbose=False,
        )

        # 3) BoxMOT format + tracker update
        dets = yolo_to_boxmot(results, cfg.target_classes)
        tracks = session.tracker.update(dets, frame)

        # 4) Fetch zones (real pixel dimensions)
        zones: list = []
        if video_id and self._zone_svc is not None:
            zones = self._zone_svc.get_zones_for_frame(video_id, w, h)

        # 5) Zone membership: {track_id: zone_name}
        zone_map: Dict[int, str] = compute_zone_membership(tracks, zones)

        # 6) Annotate — zones first, then tracks with zone badges
        annotated = frame.copy()
        if zones:
            draw_zones(annotated, zones)
        annotated = draw_tracks(annotated, tracks, zone_map=zone_map, show_id=session.show_id)

        self._store.set_annotated_frame(session_id, encode_jpeg(annotated))

        # 7) Aggregate occupancy: {zone_name: [track_ids]}
        occupancy: Dict[str, List[int]] = defaultdict(list)
        for tid, zname in zone_map.items():
            occupancy[zname].append(tid)
        self._store.set_zone_occupancy(session_id, dict(occupancy))

        # 8) Build response
        track_list = self._build_tracks(tracks)
        self._store.set_track_count(session_id, len(track_list))
        frame_idx = self._store.increment_frame(session_id)

        return TrackResponse(
            session_id=session_id,
            frame_index=frame_idx,
            tracks=track_list,
        )

    def get_latest_frame(self, session_id: str) -> Optional[bytes]:
        session = self._store.get(session_id)
        return session.last_annotated_frame if session else None

    def get_stats(self, session_id: str) -> Optional[dict]:
        return self._store.get_stats(session_id)

    @staticmethod
    def _decode_frame(frame_b64: str) -> np.ndarray:
        try:
            img_bytes = base64.b64decode(frame_b64)
            arr = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError("cv2.imdecode returned None.")
            return frame
        except Exception as e:
            raise ValueError(f"Could not decode frame: {e}") from e

    @staticmethod
    def _build_tracks(tracks: Optional[np.ndarray]) -> List[TrackedObject]:
        if tracks is None or len(tracks) == 0:
            return []
        return [
            TrackedObject(
                track_id=int(t[4]),
                bbox=[float(t[0]), float(t[1]), float(t[2]), float(t[3])],
                confidence=float(t[5]),
                class_id=int(t[6]),
            )
            for t in tracks
        ]
