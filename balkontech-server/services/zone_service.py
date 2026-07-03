"""
ZoneService — zone CRUD with coordinate normalization.

Responsibilities:
  - Accept pixel-space zone definitions from callers
  - Normalize to [0.0, 1.0] before persisting
  - Denormalize back to pixel space when requested for a specific resolution
  - Delegate all I/O to ZoneStore
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from core.zone import (
    NormalizedPoint,
    PixelPoint as GeomPixelPoint,
    normalize_points,
    denormalize_points,
)
from schemas.zones import (
    PixelPoint,
    ZoneCreateRequest,
    ZoneInfo,
    ZonePoint,
    ZoneUpdateRequest,
    Resolution,
)
from storage.zone_store import ZoneStore


class ZoneService:

    def __init__(self, store: ZoneStore) -> None:
        self._store = store

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(self, video_id: str, req: ZoneCreateRequest) -> ZoneInfo:
        """Normalize pixel points and persist the zone."""
        self._assert_name_unique(video_id, req.name)

        norm_points = normalize_points(
            [GeomPixelPoint(x=p.x, y=p.y) for p in req.pixel_points],
            req.reference_width,
            req.reference_height,
        )

        zone_dict = {
            "id": str(uuid.uuid4()),
            "name": req.name,
            "description": req.description,
            "points": [{"x": p.x, "y": p.y} for p in norm_points],
            "reference_resolution": {
                "width": req.reference_width,
                "height": req.reference_height,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True,
        }

        saved = self._store.save_zone(video_id, zone_dict)
        return self._to_schema(saved)

    def list_zones(self, video_id: str) -> List[ZoneInfo]:
        return [self._to_schema(z) for z in self._store.list_zones(video_id)]

    def get_zone(self, video_id: str, zone_id: str) -> Optional[ZoneInfo]:
        z = self._store.get_zone(video_id, zone_id)
        return self._to_schema(z) if z else None

    def update(self, video_id: str, zone_id: str, req: ZoneUpdateRequest) -> Optional[ZoneInfo]:
        """Partial update — only provided fields are changed."""
        existing = self._store.get_zone(video_id, zone_id)
        if existing is None:
            return None

        if req.name and req.name != existing["name"]:
            self._assert_name_unique(video_id, req.name, exclude_id=zone_id)
            existing["name"] = req.name

        if req.description is not None:
            existing["description"] = req.description

        if req.pixel_points is not None:
            norm_points = normalize_points(
                [GeomPixelPoint(x=p.x, y=p.y) for p in req.pixel_points],
                req.reference_width,
                req.reference_height,
            )
            existing["points"] = [{"x": p.x, "y": p.y} for p in norm_points]
            existing["reference_resolution"] = {
                "width": req.reference_width,
                "height": req.reference_height,
            }

        saved = self._store.save_zone(video_id, existing)
        return self._to_schema(saved)

    def delete_zone(self, video_id: str, zone_id: str) -> bool:
        return self._store.delete_zone(video_id, zone_id)

    def delete_all(self, video_id: str) -> int:
        return self._store.delete_all_zones(video_id)

    # ── Transform ─────────────────────────────────────────────────────────────

    def get_zones_for_frame(
        self, video_id: str, width: int, height: int
    ) -> List[dict]:
        """
        Return zones with points denormalized to the given frame resolution.
        Used by TrackingService to do pixel-space intersection tests.
        """
        result = []
        for z in self._store.list_zones(video_id):
            if not z.get("active", True):
                continue
            norm_pts = [NormalizedPoint(x=p["x"], y=p["y"]) for p in z["points"]]
            pixel_pts = denormalize_points(norm_pts, width, height)
            result.append({
                "id": z["id"],
                "name": z["name"],
                "pixel_points": pixel_pts,   # List[GeomPixelPoint]
            })
        return result

    def list_video_ids(self) -> List[str]:
        return self._store.list_video_ids()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _assert_name_unique(
        self, video_id: str, name: str, exclude_id: Optional[str] = None
    ) -> None:
        for z in self._store.list_zones(video_id):
            if z["name"] == name and z["id"] != exclude_id:
                raise ValueError(f"A zone named '{name}' already exists for '{video_id}'.")

    @staticmethod
    def _to_schema(z: dict) -> ZoneInfo:
        res = z.get("reference_resolution", {})
        return ZoneInfo(
            id=z["id"],
            name=z["name"],
            description=z.get("description"),
            points=[ZonePoint(x=p["x"], y=p["y"]) for p in z["points"]],
            reference_resolution=Resolution(
                width=res.get("width", 0),
                height=res.get("height", 0),
            ),
            created_at=z["created_at"],
            active=z.get("active", True),
        )
