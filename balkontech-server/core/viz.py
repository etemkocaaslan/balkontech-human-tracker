"""
Visualization utilities.

  draw_tracks()  : draws bounding box + label on a frame copy
  encode_jpeg()  : converts a numpy frame to JPEG bytes for MJPEG streaming
  draw_zones()   : draws semi-transparent zone polygons on a frame (in-place)
"""

import cv2
import numpy as np
from typing import Dict, Optional

# Zone palette — BGR
_ZONE_COLORS = [
    (235, 137,  59),  # orange
    ( 45, 158, 245),  # amber
    (180,  81, 228),  # pink/magenta
    ( 91, 179, 132),  # teal
    (180, 182,   6),  # lime
    (200,  80,  80),  # steel blue
]

# Zone name → color index (populated by draw_zones, used by draw_tracks)
_zone_color_index: Dict[str, int] = {}


def draw_zones(frame: np.ndarray, zones: list) -> np.ndarray:
    """
    Draw zone polygons on the frame (in-place).
    zones: list of dicts with keys 'name' and 'pixel_points' (List[PixelPoint])
    """
    global _zone_color_index
    _zone_color_index = {}

    overlay = frame.copy()

    for i, zone in enumerate(zones):
        color = _ZONE_COLORS[i % len(_ZONE_COLORS)]
        _zone_color_index[zone["name"]] = i
        pts = zone.get("pixel_points", [])
        if len(pts) < 3:
            continue

        contour = np.array(
            [[int(p.x), int(p.y)] for p in pts],
            dtype=np.int32,
        ).reshape((-1, 1, 2))

        cv2.fillPoly(overlay, [contour], color)
        cv2.polylines(frame, [contour], isClosed=True, color=color, thickness=2)

        # Zone label at centroid
        cx = int(sum(p.x for p in pts) / len(pts))
        cy = int(sum(p.y for p in pts) / len(pts))
        (tw, th), _ = cv2.getTextSize(zone["name"], cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        cv2.rectangle(frame, (cx - tw // 2 - 4, cy - th - 6), (cx + tw // 2 + 4, cy + 4), color, -1)
        cv2.putText(frame, zone["name"], (cx - tw // 2, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

    cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
    return frame


def draw_tracks(
    frame: np.ndarray,
    tracks: Optional[np.ndarray],
    zone_map: Optional[Dict[int, str]] = None,
    show_id: bool = True,
) -> np.ndarray:
    """
    BoxMOT track format: (M, 8) — [x1, y1, x2, y2, track_id, conf, class_id, det_idx]

    zone_map : {track_id: zone_name} — if provided, tracks inside a zone get:
               - the zone's color instead of the random track color
               - an extra zone badge below the main label
    """
    out = frame.copy()
    if zone_map is None:
        zone_map = {}

    if tracks is None or len(tracks) == 0:
        return out

    for track in tracks:
        x1, y1, x2, y2 = int(track[0]), int(track[1]), int(track[2]), int(track[3])
        track_id = int(track[4])
        conf     = float(track[5])
        class_id = int(track[6])

        zone_name = zone_map.get(track_id)

        if zone_name and zone_name in _zone_color_index:
            color = _ZONE_COLORS[_zone_color_index[zone_name] % len(_ZONE_COLORS)]
        else:
            # Deterministic color per track ID
            color = (
                (track_id * 37)  % 255,
                (track_id * 97)  % 255,
                (track_id * 157) % 255,
            )

        # Bounding box — thicker when inside a zone
        thickness = 3 if zone_name else 2
        cv2.rectangle(out, (x1, y1), (x2, y2), color, thickness)

        # Primary label: class name (+ ID if show_id is True)
        class_name = "Worker" if class_id == 0 else str(class_id)
        label = f"{class_name} #{track_id}  {conf:.2f}" if show_id else f"{class_name}  {conf:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 2)
        cv2.rectangle(out, (x1, y1 - th - 8), (x1 + tw + 6, y1), color, -1)
        cv2.putText(out, label, (x1 + 3, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)

        # Zone badge below the top label (when inside a zone)
        if zone_name:
            badge = f"@ {zone_name}"
            (bw, bh), _ = cv2.getTextSize(badge, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(out, (x1, y1), (x1 + bw + 6, y1 + bh + 6), color, -1)
            cv2.putText(out, badge, (x1 + 3, y1 + bh + 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    cv2.putText(out, f"Tracks: {len(tracks)}", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    return out


def encode_jpeg(frame: np.ndarray, quality: int = 80) -> bytes:
    """Encode a numpy BGR frame as JPEG bytes."""
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes()
