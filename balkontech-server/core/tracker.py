"""
Core tracking utilities.

  build_tracker()   : factory — create any BoxMOT tracker by name
  yolo_to_boxmot()  : convert Ultralytics YOLO output → BoxMOT (N,6) array
  load_detector()   : load a YOLO model from path

Supported tracker types
-----------------------
Motion-only (no ReID model required):
  bytetrack, ocsort

Appearance-based (reid_weights required):
  boosttrack, botsort, strongsort, deepocsort, hybridsort
"""

from pathlib import Path
from typing import Any, List, Optional

import numpy as np
from ultralytics import YOLO

# ── Tracker registry ──────────────────────────────────────────────────────────
_TRACKER_CLASS_MAP: dict[str, str] = {
    "bytetrack":  "ByteTrack",
    "ocsort":     "OcSort",
    "boosttrack": "BoostTrack",
    "botsort":    "BotSort",
    "strongsort": "StrongSort",
    "deepocsort": "DeepOcSort",
    "hybridsort": "HybridSort",
}

# Trackers that run on motion only — no ReID model needed
_MOTION_ONLY: set[str] = {"bytetrack", "ocsort"}

# Public list for validation and UI dropdowns
SUPPORTED_TRACKERS: List[str] = sorted(_TRACKER_CLASS_MAP.keys())


# ── Factory ───────────────────────────────────────────────────────────────────

def build_tracker(
    tracker_type: str,
    device: str = "cpu",
    reid_weights: Optional[Path] = None,
    per_class: bool = False,
) -> Any:
    """
    Create any BoxMOT tracker by name.

    Parameters
    ----------
    tracker_type : str
        One of SUPPORTED_TRACKERS (case-insensitive).
    device : str
        Torch device string — "cpu", "cuda:0", etc.
        Ignored for motion-only trackers (ByteTrack, OcSort).
    reid_weights : Path, optional
        Path to a ReID model .pt file.
        Required for appearance-based trackers; ignored for motion-only ones.
    per_class : bool
        Track each class independently.
    """
    key = tracker_type.lower()

    if key not in _TRACKER_CLASS_MAP:
        raise ValueError(
            f"Unknown tracker '{tracker_type}'. "
            f"Supported: {SUPPORTED_TRACKERS}"
        )

    if key not in _MOTION_ONLY and reid_weights is None:
        raise ValueError(
            f"Tracker '{tracker_type}' requires a ReID model. "
            "Pass reid_weights or set reid_model in the session request."
        )

    try:
        import importlib
        module = importlib.import_module("boxmot.trackers")
        cls = getattr(module, _TRACKER_CLASS_MAP[key])
    except (ImportError, AttributeError) as exc:
        raise RuntimeError(
            f"Could not import tracker '{tracker_type}' from boxmot: {exc}"
        ) from exc

    if key in _MOTION_ONLY:
        return cls(per_class=per_class)
    else:
        # BoxMOT trackers expect a pre-built ReID backend object, not a raw path.
        # Build it via boxmot.reid.core.ReID, then pass .model (the backend).
        try:
            from boxmot.reid.core.reid import ReID
            reid_obj = ReID(weights=reid_weights, device=device, half=False)
            reid_backend = reid_obj.model
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load ReID model '{reid_weights}': {exc}"
            ) from exc

        return cls(reid_model=reid_backend, per_class=per_class)


# ── Helpers ───────────────────────────────────────────────────────────────────

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
