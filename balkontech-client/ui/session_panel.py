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
        form = QFormLayout(create_group)
        form.setSpacing(5)
        form.setContentsMargins(8, 10, 8, 8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # ── Video file ────────────────────────────────────────────────
        video_row = QHBoxLayout()
        video_row.setSpacing(4)
        self._video_edit = QLineEdit()
        self._video_edit.setPlaceholderText("select or type path…")
        video_browse = QPushButton("…")
        video_browse.setFixedWidth(26)
        video_browse.setToolTip("Browse for a video file")
        video_browse.clicked.connect(self._browse_video)
        video_row.addWidget(self._video_edit)
        video_row.addWidget(video_browse)
        self._video_edit.textChanged.connect(self._auto_fill_video_id)
        form.addRow("Video:", video_row)

        # ── Detector model ────────────────────────────────────────────
        model_row = QHBoxLayout()
        model_row.setSpacing(4)
        self._model_combo = QComboBox()
        self._model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._model_combo.setEditable(True)
        self._model_combo.setPlaceholderText("loading…")
        model_browse = QPushButton("…")
        model_browse.setFixedWidth(26)
        model_browse.setToolTip("Browse for a .pt model file")
        model_browse.clicked.connect(self._browse_model)
        model_row.addWidget(self._model_combo)
        model_row.addWidget(model_browse)
        form.addRow("Model:", model_row)

        # ── Tracker ───────────────────────────────────────────────────
        MOTION_ONLY = {"bytetrack", "ocsort"}
        self._motion_only: set[str] = MOTION_ONLY
        self._tracker_combo = QComboBox()
        for key, label in [
            ("bytetrack",  "ByteTrack  (fast, motion)"),
            ("ocsort",     "OcSort  (motion)"),
            ("boosttrack", "BoostTrack  (appearance)"),
            ("botsort",    "BotSort  (appearance)"),
            ("deepocsort", "DeepOcSort  (appearance)"),
            ("hybridsort", "HybridSort  (appearance)"),
            ("strongsort", "StrongSort  (appearance)"),
        ]:
            self._tracker_combo.addItem(label, key)
        self._tracker_combo.currentIndexChanged.connect(self._on_tracker_changed)
        form.addRow("Tracker:", self._tracker_combo)

        # ── ReID model (conditional) ──────────────────────────────────
        self._reid_label = QLabel("ReID:")
        self._reid_combo = QComboBox()
        self._reid_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._reid_label.setVisible(False)
        self._reid_combo.setVisible(False)
        form.addRow(self._reid_label, self._reid_combo)

        # ── Conf + Det-skip (one row) ─────────────────────────────────
        params_row = QHBoxLayout()
        params_row.setSpacing(6)

        self._conf_spin = QDoubleSpinBox()
        self._conf_spin.setRange(0.05, 1.0)
        self._conf_spin.setSingleStep(0.05)
        self._conf_spin.setValue(0.35)
        self._conf_spin.setDecimals(2)
        self._conf_spin.setFixedWidth(62)
        self._conf_spin.setToolTip("Confidence threshold")

        self._det_skip_spin = QSpinBox()
        self._det_skip_spin.setRange(1, 10)
        self._det_skip_spin.setValue(2)
        self._det_skip_spin.setFixedWidth(46)
        self._det_skip_spin.setToolTip("Run YOLO every N frames (higher = faster)")

        params_row.addWidget(QLabel("Conf"))
        params_row.addWidget(self._conf_spin)
        params_row.addSpacing(8)
        params_row.addWidget(QLabel("Skip"))
        params_row.addWidget(self._det_skip_spin)
        params_row.addStretch()
        form.addRow("", params_row)

        # ── Checkboxes row ────────────────────────────────────────────
        checks_row = QHBoxLayout()
        checks_row.setSpacing(12)
        self._loop_check = QCheckBox("Loop")
        self._loop_check.setChecked(False)
        self._show_id_check = QCheckBox("Show ID")
        self._show_id_check.setChecked(True)
        self._show_id_check.stateChanged.connect(self._on_show_id_changed)
        checks_row.addWidget(self._loop_check)
        checks_row.addWidget(self._show_id_check)
        checks_row.addStretch()
        form.addRow("", checks_row)

        # ── Advanced (collapsible: Video ID) ──────────────────────────
        self._adv_btn = QPushButton("▶  Advanced")
        self._adv_btn.setFlat(True)
        self._adv_btn.setStyleSheet("text-align:left; color:#888; font-size:11px; padding:0;")
        self._adv_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._adv_btn.clicked.connect(self._toggle_advanced)
        form.addRow(self._adv_btn)

        self._adv_widget = QWidget()
        adv_form = QFormLayout(self._adv_widget)
        adv_form.setSpacing(4)
        adv_form.setContentsMargins(0, 0, 0, 0)
        adv_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._video_id_edit = QLineEdit()
        self._video_id_edit.setPlaceholderText("auto from filename")
        adv_form.addRow("Video ID:", self._video_id_edit)
        self._adv_widget.setVisible(False)
        form.addRow(self._adv_widget)

        # ── Create button ─────────────────────────────────────────────
        self._create_btn = QPushButton("➕  Create Session")
        self._create_btn.setFixedHeight(30)
        self._create_btn.clicked.connect(self._create_session)
        form.addRow(self._create_btn)

        # ── Active sessions group ─────────────────────────────────────
        active_group = QGroupBox("Active Sessions")
        active_layout = QVBoxLayout(active_group)
        active_layout.setSpacing(5)
        active_layout.setContentsMargins(8, 8, 8, 8)

        self._session_combo = QComboBox()
        self._session_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._session_combo.currentIndexChanged.connect(self._on_session_changed)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        self._refresh_btn = QPushButton("↻ Refresh")
        self._refresh_btn.clicked.connect(self.refresh)
        self._delete_btn = QPushButton("🗑 Delete")
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
        root.setSpacing(8)
        root.addWidget(create_group)
        root.addWidget(active_group)
        root.addStretch()

        self.refresh()

    # ── Public ────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self._load_models()
        self._load_reid_catalog()
        self._load_sessions()

    def current_session_id(self) -> str | None:
        data = self._session_combo.currentData()
        return data if isinstance(data, str) else None

    # ── Advanced toggle ───────────────────────────────────────────────

    def _toggle_advanced(self) -> None:
        visible = self._adv_widget.isVisible()
        self._adv_widget.setVisible(not visible)
        self._adv_btn.setText(("▼" if not visible else "▶") + "  Advanced")

    # ── File browse dialogs ───────────────────────────────────────────

    def _browse_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select detector model", "",
            "PyTorch models (*.pt);;All files (*)",
        )
        if path:
            self._model_combo.setCurrentText(path)

    def _browse_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select video file", "",
            "Video files (*.mp4 *.avi *.mov *.mkv *.wmv);;All files (*)",
        )
        if path:
            self._video_edit.setText(path)

    def _auto_fill_video_id(self, path: str) -> None:
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
                if m.get("has_detector") or m.get("type") == "detector":
                    self._model_combo.addItem(m["name"], m.get("path", m["name"]))
            if current:
                idx = self._model_combo.findText(current)
                if idx >= 0:
                    self._model_combo.setCurrentIndex(idx)
                else:
                    self._model_combo.setCurrentText(current)
            if self._model_combo.count() == 0:
                self._set_status("No detector models found")
        except Exception as exc:
            self._set_status(f"⚠ {exc}", error=True)

    def _load_reid_catalog(self) -> None:
        tracker_key = self._tracker_combo.currentData() or "bytetrack"
        if tracker_key in self._motion_only:
            return

        try:
            catalog = self._client.list_reid_catalog()
        except Exception:
            try:
                models = self._client.list_models()
                catalog = [
                    {"name": m["name"], "size_mb": m.get("size_mb", 0),
                     "description": "", "downloaded": True,
                     "compatible_trackers": list({"botsort","boosttrack","strongsort","deepocsort","hybridsort"})}
                    for m in models if m.get("has_reid") or m.get("type") == "reid"
                ]
            except Exception as exc:
                self._set_status(f"⚠ {exc}", error=True)
                return

        self._reid_combo.clear()
        compatible = [m for m in catalog if tracker_key in m.get("compatible_trackers", [])]
        downloaded = [m for m in compatible if m.get("downloaded")]
        not_downloaded = [m for m in compatible if not m.get("downloaded")]

        for m in downloaded:
            size = m.get("size_mb", 0)
            self._reid_combo.addItem(f"✓ {m['name']}  ({size:.1f} MB)", m["name"])
        for m in not_downloaded:
            size = m.get("size_mb", 0)
            self._reid_combo.addItem(f"⬇ {m['name']}  ({size:.1f} MB)", m["name"])

        if self._reid_combo.count() == 0:
            self._reid_combo.addItem("— no compatible ReID models —", "")

    def _load_sessions(self) -> None:
        try:
            sessions = self._client.list_sessions()
            current_id = self.current_session_id()

            self._session_combo.blockSignals(True)
            self._session_combo.clear()
            for s in sessions:
                model   = s.get("detector_model", "?")
                tracker = s.get("tracker_type", "")
                label   = f"{s['session_id'][:8]}…  {model}  [{tracker}]"
                self._session_combo.addItem(label, s["session_id"])

            if current_id:
                for i in range(self._session_combo.count()):
                    if self._session_combo.itemData(i) == current_id:
                        self._session_combo.setCurrentIndex(i)
                        break

            self._session_combo.blockSignals(False)
            self._on_session_changed()
            self._set_status(f"{self._session_combo.count()} session(s)")
        except Exception as exc:
            self._set_status(f"⚠ {exc}", error=True)

    def _on_tracker_changed(self) -> None:
        tracker_key = self._tracker_combo.currentData()
        is_appearance = tracker_key not in self._motion_only
        self._reid_label.setVisible(is_appearance)
        self._reid_combo.setVisible(is_appearance)
        if is_appearance:
            self._load_reid_catalog()

    def _create_session(self) -> None:
        idx = self._model_combo.currentIndex()
        model = (self._model_combo.itemData(idx)
                 if idx >= 0 and self._model_combo.itemData(idx)
                 else self._model_combo.currentText().strip())
        if not model:
            QMessageBox.warning(self, "No model", "Select or type a detector model path.")
            return

        tracker_key = self._tracker_combo.currentData() or "bytetrack"
        reid_model: str | None = None
        if tracker_key not in self._motion_only:
            reid_model = self._reid_combo.currentData() or ""
            if not reid_model:
                QMessageBox.warning(
                    self, "ReID model required",
                    f'Tracker "{tracker_key}" requires a ReID model.\n'
                    "Download one from the server Models tab first.",
                )
                return

        try:
            resp = self._client.create_session(
                detector_model=model,
                tracker_type=tracker_key,
                reid_model=reid_model,
                conf_threshold=self._conf_spin.value(),
                video_id=self._video_id_edit.text().strip() or None,
                video_path=self._video_edit.text().strip() or None,
                det_skip=self._det_skip_spin.value(),
                loop=self._loop_check.isChecked(),
                device="0",
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

    def _on_show_id_changed(self) -> None:
        sid = self.current_session_id()
        if not sid:
            return
        try:
            self._client.set_display_options(sid, show_id=self._show_id_check.isChecked())
        except Exception:
            pass

    def _set_status(self, msg: str, *, error: bool = False) -> None:
        self._status_label.setText(msg)
        color = "#c0392b" if error else "#888"
        self._status_label.setStyleSheet(f"color: {color}; font-size: 11px;")
