"""
SnapshotService — extracts a single frame from a video file.

Path resolution order:
  1. As given (absolute or relative to CWD)
  2. Relative to the service's parent directory (where videos typically live)
  3. Raises FileNotFoundError if none found
"""

from __future__ import annotations

import base64
from pathlib import Path

import cv2

from schemas.zones import SnapshotResponse

_PARENT_DIR = Path(__file__).resolve().parents[2]


def _resolve_video_path(video_path: str) -> Path:
    candidates = [
        Path(video_path),
        Path.cwd() / video_path,
        _PARENT_DIR / video_path,
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()
    raise FileNotFoundError(
        f"Video not found: '{video_path}'\n"
        f"Searched in:\n" + "\n".join(f"  - {c}" for c in candidates)
    )


class SnapshotService:

    def extract(self, video_path: str, frame_index: int = 0) -> SnapshotResponse:
        path = _resolve_video_path(video_path)

        cap = cv2.VideoCapture(str(path))
        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if frame_index >= total_frames > 0:
                raise ValueError(
                    f"frame_index {frame_index} out of range "
                    f"(video has {total_frames} frames)."
                )
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = cap.read()
            if not ret or frame is None:
                raise ValueError(f"Could not read frame {frame_index}.")
        finally:
            cap.release()

        height, width = frame.shape[:2]
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        frame_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

        return SnapshotResponse(
            video_path=str(path),
            frame_index=frame_index,
            width=width,
            height=height,
            frame_b64=frame_b64,
        )
