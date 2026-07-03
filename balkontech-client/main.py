"""
Balkontech Human Tracker — desktop client entry point.

Run:
    python main.py
"""

import sys

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Balkontech Human Tracker")
    app.setOrganizationName("Balkontech")

    # Dark palette (optional — comment out to use system theme)
    app.setStyle("Fusion")
    _apply_dark_palette(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


def _apply_dark_palette(app: QApplication) -> None:
    from PyQt6.QtGui import QColor, QPalette

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


if __name__ == "__main__":
    main()
