"""
BHTClient — HTTP client for the Balkontech Human Tracker API.

All public endpoints are under /api/v1/ and require an X-API-Key header.
Long-running calls (MJPEG stream) are handled via streaming responses
intended for use inside QThread workers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests


class BHTClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", api_key: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key  = api_key
        self._session = requests.Session()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v1{path}"

    def _get(self, path: str, **kwargs) -> Any:
        r = self._session.get(self._url(path), headers=self._headers(), timeout=10, **kwargs)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json: dict | None = None, **kwargs) -> Any:
        r = self._session.post(self._url(path), headers=self._headers(), json=json, timeout=30, **kwargs)
        r.raise_for_status()
        return r.json()

    def _patch(self, path: str, json: dict | None = None) -> Any:
        r = self._session.patch(self._url(path), headers=self._headers(), json=json, timeout=10)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str) -> int:
        r = self._session.delete(self._url(path), headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.status_code

    # ── Health ────────────────────────────────────────────────────────────────

    def health(self) -> Dict:
        r = self._session.get(f"{self.base_url}/health", timeout=5)
        r.raise_for_status()
        return r.json()

    def ping(self) -> bool:
        try:
            self.health()
            return True
        except Exception:
            return False

    # ── Models ────────────────────────────────────────────────────────────────

    def list_models(self) -> List[Dict]:
        return self._get("/models")

    def list_reid_catalog(self) -> List[Dict]:
        """Return the full ReID catalog with downloaded status from the server."""
        return self._get("/models/reid/catalog")

    # ── Sessions ──────────────────────────────────────────────────────────────

    def create_session(
        self,
        detector_model: str = "yolov8n.pt",
        tracker_type: str = "bytetrack",
        reid_model: Optional[str] = None,
        conf_threshold: float = 0.25,
        nms_iou_threshold: float = 0.45,
        target_classes: Optional[List[int]] = None,
        imgsz: int = 640,
        device: str = "cpu",
        video_id: Optional[str] = None,
        video_path: Optional[str] = None,
        det_skip: int = 2,
        fps_target: float = 25.0,
        loop: bool = False,
    ) -> Dict:
        payload: Dict = {
            "detector_model": detector_model,
            "tracker_type": tracker_type,
            "conf_threshold": conf_threshold,
            "nms_iou_threshold": nms_iou_threshold,
            "target_classes": target_classes or [0],
            "imgsz": imgsz,
            "device": device,
            "det_skip": det_skip,
            "fps_target": fps_target,
            "loop": loop,
        }
        if reid_model:
            payload["reid_model"] = reid_model
        if video_id:
            payload["video_id"] = video_id
        if video_path:
            payload["video_path"] = video_path
        return self._post("/sessions", json=payload)

    def list_sessions(self) -> List[Dict]:
        """Returns sessions as a list of SessionInfo dicts."""
        return self._get("/sessions")

    def get_stats(self, session_id: str) -> Dict:
        return self._get(f"/sessions/{session_id}/stats")

    def delete_session(self, session_id: str) -> int:
        return self._delete(f"/sessions/{session_id}")

    def set_display_options(self, session_id: str, *, show_id: bool) -> Dict:
        return self._patch(f"/sessions/{session_id}/display", json={"show_id": show_id})

    def track_frame(self, session_id: str, frame_b64: str, video_id: Optional[str] = None) -> Dict:
        payload: Dict = {"frame_b64": frame_b64}
        if video_id:
            payload["video_id"] = video_id
        return self._post(f"/sessions/{session_id}/track", json=payload)

    # ── Zones ─────────────────────────────────────────────────────────────────

    def list_video_ids(self) -> List[str]:
        return self._get("/zones")

    def list_zones(self, video_id: str) -> List[Dict]:
        return self._get(f"/zones/{video_id}")

    # ── Stream ────────────────────────────────────────────────────────────────

    def get_stream_bytes(self, session_id: str):
        """Return a streaming response for MJPEG — iterate over chunks in a QThread."""
        url = self._url(f"/sessions/{session_id}/stream")
        return self._session.get(url, headers=self._headers(), stream=True, timeout=None)
