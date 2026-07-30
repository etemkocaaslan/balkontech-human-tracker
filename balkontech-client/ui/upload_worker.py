"""
UploadWorker — QThread that uploads a video file to the server in the background.

Signals:
    upload_started()          — emitted when upload begins
    upload_progress(int)      — upload percentage 0-100
    upload_finished(str, str) — (server_video_path, video_id) on success
    upload_error(str)         — error message on failure
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from api.client import BHTClient


class UploadWorker(QThread):
    upload_started   = pyqtSignal()
    upload_progress  = pyqtSignal(int)
    upload_finished  = pyqtSignal(str, str)   # (video_path, video_id)
    upload_error     = pyqtSignal(str)

    def __init__(
        self,
        client: BHTClient,
        file_path: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._client    = client
        self._file_path = file_path

    def run(self) -> None:
        self.upload_started.emit()
        try:
            result = self._client.upload_video(
                self._file_path,
                on_progress=lambda pct: self.upload_progress.emit(pct),
            )
            self.upload_finished.emit(result["video_path"], result["video_id"])
        except Exception as exc:
            self.upload_error.emit(str(exc))
