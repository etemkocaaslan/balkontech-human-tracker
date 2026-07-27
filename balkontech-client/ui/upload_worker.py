"""
UploadWorker — QThread that handles Google Drive upload in the background.

Wraps the logic from google-drive/upload.py (ffmpeg conversion + resumable upload)
so that the Create Session flow can start an upload without blocking the UI.
Signals:
  upload_started()         — emitted when the upload begins
  upload_progress(int)     — emitted with percentage (0–100)
  upload_finished(str)     — emitted with the Drive file_id when upload completes
  upload_error(str)        — emitted with an error message on failure
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal


def _load_upload_module():
    """Dynamically load google-drive/upload.py as an importable module."""
    gd_dir = Path(__file__).resolve().parent.parent / "google-drive"
    upload_path = gd_dir / "upload.py"
    if not upload_path.exists():
        raise ImportError(f"Cannot load upload module from {upload_path}")
    sys.path.insert(0, str(gd_dir))
    try:
        spec = importlib.util.spec_from_file_location("drive_upload", str(upload_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load upload module from {upload_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(gd_dir))


class UploadWorker(QThread):
    upload_started = pyqtSignal()
    upload_progress = pyqtSignal(int)
    upload_finished = pyqtSignal(str)
    upload_error = pyqtSignal(str)

    def __init__(self, video_path: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._video_path = video_path
        self._cancelled = False

    def run(self) -> None:
        try:
            drive_upload = _load_upload_module()
        except ImportError as exc:
            self.upload_error.emit(f"Google Drive module unavailable: {exc}")
            return

        self.upload_started.emit()

        # Step 1: Convert to MP4 if necessary
        video_path = self._video_path
        if not video_path.lower().endswith(".mp4"):
            self.upload_progress.emit(0)
            converted = drive_upload.convert_to_mp4(video_path)
            if self._cancelled:
                return
            if converted is None:
                self.upload_error.emit("FFmpeg conversion failed.")
                return
            video_path = converted

        # Step 2: Upload to Google Drive
        self.upload_progress.emit(10)
        file_name = Path(video_path).name

        def _on_progress(pct: int) -> None:
            self.upload_progress.emit(pct)

        file_id = drive_upload.upload_video_resumable(
            video_path,
            file_name=file_name,
            on_progress=_on_progress,
        )

        if self._cancelled:
            return

        if file_id is None:
            self.upload_error.emit("Upload to Google Drive failed.")
            return

        self.upload_progress.emit(100)
        self.upload_finished.emit(file_id)

    def cancel(self) -> None:
        self._cancelled = True
        self.quit()
        self.wait(2000)