"""
VideoSourceService — background video ingestion per session.

Starts one thread per session that reads a video file with cv2.VideoCapture,
runs detection + tracking, and writes annotated frames into SessionStore.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np

from core.tracker import yolo_to_boxmot
from core.viz import draw_tracks, draw_zones, encode_jpeg
from core.zone import compute_zone_membership
from schemas.video_source import VideoSourceRequest, VideoSourceStatus
from services.snapshot_service import _resolve_video_path

logger = logging.getLogger(__name__)


@dataclass
class _SourceState:
    session_id: str
    video_path: str
    det_skip: int
    fps_target: float
    loop: bool
    video_id: str
    status: str = "running"
    frame_index: int = 0
    fps_actual: float = 0.0
    error: Optional[str] = None
    _thread: Optional[threading.Thread] = field(default=None, repr=False)
    _stop_event: threading.Event = field(default_factory=threading.Event, repr=False)


class VideoSourceService:
    """
    Manages background video-reading threads.
    Shares the same SessionStore and ZoneService singletons as TrackingService.
    """

    def __init__(self, session_store, zone_service=None) -> None:
        self._store = session_store
        self._zone_svc = zone_service
        self._sources: Dict[str, _SourceState] = {}
        self._lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, session_id: str, req: VideoSourceRequest) -> VideoSourceStatus:
        session = self._store.get(session_id)
        if session is None:
            raise KeyError(f"Session '{session_id}' not found.")

        with self._lock:
            existing = self._sources.get(session_id)
            if existing and existing.status == "running":
                raise ValueError(f"Session '{session_id}' already has a running video source.")

        video_path = str(_resolve_video_path(req.video_path))
        video_id   = req.video_id or Path(req.video_path).stem

        state = _SourceState(
            session_id=session_id,
            video_path=video_path,
            det_skip=req.det_skip,
            fps_target=req.fps_target,
            loop=req.loop,
            video_id=video_id,
        )

        thread = threading.Thread(
            target=self._run_loop,
            args=(state, session),
            daemon=True,
            name=f"vsrc-{session_id[:8]}",
        )
        state._thread = thread

        with self._lock:
            self._sources[session_id] = state

        thread.start()
        return self._to_status(state)

    def stop(self, session_id: str) -> VideoSourceStatus:
        with self._lock:
            state = self._sources.get(session_id)
        if state is None:
            raise KeyError(f"No video source for session '{session_id}'.")
        state._stop_event.set()
        if state._thread:
            state._thread.join(timeout=3.0)
        state.status = "stopped"
        return self._to_status(state)

    def get_status(self, session_id: str) -> Optional[VideoSourceStatus]:
        with self._lock:
            state = self._sources.get(session_id)
        return self._to_status(state) if state else None

    # ── Background loop ───────────────────────────────────────────────────────

    def _run_loop(self, state: _SourceState, session) -> None:
        cap = cv2.VideoCapture(state.video_path)
        if not cap.isOpened():
            state.status = "error"
            state.error  = f"Cannot open video: {state.video_path}"
            logger.error("VideoSourceService: %s", state.error)
            return

        frame_duration = 1.0 / state.fps_target
        cfg = session.config

        # Cache last ByteTrack output so skip-frames reuse last known positions
        # rather than passing empty detections (which would move tracks to "lost").
        last_tracks = np.empty((0, 8), dtype=np.float32)

        try:
            while not state._stop_event.is_set():
                t0 = time.perf_counter()

                ret, frame = cap.read()
                if not ret:
                    if state.loop:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        state.status = "finished"
                        break

                h, w = frame.shape[:2]

                if state.frame_index % state.det_skip == 0:
                    results = session.detector.predict(
                        source=frame,
                        conf=cfg.conf_threshold,
                        iou=cfg.nms_iou_threshold,
                        imgsz=cfg.imgsz,
                        device=cfg.device,
                        classes=cfg.target_classes,
                        verbose=False,
                    )
                    dets = yolo_to_boxmot(results, cfg.target_classes)
                    last_tracks = session.tracker.update(dets, frame)

                tracks = last_tracks

                zones: list = []
                if self._zone_svc is not None:
                    zones = self._zone_svc.get_zones_for_frame(state.video_id, w, h)

                zone_map = compute_zone_membership(tracks, zones)

                annotated = frame.copy()
                if zones:
                    draw_zones(annotated, zones)
                annotated = draw_tracks(annotated, tracks, zone_map=zone_map)

                self._store.set_annotated_frame(session.session_id, encode_jpeg(annotated))
                self._store.set_track_count(session.session_id, len(tracks) if tracks is not None else 0)

                occupancy: Dict[str, List[int]] = defaultdict(list)
                for tid, zname in zone_map.items():
                    occupancy[zname].append(tid)
                self._store.set_zone_occupancy(session.session_id, dict(occupancy))
                self._store.increment_frame(session.session_id)

                state.frame_index += 1

                elapsed = time.perf_counter() - t0
                state.fps_actual = round(1.0 / elapsed, 1) if elapsed > 0 else 0.0
                sleep_time = frame_duration - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as exc:
            state.status = "error"
            state.error  = str(exc)
            logger.exception("VideoSourceService error in session %s", state.session_id[:8])
        finally:
            cap.release()
            if state.status == "running":
                state.status = "stopped"

    # ── Helper ────────────────────────────────────────────────────────────────

    @staticmethod
    def _to_status(state: _SourceState) -> VideoSourceStatus:
        return VideoSourceStatus(
            session_id=state.session_id,
            status=state.status,
            video_path=state.video_path,
            frame_index=state.frame_index,
            fps_actual=state.fps_actual,
            det_skip=state.det_skip,
            loop=state.loop,
            error=state.error,
        )
