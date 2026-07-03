"""
Zone geometry — pure logic, no I/O.

normalize_points()   : pixel coords → [0.0, 1.0]
denormalize_points() : [0.0, 1.0]  → pixel coords for a given frame size
is_point_in_zone()   : centroid-in-polygon test via cv2.pointPolygonTest
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np


@dataclass(frozen=True)
class NormalizedPoint:
    x: float   # [0.0, 1.0]
    y: float   # [0.0, 1.0]


@dataclass(frozen=True)
class PixelPoint:
    x: float
    y: float


# ── Coordinate transforms ─────────────────────────────────────────────────────

def normalize_points(
    pixel_points: List[PixelPoint],
    width: int,
    height: int,
) -> List[NormalizedPoint]:
    """Convert pixel coordinates to normalized [0.0, 1.0] space."""
    return [
        NormalizedPoint(x=p.x / width, y=p.y / height)
        for p in pixel_points
    ]


def denormalize_points(
    norm_points: List[NormalizedPoint],
    width: int,
    height: int,
) -> List[PixelPoint]:
    """Convert normalized points back to pixel coordinates for a given frame size."""
    return [
        PixelPoint(x=p.x * width, y=p.y * height)
        for p in norm_points
    ]


def to_contour(pixel_points: List[PixelPoint]) -> np.ndarray:
    """Convert pixel point list to the contour format expected by cv2."""
    return np.array(
        [[int(p.x), int(p.y)] for p in pixel_points],
        dtype=np.int32,
    ).reshape((-1, 1, 2))


# ── Geometry ──────────────────────────────────────────────────────────────────

def is_point_in_zone(
    point: Tuple[float, float],
    pixel_points: List[PixelPoint],
) -> bool:
    """
    Test whether a (cx, cy) centroid falls inside the polygon defined by pixel_points.
    Returns True if inside or on the boundary.
    Uses cv2.pointPolygonTest (positive = inside, 0 = on edge, negative = outside).
    """
    contour = to_contour(pixel_points)
    result = cv2.pointPolygonTest(contour, (float(point[0]), float(point[1])), measureDist=False)
    return result >= 0


def centroid_of_bbox(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float]:
    """Return the centroid of a bounding box."""
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


# ── Zone membership ───────────────────────────────────────────────────────────

def compute_zone_membership(
    tracks: "np.ndarray | None",
    zones: list,
) -> dict[int, str]:
    """
    For each track, find which zone (if any) its centroid falls in.

    Parameters
    ----------
    tracks : BoxMOT output array (M, 8) — [x1, y1, x2, y2, track_id, conf, cls, det_idx]
             or None / empty.
    zones  : list of dicts with keys 'name' and 'pixel_points' (List[PixelPoint])
             as returned by ZoneService.get_zones_for_frame().

    Returns
    -------
    {track_id (int): zone_name (str)}  — only tracks that are inside a zone.
    """
    if tracks is None or len(tracks) == 0 or not zones:
        return {}

    membership: dict[int, str] = {}
    for t in tracks:
        x1, y1, x2, y2, track_id = float(t[0]), float(t[1]), float(t[2]), float(t[3]), int(t[4])
        cx, cy = centroid_of_bbox(x1, y1, x2, y2)
        for zone in zones:
            pts = zone.get("pixel_points", [])
            if len(pts) >= 3 and is_point_in_zone((cx, cy), pts):
                membership[track_id] = zone["name"]
                break  # first matching zone wins
    return membership
