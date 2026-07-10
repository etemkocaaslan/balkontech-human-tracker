"""
Balkontech Master Dashboard — entry point.

Run this script to launch the dashboard:
    python -m dashboard.main

On first run (or if the fwa venv / models are missing) a setup wizard
dialog appears automatically. Subsequent launches skip completed steps.
"""

import sys
import hashlib
import json
from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QMessageBox

from dashboard.setup.setup_manager import (
    venv_exists,
    missing_models,
    VENV_PYTHON,
)
from dashboard.setup.setup_dialog import SetupDialog
from dashboard.ui.main_window import MainWindow

# ── Constants ─────────────────────────────────────────────────────────────────

APP_ORG    = "Balkontech"
APP_NAME   = "HumanTracker"
MASTER_KEY = "bht_admin_master_dashboard_secret_key_8000"

_REPO_ROOT = Path(__file__).resolve().parent.parent


# ── API Key bootstrap ─────────────────────────────────────────────────────────

def ensure_admin_api_key() -> None:
    """Auto-registers the master API key in the server's json database
    and shares it in QSettings so both client and dashboard connect seamlessly.
    """
    # 1. Save to QSettings so the client picks it up automatically
    settings = QSettings(APP_ORG, APP_NAME)
    settings.setValue("api/key", MASTER_KEY)
    if not settings.value("api/base_url"):
        settings.setValue("api/base_url", "http://127.0.0.1:8000")

    # 2. Write key hash to server's api_keys.json
    keys_file = _REPO_ROOT / "balkontech-server" / "api_keys.json"
    key_hash  = hashlib.sha256(MASTER_KEY.encode()).hexdigest()

    keys: list = []
    if keys_file.exists():
        try:
            with open(keys_file, "r", encoding="utf-8") as f:
                keys = json.load(f)
        except Exception:
            keys = []

    if not any(k.get("key_hash") == key_hash for k in keys):
        keys.append({
            "id":         "admin_db",
            "name":       "Balkontech Master Dashboard",
            "key_hash":   key_hash,
            "created_at": "2026-07-09T00:00:00.000000+00:00",
        })
        try:
            keys_file.parent.mkdir(parents=True, exist_ok=True)
            with open(keys_file, "w", encoding="utf-8") as f:
                json.dump(keys, f, indent=2)
        except Exception:
            pass


# ── Theme ─────────────────────────────────────────────────────────────────────

def apply_dark_palette(app: QApplication) -> None:
    """Configures the dark fusion palette to align with the client's design theme."""
    app.setStyle("Fusion")
    dark = QPalette()
    dark.setColor(QPalette.ColorRole.Window,          QColor(30, 30, 30))
    dark.setColor(QPalette.ColorRole.WindowText,      QColor(220, 220, 220))
    dark.setColor(QPalette.ColorRole.Base,            QColor(25, 25, 25))
    dark.setColor(QPalette.ColorRole.AlternateBase,   QColor(45, 45, 45))
    dark.setColor(QPalette.ColorRole.ToolTipBase,     QColor(255, 255, 220))
    dark.setColor(QPalette.ColorRole.ToolTipText,     QColor(0, 0, 0))
    dark.setColor(QPalette.ColorRole.Text,            QColor(220, 220, 220))
    dark.setColor(QPalette.ColorRole.Button,          QColor(53, 53, 53))
    dark.setColor(QPalette.ColorRole.ButtonText,      QColor(220, 220, 220))
    dark.setColor(QPalette.ColorRole.BrightText,      QColor(255, 0, 0))
    dark.setColor(QPalette.ColorRole.Link,            QColor(42, 130, 218))
    dark.setColor(QPalette.ColorRole.Highlight,       QColor(42, 130, 218))
    dark.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(dark)


# ── Entry point ───────────────────────────────────────────────────────────────

def setup_needed() -> bool:
    """Return True if the venv is missing or any model file is absent."""
    return not venv_exists() or bool(missing_models())


def main() -> None:
    # Register master API key before anything else
    ensure_admin_api_key()

    app = QApplication(sys.argv)
    app.setApplicationName("Balkontech Master Dashboard")
    app.setOrganizationName("Balkontech")
    apply_dark_palette(app)

    # ── First-run setup wizard ────────────────────────────────────────────────
    if setup_needed():
        dialog = SetupDialog()
        dialog.exec()
        if not dialog.was_successful():
            QMessageBox.critical(
                None,
                "Setup Failed",
                "First-run setup did not complete successfully.\n"
                "Please check the log in the setup dialog and try again.",
            )
            sys.exit(1)

    # ── Main window ───────────────────────────────────────────────────────────
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
