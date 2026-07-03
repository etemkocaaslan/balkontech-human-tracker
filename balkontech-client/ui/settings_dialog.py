"""
SettingsDialog — persistent connection configuration.

API URL and key are stored with QSettings (Windows Registry on Windows,
~/.config on Linux/macOS) and restored on next launch.
"""

from __future__ import annotations

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

APP_ORG  = "Balkontech"
APP_NAME = "HumanTracker"


def load_settings() -> tuple[str, str]:
    """Return (base_url, api_key) from persistent storage."""
    s = QSettings(APP_ORG, APP_NAME)
    return (
        s.value("api/base_url", "http://127.0.0.1:8000"),
        s.value("api/key",      ""),
    )


def save_settings(base_url: str, api_key: str) -> None:
    s = QSettings(APP_ORG, APP_NAME)
    s.setValue("api/base_url", base_url)
    s.setValue("api/key",      api_key)


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Connection Settings")
        self.setMinimumWidth(420)

        base_url, api_key = load_settings()

        self._url_edit = QLineEdit(base_url)
        self._key_edit = QLineEdit(api_key)
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_edit.setPlaceholderText("bht_…  (create in admin panel → API Keys)")

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Backend URL:", self._url_edit)
        form.addRow("API Key:", self._key_edit)

        hint = QLabel(
            "Open <b>http://127.0.0.1:8000</b> in a browser,<br>"
            "go to the <b>🔑 API Keys</b> tab to create a key."
        )
        hint.setStyleSheet("color: #888; font-size: 11px;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        save_settings(self._url_edit.text().strip(), self._key_edit.text().strip())
        self.accept()
