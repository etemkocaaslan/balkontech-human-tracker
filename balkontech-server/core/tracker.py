"""
Core tracking logic — adapted from boxmot_cyolo.py (original file untouched).

Responsibilities:
  - build_bytetrack()  : create a ByteTrack instance with custom params
  - yolo_to_boxmot()   : convert Ultralytics YOLO output → BoxMOT (N,6) array
  - load_detector()    : load a YOLO model from path

Note: patch_bytetrack() from boxmot_cyolo.py is intentionally omitted here —
the service creates fresh tracker instances per session instead of mutating live ones.
"""

from pathlib import Path
from typing import List, Optional

import numpy as np
from ultralytics import YOLO
from boxmot.trackers import ByteTrack


def build_bytetrack(
    track_buffer: int = 60,
    frame_rate: int = 30,
    max_age: int = 1000,
    track_thresh: float = 0.45,
    min_conf: float = 0.1,
    match_thresh: float = 0.85,
    min_hits: int = 1,
    iou_threshold: float = 0.3,
    per_class: bool = False,
) -> ByteTrack:
    """
    Create a ByteTrack instance. Device is not passed — ByteTrack is CPU-only
    for motion calculations; the YOLO detector handles device selection separately.
    """
    return ByteTrack(
        min_conf=min_conf,
        track_thresh=track_thresh,
        match_thresh=match_thresh,
        track_buffer=track_buffer,
        frame_rate=frame_rate,
        det_thresh=track_thresh,
        max_age=max_age,
        min_hits=min_hits,
        iou_threshold=iou_threshold,
        per_class=per_class,
    )


def yolo_to_boxmot(results, target_classes: Optional[List[int]] = None) -> np.ndarray:
    """
    Ultralytics YOLO results → BoxMOT input format.
    Output shape: (N, 6) — [x1, y1, x2, y2, confidence, class_id]
    """
    detections = []

    for result in results:
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            continue

        xyxy   = boxes.xyxy.cpu().numpy()
        confs  = boxes.conf.cpu().numpy()
        clsids = boxes.cls.cpu().numpy()

        for i in range(len(xyxy)):
            cls_id = int(clsids[i])
            if target_classes is not None and cls_id not in target_classes:
                continue
            x1, y1, x2, y2 = xyxy[i]
            detections.append([x1, y1, x2, y2, float(confs[i]), cls_id])

    if not detections:
        return np.empty((0, 6), dtype=np.float32)

    return np.array(detections, dtype=np.float32)


def load_detector(model_path: Path) -> YOLO:
    return YOLO(str(model_path))
