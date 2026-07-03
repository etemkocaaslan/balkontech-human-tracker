"""
StatsWorker — polls /sessions/{id}/stats every second and emits results.
"""

from __future__ import annotations

import time

from PyQt6.QtCore import QThread, pyqtSignal

from api.client import BHTClient


class StatsWorker(QThread):
    stats_ready = pyqtSignal(dict)   # {track_count, frame_index, zone_occupancy}
    poll_error  = pyqtSignal(str)

    def __init__(self, client: BHTClient, session_id: str, interval: float = 1.0) -> None:
        super().__init__()
        self._client     = client
        self._session_id = session_id
        self._interval   = interval
        self._running    = False

    def run(self) -> None:
        self._running = True
        while self._running:
            try:
                stats = self._client.get_stats(self._session_id)
                self.stats_ready.emit(stats)
            except Exception as exc:
                self.poll_error.emit(str(exc))
            time.sleep(self._interval)

    def stop(self) -> None:
        self._running = False
        self.quit()
        self.wait(2000)
