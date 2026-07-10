"""
MainWindow — Balkontech Human Tracker desktop client.

Layout
------
┌─ toolbar ──────────────────────────────────────────────────────────┐
│ ┌─ left panel (290px) ──┐  ┌─ stream display ───────────────────┐ │
│ │  SessionPanel          │  │  MJPEG frame (aspect ratio kept)   │ │
│ │  ZonePanel             │  └────────────────────────────────────┘ │
│ └───────────────────────┘                                          │
└────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from api.client import BHTClient
from ui.session_panel import SessionPanel
from ui.settings_dialog import SettingsDialog, load_settings
from ui.stats_worker import StatsWorker
from ui.stream_worker import StreamWorker
from ui.zone_panel import ZonePanel


class _StreamDisplay(QLabel):
    """QLabel that scales the MJPEG pixmap while preserving aspect ratio."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(480, 270)
        self._raw: QPixmap | None = None
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        self.setText("No stream\n\nCreate or select a session,\nthen click  ▶  Connect")
        self.setStyleSheet("background: #1a1a1a; color: #555; font-size: 14px;")

    def set_frame(self, px: QPixmap) -> None:
        self._raw = px
        self.setText("")
        self.setStyleSheet("background: #000;")
        self._rescale()

    def clear_frame(self) -> None:
        self._raw = None
        self._show_placeholder()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        if self._raw:
            scaled = self._raw.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(scaled)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Balkontech Human Tracker")
        self.resize(1200, 720)

        self._stream_worker: StreamWorker | None = None
        self._stats_worker: StatsWorker | None = None
        self._current_session_id: str | None = None

        base_url, api_key = load_settings()
        self._client = BHTClient(base_url=base_url, api_key=api_key)

        self._build_toolbar()
        self._build_ui()
        self._build_status_bar()

        QTimer.singleShot(500, self._ping_server)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setFloatable(False)
        self.addToolBar(tb)

        title = QLabel("  🎯  Balkontech Human Tracker  ")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #3498db;")
        tb.addWidget(title)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        self._connect_btn = QPushButton("▶  Connect")
        self._connect_btn.setFixedHeight(30)
        self._connect_btn.setCheckable(True)
        self._connect_btn.clicked.connect(self._toggle_stream)
        tb.addWidget(self._connect_btn)

        settings_action = QAction("⚙  Settings", self)
        settings_action.triggered.connect(self._open_settings)
        tb.addAction(settings_action)

    def _build_ui(self) -> None:
        self._session_panel = SessionPanel(self._client)
        self._session_panel.session_selected.connect(self._on_session_selected)
        self._session_panel.session_deleted.connect(self._on_session_deleted)

        self._zone_panel = ZonePanel()

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(12)
        left_layout.addWidget(self._session_panel)
        left_layout.addWidget(self._zone_panel, stretch=1)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFixedWidth(320)
        left_scroll.setWidget(left_widget)

        self._stream_display = _StreamDisplay()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_scroll)
        splitter.addWidget(self._stream_display)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 900])

        self.setCentralWidget(splitter)

    def _build_status_bar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_label = QLabel("Not connected")
        sb.addWidget(self._status_label)

    # ── Server health ─────────────────────────────────────────────────────────

    def _ping_server(self) -> None:
        try:
            if self._client.ping():
                self._set_status("✓ Server reachable", ok=True)
            else:
                self._set_status("⚠ Server not responding", ok=False)
        except Exception as exc:
            self._set_status(f"⚠ {exc}", ok=False)

    # ── Session callbacks ─────────────────────────────────────────────────────

    def _on_session_selected(self, session_id: str) -> None:
        if session_id == self._current_session_id:
            return
        self._stop_workers()
        self._current_session_id = session_id
        self._zone_panel.clear()
        self._stream_display.clear_frame()
        self._connect_btn.setChecked(False)
        self._connect_btn.setText("▶  Connect")
        self._set_status(f"Session: {session_id[:8]}…  (press Connect to start stream)")

    def _on_session_deleted(self, _session_id: str) -> None:
        self._stop_workers()
        self._current_session_id = None
        self._zone_panel.clear()
        self._stream_display.clear_frame()
        self._connect_btn.setChecked(False)
        self._connect_btn.setText("▶  Connect")
        self._set_status("Session deleted")

    # ── Stream control ────────────────────────────────────────────────────────

    def _toggle_stream(self, checked: bool) -> None:
        if checked:
            self._start_workers()
        else:
            self._stop_workers()
            self._stream_display.clear_frame()
            self._zone_panel.clear()
            self._connect_btn.setText("▶  Connect")

    def _start_workers(self) -> None:
        sid = self._current_session_id
        if not sid:
            self._connect_btn.setChecked(False)
            QMessageBox.information(self, "No session", "Create or select a session first.")
            return

        self._connect_btn.setText("⏹  Disconnect")

        self._stream_worker = StreamWorker(self._client, sid)
        self._stream_worker.frame_ready.connect(self._on_frame)
        self._stream_worker.stream_error.connect(self._on_stream_error)
        self._stream_worker.stream_stopped.connect(self._on_stream_stopped)
        self._stream_worker.start()

        self._stats_worker = StatsWorker(self._client, sid, interval=1.0)
        self._stats_worker.stats_ready.connect(self._zone_panel.update_stats)
        self._stats_worker.poll_error.connect(lambda e: self._set_status(f"Stats error: {e}", ok=False))
        self._stats_worker.start()

        self._set_status(f"Streaming  {sid[:8]}…")

    def _stop_workers(self) -> None:
        if self._stream_worker:
            self._stream_worker.stop()
            self._stream_worker = None
        if self._stats_worker:
            self._stats_worker.stop()
            self._stats_worker = None

    # ── Worker callbacks ──────────────────────────────────────────────────────

    def _on_frame(self, px: QPixmap) -> None:
        self._stream_display.set_frame(px)

    def _on_stream_error(self, msg: str) -> None:
        self._set_status(f"Stream error: {msg}", ok=False)
        self._connect_btn.setChecked(False)
        self._connect_btn.setText("▶  Connect")

    def _on_stream_stopped(self) -> None:
        self._set_status("Stream stopped")
        self._connect_btn.setChecked(False)
        self._connect_btn.setText("▶  Connect")

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._stop_workers()
            self._stream_display.clear_frame()
            self._zone_panel.clear()
            base_url, api_key = load_settings()
            self._client = BHTClient(base_url=base_url, api_key=api_key)
            self._session_panel._client = self._client
            self._session_panel.refresh()
            self._current_session_id = None
            self._connect_btn.setChecked(False)
            self._connect_btn.setText("▶  Connect")
            QTimer.singleShot(200, self._ping_server)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, msg: str, *, ok: bool = True) -> None:
        color = "#27ae60" if ok else "#e74c3c"
        self._status_label.setText(msg)
        self._status_label.setStyleSheet(f"color: {color};")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._stop_workers()
        super().closeEvent(event)
