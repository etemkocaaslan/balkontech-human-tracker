"""
ZoneStore — per-video zone persistence.

Each video gets its own JSON file under ZONES_DIR:
    zones/
        audi_b9.json
        assembly_line_1.json

File format:
{
  "video_id": "audi_b9",
  "reference_resolution": {"width": 1920, "height": 1080},
  "zones": [ { ...ZoneInfo... } ]
}
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def _zones_dir() -> Path:
    return Path(os.getenv("ZONES_DIR", "./zones"))


def _safe_video_id(video_id: str) -> str:
    """Sanitize video_id to a safe filename stem."""
    return re.sub(r"[^\w\-]", "_", video_id).strip("_") or "default"


def _file_path(video_id: str) -> Path:
    return _zones_dir() / f"{_safe_video_id(video_id)}.json"


class ZoneStore:
    """
    File-backed zone registry, one JSON file per video.
    All reads/writes go through this class — no caller touches the filesystem directly.
    """

    def __init__(self) -> None:
        _zones_dir().mkdir(parents=True, exist_ok=True)

    # ── Read ──────────────────────────────────────────────────────────────────

    def load(self, video_id: str) -> dict:
        """Return the full parsed JSON for a video, or an empty structure."""
        path = _file_path(video_id)
        if not path.exists():
            return {"video_id": video_id, "zones": []}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def list_zones(self, video_id: str) -> List[dict]:
        return self.load(video_id).get("zones", [])

    def get_zone(self, video_id: str, zone_id: str) -> Optional[dict]:
        return next(
            (z for z in self.list_zones(video_id) if z["id"] == zone_id),
            None,
        )

    def list_video_ids(self) -> List[str]:
        """Return all video IDs that have zone files."""
        return [p.stem for p in _zones_dir().glob("*.json")]

    # ── Write ─────────────────────────────────────────────────────────────────

    def save_zone(self, video_id: str, zone: dict) -> dict:
        """Insert or replace a zone. Returns the saved zone."""
        data = self.load(video_id)
        zones = data.get("zones", [])
        zones = [z for z in zones if z["id"] != zone["id"]]
        zones.append(zone)
        data["zones"] = zones
        self._write(video_id, data)
        return zone

    def delete_zone(self, video_id: str, zone_id: str) -> bool:
        """Remove a zone by ID. Returns True if it existed."""
        data = self.load(video_id)
        original = data.get("zones", [])
        filtered = [z for z in original if z["id"] != zone_id]
        if len(filtered) == len(original):
            return False
        data["zones"] = filtered
        self._write(video_id, data)
        return True

    def delete_all_zones(self, video_id: str) -> int:
        """Remove all zones for a video. Returns count removed."""
        data = self.load(video_id)
        count = len(data.get("zones", []))
        data["zones"] = []
        self._write(video_id, data)
        return count

    # ── Internal ──────────────────────────────────────────────────────────────

    def _write(self, video_id: str, data: dict) -> None:
        data["video_id"] = video_id
        path = _file_path(video_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
