"""
MainWindow — main window of the Balkontech Master Dashboard.

Provides three tabs:
  1. Control Center  – server/client execution state, status badge, session count.
  2. Model Hub       – list/table of models, add/delete, and active-session locking.
  3. Console         – plain text area displaying stdout/stderr logs from the ProcessManager.

Fully asynchronous API interaction via QThread to keep the UI responsive.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Set

from PyQt6.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.sip import isdeleted
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from dashboard.api.client import DashboardAPIClient
from dashboard.ui.process_manager import ProcessManager

# Resolve project paths
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MODELS_DIR = _REPO_ROOT / "balkontech-server" / "models"
_DETECTORS_DIR = _MODELS_DIR / "detectors"
_REID_DIR = _MODELS_DIR / "reid"


# ── Thread Workers ────────────────────────────────────────────────────────────

class HealthWorker(QThread):
    """Worker thread that continuously polls the server health endpoint."""

    health_updated = pyqtSignal(bool)

    def __init__(self, client: DashboardAPIClient, interval_ms: int = 2500, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._client = client
        self._interval_ms = interval_ms
        self._running = True

    def run(self) -> None:
        while self._running:
            is_ok = self._client.check_health()
            self.health_updated.emit(is_ok)
            self.msleep(self._interval_ms)

    def stop(self) -> None:
        self._running = False
        self.quit()
        self.wait()


class ModelRefreshWorker(QThread):
    """Worker thread that fetches models and active sessions from the API."""

    # Emitted on success with: (models, active_detector_models, session_count)
    refresh_done = pyqtSignal(list, set, int)
    # Emitted on error with message
    refresh_error = pyqtSignal(str)

    def __init__(self, client: DashboardAPIClient, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._client = client

    def run(self) -> None:
        try:
            # 1. Fetch available models
            models = self._client.get_models()

            # 2. Fetch active sessions
            session_ids = self._client.get_sessions()

            # 3. Query details for each session to find the active models
            active_detector_models: Set[str] = set()
            for sid in session_ids:
                try:
                    detail = self._client.get_session_detail(sid)
                    det_model = detail.get("detector_model")
                    if det_model:
                        active_detector_models.add(det_model)
                except Exception:
                    # If a session closed or details query failed, ignore it
                    pass

            self.refresh_done.emit(models, active_detector_models, len(session_ids))
        except Exception as exc:
            self.refresh_error.emit(str(exc))


# ── MainWindow Class ──────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Balkontech Master Launcher & Dashboard")
        self.resize(900, 600)

        # Isolated API client and process manager
        self._api_client = DashboardAPIClient()
        self._proc_mgr = ProcessManager(self)

        # Track UI state
        self._server_online = False
        self._active_detector_models: Set[str] = set()

        self._build_ui()
        self._connect_signals()

        # Start health worker
        self._health_worker = HealthWorker(self._api_client, parent=self)
        self._health_worker.health_updated.connect(self._on_health_updated)
        self._health_worker.start()

        # Initial refresh of model list
        QTimer.singleShot(1000, self.refresh_models)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._tabs = QTabWidget()

        # Tabs
        self._tabs.addTab(self._build_control_tab(), "🎛 Control Center")
        self._tabs.addTab(self._build_model_tab(), "🔒 Model Hub")
        self._tabs.addTab(self._build_console_tab(), "💻 Console")

        self.setCentralWidget(self._tabs)

        # Status Bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_label = QLabel("Initializing Master Dashboard...")
        self._status_bar.addWidget(self._status_label)

    def _build_control_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Server Status Panel
        status_layout = QHBoxLayout()
        status_title = QLabel("Server Reachability:")
        status_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self._status_badge = QLabel("🔴 Offline")
        self._status_badge.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self._status_badge.setStyleSheet("color: #ff4d4d;")
        status_layout.addWidget(status_title)
        status_layout.addWidget(self._status_badge)
        status_layout.addStretch()

        self._session_count_label = QLabel("Active Sessions: —")
        self._session_count_label.setFont(QFont("Arial", 11))
        status_layout.addWidget(self._session_count_label)
        layout.addLayout(status_layout)

        # Separator line
        sep = QWidget()
        sep.setFixedHeight(2)
        sep.setStyleSheet("background-color: #444;")
        layout.addWidget(sep)

        # Controls Layout
        controls_layout = QHBoxLayout()

        # Server Subprocess Controls
        server_box = QVBoxLayout()
        server_label = QLabel("Orchestrate Server")
        server_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        server_box.addWidget(server_label)

        self._start_server_btn = QPushButton("Start Server")
        self._start_server_btn.setFixedHeight(40)
        self._start_server_btn.clicked.connect(self._proc_mgr.start_server)
        server_box.addWidget(self._start_server_btn)

        self._stop_server_btn = QPushButton("Stop Server")
        self._stop_server_btn.setFixedHeight(40)
        self._stop_server_btn.setEnabled(False)
        self._stop_server_btn.clicked.connect(self._proc_mgr.stop_server)
        server_box.addWidget(self._stop_server_btn)
        server_box.addStretch()

        controls_layout.addLayout(server_box, stretch=1)

        # Client Subprocess Controls
        client_box = QVBoxLayout()
        client_label = QLabel("Orchestrate Client")
        client_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        client_box.addWidget(client_label)

        self._start_client_btn = QPushButton("Launch Client")
        self._start_client_btn.setFixedHeight(40)
        self._start_client_btn.clicked.connect(self._proc_mgr.start_client)
        client_box.addWidget(self._start_client_btn)

        self._stop_client_btn = QPushButton("Stop Client")
        self._stop_client_btn.setFixedHeight(40)
        self._stop_client_btn.setEnabled(False)
        self._stop_client_btn.clicked.connect(self._proc_mgr.stop_client)
        client_box.addWidget(self._stop_client_btn)
        client_box.addStretch()

        controls_layout.addLayout(client_box, stretch=1)

        layout.addLayout(controls_layout)
        layout.addStretch()
        return widget

    def _build_model_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Model Table
        self._model_table = QTableWidget(0, 4)
        self._model_table.setHorizontalHeaderLabels(["Model Filename", "Type", "Size (MB)", "Status"])
        self._model_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._model_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._model_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._model_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._model_table.setAlternatingRowColors(True)
        self._model_table.itemSelectionChanged.connect(self._on_table_selection_changed)
        layout.addWidget(self._model_table)

        # Actions Layout
        actions_layout = QHBoxLayout()

        self._add_model_btn = QPushButton("Add Model (.pt)")
        self._add_model_btn.clicked.connect(self._on_add_model_clicked)
        actions_layout.addWidget(self._add_model_btn)

        self._delete_model_btn = QPushButton("Delete Model")
        self._delete_model_btn.setEnabled(False)
        self._delete_model_btn.setStyleSheet("QPushButton:disabled { color: #555; }")
        self._delete_model_btn.clicked.connect(self._on_delete_model_clicked)
        actions_layout.addWidget(self._delete_model_btn)

        self._refresh_models_btn = QPushButton("Refresh List")
        self._refresh_models_btn.clicked.connect(self.refresh_models)
        actions_layout.addWidget(self._refresh_models_btn)

        layout.addLayout(actions_layout)
        return widget

    def _build_console_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        self._console_text = QPlainTextEdit()
        self._console_text.setReadOnly(True)
        self._console_text.setMaximumBlockCount(1000)
        font = QFont("Courier New", 10)
        self._console_text.setFont(font)
        self._console_text.setStyleSheet("background-color: #111; color: #00ff00;")
        layout.addWidget(self._console_text)

        clear_btn = QPushButton("Clear Console")
        clear_btn.clicked.connect(self._console_text.clear)
        layout.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignRight)
        return widget

    # ── Signal Connections ────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._proc_mgr.log_received.connect(self._on_log_received)
        self._proc_mgr.state_changed.connect(self._on_proc_state_changed)

    # ── Subprocess Event Handlers ─────────────────────────────────────────────

    def _on_log_received(self, source: str, text: str) -> None:
        tag = "SRV" if source == "server" else "CLI"
        # Append formatted output
        for line in text.splitlines():
            if line.strip():
                self._console_text.appendPlainText(f"[{tag}] {line}")

    def _on_proc_state_changed(self, source: str, is_running: bool) -> None:
        if source == "server":
            self._start_server_btn.setEnabled(not is_running)
            self._stop_server_btn.setEnabled(is_running)
        elif source == "client":
            self._start_client_btn.setEnabled(not is_running)
            self._stop_client_btn.setEnabled(is_running)

    # ── Health Status Poll Callback ───────────────────────────────────────────

    def _on_health_updated(self, is_ok: bool) -> None:
        was_offline = not self._server_online
        self._server_online = is_ok
        if is_ok:
            self._status_badge.setText("🟢 Online")
            self._status_badge.setStyleSheet("color: #22c55e;")
            self._status_label.setText("Server connected & responsive.")
            if was_offline:
                self.refresh_models()
        else:
            self._status_badge.setText("🔴 Offline")
            self._status_badge.setStyleSheet("color: #ef4444;")
            self._status_label.setText("Server not responding.")
            self._session_count_label.setText("Active Sessions: —")

    # ── Model Hub Business Logic ──────────────────────────────────────────────

    def refresh_models(self) -> None:
        """Trigger async model/session retrieval."""
        # Force API configuration refresh in case user changed settings in client
        self._api_client.reload_settings()

        if not self._server_online:
            self._model_table.setRowCount(0)
            self._session_count_label.setText("Active Sessions: Server Offline")
            return

        self._refresh_models_btn.setEnabled(False)
        self._status_label.setText("Fetching model configuration from server API...")

        self._model_worker = ModelRefreshWorker(self._api_client, parent=self)
        self._model_worker.refresh_done.connect(self._on_models_refreshed)
        self._model_worker.refresh_error.connect(self._on_models_refresh_failed)
        self._model_worker.finished.connect(lambda: self._refresh_models_btn.setEnabled(True))
        self._model_worker.finished.connect(self._model_worker.deleteLater)
        self._model_worker.start()

    def _on_models_refreshed(self, models: List[Dict[str, Any]], active_detectors: Set[str], session_count: int) -> None:
        self._active_detector_models = active_detectors
        self._session_count_label.setText(f"Active Sessions: {session_count}")
        self._status_label.setText(f"Models synchronized. Active sessions: {session_count}")

        self._model_table.setRowCount(0)
        for row_idx, model in enumerate(models):
            self._model_table.insertRow(row_idx)

            name = model.get("name", "Unknown")
            mtype = model.get("type", "detector")
            size_mb = model.get("size_mb", 0.0)

            # Check strict lock logic
            is_locked = name in self._active_detector_models

            # Populate items
            self._model_table.setItem(row_idx, 0, QTableWidgetItem(name))
            self._model_table.setItem(row_idx, 1, QTableWidgetItem(mtype))
            self._model_table.setItem(row_idx, 2, QTableWidgetItem(f"{size_mb:.2f} MB"))

            status_str = "🔒 In Use" if is_locked else "Available"
            status_item = QTableWidgetItem(status_str)
            if is_locked:
                status_item.setForeground(QColor("#f59e0b"))  # Yellowish warning color
            else:
                status_item.setForeground(QColor("#22c55e"))  # Green safety color

            self._model_table.setItem(row_idx, 3, status_item)

        self._on_table_selection_changed()

    def _on_models_refresh_failed(self, error_msg: str) -> None:
        self._status_label.setText(f"Error checking API status: {error_msg}")
        QMessageBox.warning(self, "API Sync Failure", f"Failed to sync models via API:\n{error_msg}")

    def _on_table_selection_changed(self) -> None:
        selected_rows = self._model_table.selectionModel().selectedRows()
        if not selected_rows:
            self._delete_model_btn.setEnabled(False)
            return

        row = selected_rows[0].row()
        name_item = self._model_table.item(row, 0)
        status_item = self._model_table.item(row, 3)

        if not name_item or not status_item:
            self._delete_model_btn.setEnabled(False)
            return

        model_name = name_item.text()
        status_str = status_item.text()

        # Strict lock check
        is_locked = "🔒" in status_str or model_name in self._active_detector_models
        self._delete_model_btn.setEnabled(not is_locked)

    def _on_add_model_clicked(self) -> None:
        """Browse and import a local model into the server's directory."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select YOLO or ReID Model File",
            "",
            "PyTorch Weight Files (*.pt)"
        )
        if not file_path:
            return

        src_path = Path(file_path)

        # Ask user for classification
        reply = QMessageBox.question(
            self,
            "Model Classification",
            f"Is '{src_path.name}' a Detector model (YOLO) or a ReID model?\n\nYes: Detector\nNo: ReID",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Cancel:
            return

        subdir = _DETECTORS_DIR if reply == QMessageBox.StandardButton.Yes else _REID_DIR
        subdir.mkdir(parents=True, exist_ok=True)

        dest_path = subdir / src_path.name
        if dest_path.exists():
            QMessageBox.warning(self, "Import Failed", f"A model named '{src_path.name}' already exists in that category.")
            return

        try:
            shutil.copy2(src_path, dest_path)
            QMessageBox.information(self, "Success", f"Successfully imported '{src_path.name}' to model store.")
            self.refresh_models()
        except Exception as exc:
            QMessageBox.critical(self, "File Operations Error", f"Failed to import model: {exc}")

    def _on_delete_model_clicked(self) -> None:
        """Removes the selected model file after strict safety check."""
        selected_rows = self._model_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        name_item = self._model_table.item(row, 0)
        if not name_item:
            return

        model_name = name_item.text()

        # Strict safety double check: fetch active sessions again synchronously right before deletion
        try:
            self._status_label.setText("Double-checking active sessions before delete operation...")
            session_ids = self._api_client.get_sessions()
            active_detectors = set()
            for sid in session_ids:
                detail = self._api_client.get_session_detail(sid)
                det = detail.get("detector_model")
                if det:
                    active_detectors.add(det)

            if model_name in active_detectors:
                QMessageBox.warning(
                    self,
                    "Strict Lock Violation",
                    f"Action Cancelled: '{model_name}' has just become active in a running session."
                )
                self.refresh_models()
                return
        except Exception as exc:
            QMessageBox.warning(
                self,
                "API Warning",
                f"Could not verify active sessions: {exc}. Aborting delete for safety."
            )
            return

        # Confirm deletion
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete '{model_name}' from the server's model store?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        # Delete matching file from detectors or reid directories
        deleted = False
        for folder in [_DETECTORS_DIR, _REID_DIR, _MODELS_DIR]:
            file_to_delete = folder / model_name
            if file_to_delete.exists():
                try:
                    file_to_delete.unlink()
                    deleted = True
                except Exception as exc:
                    QMessageBox.critical(self, "File Operations Error", f"Error unlinking file: {exc}")
                    return

        if deleted:
            self._status_label.setText(f"Deleted model: {model_name}")
            self.refresh_models()
        else:
            QMessageBox.warning(self, "File Not Found", f"Failed to locate '{model_name}' file on server storage.")

    # ── Cleanup on Close ──────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Stop threads and uvicorn/client subprocesses gracefully."""
        self._health_worker.stop()
        try:
            if hasattr(self, "_model_worker") and self._model_worker and not isdeleted(self._model_worker):
                if self._model_worker.isRunning():
                    self._model_worker.quit()
                    self._model_worker.wait(1000)
        except Exception:
            pass
        self._proc_mgr.terminate_all()
        super().closeEvent(event)
