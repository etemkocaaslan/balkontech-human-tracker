"""
StreamWorker — QThread that reads MJPEG stream and emits QPixmap signals.
Runs entirely in background; the main thread only receives ready frames.
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

from api.client import BHTClient


class StreamWorker(QThread):
    frame_ready   = pyqtSignal(QPixmap)
    stream_error  = pyqtSignal(str)
    stream_stopped = pyqtSignal()

    def __init__(self, client: BHTClient, session_id: str) -> None:
        super().__init__()
        self._client     = client
        self._session_id = session_id
        self._running    = False

    def run(self) -> None:
        self._running = True
        try:
            response = self._client.get_stream_bytes(self._session_id)
            buffer   = b""
            for chunk in response.iter_content(chunk_size=4096):
                if not self._running:
                    break
                buffer += chunk
                # Extract complete JPEG frames from the MJPEG stream
                while True:
                    start = buffer.find(b"\xff\xd8")   # JPEG SOI
                    end   = buffer.find(b"\xff\xd9")   # JPEG EOI
                    if start == -1 or end == -1 or end < start:
                        break
                    jpeg = buffer[start:end + 2]
                    buffer = buffer[end + 2:]
                    image = QImage.fromData(jpeg, "JPEG")
                    if not image.isNull():
                        self.frame_ready.emit(QPixmap.fromImage(image))
        except Exception as exc:
            if self._running:
                self.stream_error.emit(str(exc))
        finally:
            self.stream_stopped.emit()

    def stop(self) -> None:
        self._running = False
        self.quit()
        self.wait(2000)
