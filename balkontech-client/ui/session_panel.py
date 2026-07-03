"""
SessionPanel — create and select tracking sessions.

Signals:
  session_selected(session_id: str)  — emitted when user picks a session
  session_deleted(session_id: str)   — emitted after deletion
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from api.client import BHTClient


class SessionPanel(QWidget):
    session_selected = pyqtSignal(str)
    session_deleted  = pyqtSignal(str)

    def __init__(self, client: BHTClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = client

        # ── Create session group ──────────────────────────────────────
        create_group = QGroupBox("New Session")
        create_layout = QFormLayout(create_group)
        create_layout.setSpacing(8)

        # Model selection: dropdown (from /models) + Browse button
        model_row = QHBoxLayout()
        self._model_combo = QComboBox()
        self._model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._model_combo.setEditable(True)
        self._model_combo.setPlaceholderText("yolov8n.pt or full path…")
        model_browse = QPushButton("…")
        model_browse.setFixedWidth(28)
        model_browse.setToolTip("Browse for a .pt model file")
        model_browse.clicked.connect(self._browse_model)
        model_row.addWidget(self._model_combo)
        model_row.addWidget(model_browse)

        # Video path: text field + Browse button
        video_row = QHBoxLayout()
        self._video_edit = QLineEdit()
        self._video_edit.setPlaceholderText("path/to/video.mp4")
        self._video_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        video_browse = QPushButton("…")
        video_browse.setFixedWidth(28)
        video_browse.setToolTip("Browse for a video file")
        video_browse.clicked.connect(self._browse_video)
        video_row.addWidget(self._video_edit)
        video_row.addWidget(video_browse)

        # Video ID (auto-derived from filename, editable)
        self._video_id_edit = QLineEdit()
        self._video_id_edit.setPlaceholderText("auto from filename")
        self._video_edit.textChanged.connect(self._auto_fill_video_id)

        # Confidence threshold
        self._conf_spin = QDoubleSpinBox()
        self._conf_spin.setRange(0.05, 1.0)
        self._conf_spin.setSingleStep(0.05)
        self._conf_spin.setValue(0.35)
        self._conf_spin.setDecimals(2)

        # Det-skip: run YOLO every N frames
        self._det_skip_spin = QSpinBox()
        self._det_skip_spin.setRange(1, 10)
        self._det_skip_spin.setValue(2)
        self._det_skip_spin.setToolTip("Run YOLO every N frames — ByteTrack predicts in between (higher = faster)")

        # Loop video
        self._loop_check = QCheckBox("Loop video")
        self._loop_check.setChecked(False)

        self._create_btn = QPushButton("➕  Create Session")
        self._create_btn.setFixedHeight(32)
        self._create_btn.clicked.connect(self._create_session)

        create_layout.addRow("Detector model:", model_row)
        create_layout.addRow("Video file:", video_row)
        create_layout.addRow("Video ID:", self._video_id_edit)
        create_layout.addRow("Confidence:", self._conf_spin)
        create_layout.addRow("Det-skip:", self._det_skip_spin)
        create_layout.addRow("", self._loop_check)
        create_layout.addRow(self._create_btn)

        # ── Active sessions group ─────────────────────────────────────
        active_group = QGroupBox("Active Sessions")
        active_layout = QVBoxLayout(active_group)
        active_layout.setSpacing(6)

        self._session_combo = QComboBox()
        self._session_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._session_combo.currentIndexChanged.connect(self._on_session_changed)

        btn_row = QHBoxLayout()
        self._refresh_btn = QPushButton("🔄  Refresh")
        self._refresh_btn.clicked.connect(self.refresh)
        self._delete_btn = QPushButton("🗑  Delete")
        self._delete_btn.clicked.connect(self._delete_session)
        btn_row.addWidget(self._refresh_btn)
        btn_row.addWidget(self._delete_btn)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #888; font-size: 11px;")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        active_layout.addWidget(self._session_combo)
        active_layout.addLayout(btn_row)
        active_layout.addWidget(self._status_label)

        # ── Root layout ───────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addWidget(create_group)
        root.addWidget(active_group)
        root.addStretch()

        self.refresh()

    # ── Public ────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload models from server and refresh session list."""
        self._load_models()
        self._load_sessions()

    def current_session_id(self) -> str | None:
        data = self._session_combo.currentData()
        return data if isinstance(data, str) else None

    # ── File browse dialogs ───────────────────────────────────────────

    def _browse_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select detector model",
            "",
            "PyTorch models (*.pt);;All files (*)",
        )
        if path:
            self._model_combo.setCurrentText(path)

    def _browse_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select video file",
            "",
            "Video files (*.mp4 *.avi *.mov *.mkv *.wmv);;All files (*)",
        )
        if path:
            self._video_edit.setText(path)

    def _auto_fill_video_id(self, path: str) -> None:
        """Auto-fill Video ID from the video filename (stem only)."""
        if not self._video_id_edit.text():
            stem = Path(path).stem if path else ""
            if stem:
                self._video_id_edit.setText(stem)

    # ── Private ───────────────────────────────────────────────────────

    def _load_models(self) -> None:
        try:
            models = self._client.list_models()
            current = self._model_combo.currentText()
            self._model_combo.clear()
            for m in models:
                # Show name, store full path as data
                self._model_combo.addItem(m["name"], m.get("path", m["name"]))
            # Restore typed text / previous selection
            if current:
                idx = self._model_combo.findText(current)
                if idx >= 0:
                    self._model_combo.setCurrentIndex(idx)
                else:
                    self._model_combo.setCurrentText(current)
            if self._model_combo.count() == 0:
                self._set_status("No models found in models/ dir")
        except Exception as exc:
            self._set_status(f"⚠ {exc}", error=True)

    def _load_sessions(self) -> None:
        try:
            sessions = self._client.list_sessions()
            current_id = self.current_session_id()

            self._session_combo.blockSignals(True)
            self._session_combo.clear()
            for s in sessions:
                label = f"{s['session_id'][:8]}…  [{s.get('detector_model','?')}]"
                self._session_combo.addItem(label, s["session_id"])

            if current_id:
                for i in range(self._session_combo.count()):
                    if self._session_combo.itemData(i) == current_id:
                        self._session_combo.setCurrentIndex(i)
                        break

            self._session_combo.blockSignals(False)
            self._on_session_changed()

            count = self._session_combo.count()
            self._set_status(f"{count} session(s) active")
        except Exception as exc:
            self._set_status(f"⚠ {exc}", error=True)

    def _create_session(self) -> None:
        # Model: prefer stored full path (from combo data), fall back to typed text
        idx = self._model_combo.currentIndex()
        if idx >= 0 and self._model_combo.itemData(idx):
            model = self._model_combo.itemData(idx)
        else:
            model = self._model_combo.currentText().strip()

        if not model:
            QMessageBox.warning(self, "No model", "Select or type a detector model path.")
            return

        video_path = self._video_edit.text().strip() or None
        video_id   = self._video_id_edit.text().strip() or None
        conf       = self._conf_spin.value()
        det_skip   = self._det_skip_spin.value()
        loop       = self._loop_check.isChecked()

        try:
            resp = self._client.create_session(
                detector_model=model,
                conf_threshold=conf,
                video_id=video_id,
                video_path=video_path,
                det_skip=det_skip,
                loop=loop,
            )
            self._set_status(f"✓ Created {resp['session_id'][:8]}…")
            self.refresh()
            new_id = resp["session_id"]
            for i in range(self._session_combo.count()):
                if self._session_combo.itemData(i) == new_id:
                    self._session_combo.setCurrentIndex(i)
                    break
        except Exception as exc:
            QMessageBox.critical(self, "Create failed", str(exc))

    def _delete_session(self) -> None:
        sid = self.current_session_id()
        if not sid:
            return
        reply = QMessageBox.question(
            self, "Delete session",
            f"Delete session {sid[:8]}…?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self._client.delete_session(sid)
            self.session_deleted.emit(sid)
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Delete failed", str(exc))

    def _on_session_changed(self) -> None:
        sid = self.current_session_id()
        if sid:
            self.session_selected.emit(sid)

    def _set_status(self, msg: str, *, error: bool = False) -> None:
        self._status_label.setText(msg)
        color = "#c0392b" if error else "#888"
        self._status_label.setStyleSheet(f"color: {color}; font-size: 11px;")
