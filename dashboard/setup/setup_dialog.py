"""
SetupDialog — a modal QDialog that runs the first-time bootstrap setup.

Shows a live log output and a progress bar while:
  1. Creating the 'fwa' venv
  2. Installing all requirements
  3. Downloading missing HuggingFace models

The dialog auto-closes on success. On failure it shows the error
and leaves the Close button available so the user can read the log.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from dashboard.setup.setup_manager import run_full_setup


# ── Worker ────────────────────────────────────────────────────────────────────

class SetupWorker(QThread):
    """Runs the full setup sequence in a background thread."""

    log_line  = pyqtSignal(str)   # emits one text chunk at a time
    succeeded = pyqtSignal()
    failed    = pyqtSignal(str)   # emits error message

    def run(self) -> None:
        try:
            run_full_setup(log=self.log_line.emit)
            self.succeeded.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


# ── Dialog ────────────────────────────────────────────────────────────────────

class SetupDialog(QDialog):
    """Modal progress dialog for first-time environment & model setup."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Balkontech — First-Run Setup")
        self.setMinimumSize(700, 420)
        self.setModal(True)
        self._success = False

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title
        title = QLabel("🚀 Setting up Balkontech environment…")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Creating the <b>fwa</b> virtual environment, installing packages "
            "and downloading missing YOLO models from HuggingFace.<br>"
            "This only runs once — subsequent launches skip completed steps."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Live log console
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(2000)
        self._log.setFont(QFont("Courier New", 9))
        self._log.setStyleSheet("background:#111; color:#00ff00;")
        layout.addWidget(self._log)

        # Progress bar (indeterminate)
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)   # marquee/indeterminate
        layout.addWidget(self._progress)

        # Status label
        self._status = QLabel("Initializing…")
        layout.addWidget(self._status)

        # Close button (hidden until done)
        self._btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self._btn_box.setEnabled(False)
        self._btn_box.rejected.connect(self.reject)
        layout.addWidget(self._btn_box)

        # Start worker
        self._worker = SetupWorker(parent=self)
        self._worker.log_line.connect(self._append_log)
        self._worker.succeeded.connect(self._on_success)
        self._worker.failed.connect(self._on_failure)
        self._worker.start()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _append_log(self, text: str) -> None:
        for line in text.splitlines():
            if line.strip():
                self._log.appendPlainText(line)

    def _on_success(self) -> None:
        self._success = True
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._status.setText("✅ Setup complete! Launching dashboard…")
        self._btn_box.setEnabled(True)
        # Auto-close after brief pause
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1200, self.accept)

    def _on_failure(self, error: str) -> None:
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._status.setText(f"❌ Setup failed: {error}")
        self._status.setStyleSheet("color: #ef4444;")
        self._btn_box.setEnabled(True)
        self._append_log(f"\n[ERROR] {error}\n")

    def was_successful(self) -> bool:
        return self._success

    def closeEvent(self, event) -> None:
        """Stop the worker thread if the user closes the dialog early."""
        if self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)
        super().closeEvent(event)
