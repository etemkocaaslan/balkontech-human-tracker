"""
ZonePanel — displays zone occupancy coming from StatsWorker.

Receives the stats dict:
  {
    "session_id": "...",
    "frame_index": 42,
    "track_count": 3,
    "zone_occupancy": {"Zone A": [1, 5], "Zone B": []}
  }
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class _ZoneCard(QWidget):
    """Single zone row: coloured dot · zone name · worker count badge."""

    _COLORS = [
        "#e74c3c", "#3498db", "#2ecc71", "#f39c12",
        "#9b59b6", "#1abc9c", "#e67e22", "#34495e",
    ]

    def __init__(self, zone_name: str, color_index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        color = self._COLORS[color_index % len(self._COLORS)]

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        dot.setFixedWidth(18)

        self._name_label = QLabel(zone_name)
        self._name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._count_badge = QLabel("0")
        self._count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_badge.setFixedSize(28, 20)
        self._count_badge.setStyleSheet(
            "background: #3d3d3d; color: #ccc; border-radius: 10px; font-size: 11px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)
        layout.addWidget(dot)
        layout.addWidget(self._name_label)
        layout.addWidget(self._count_badge)

    def update_count(self, track_ids: list[int]) -> None:
        n = len(track_ids)
        self._count_badge.setText(str(n))
        if n > 0:
            self._count_badge.setStyleSheet(
                "background: #27ae60; color: #fff; border-radius: 10px; font-size: 11px;"
            )
        else:
            self._count_badge.setStyleSheet(
                "background: #3d3d3d; color: #ccc; border-radius: 10px; font-size: 11px;"
            )


class ZonePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(200)

        # Header
        header = QLabel("Zone Occupancy")
        header.setStyleSheet("font-weight: bold; font-size: 13px; padding: 4px 0;")

        self._summary_label = QLabel("No active session")
        self._summary_label.setStyleSheet("color: #888; font-size: 11px;")
        self._summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Scrollable zone cards area
        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setSpacing(4)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._cards_widget)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #444;")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        root.addWidget(header)
        root.addWidget(sep)
        root.addWidget(self._summary_label)
        root.addWidget(scroll, stretch=1)

        self._cards: dict[str, _ZoneCard] = {}

    # ── Public API ────────────────────────────────────────────────────

    def update_stats(self, stats: dict) -> None:
        """Call from StatsWorker.stats_ready signal with the latest stats dict."""
        occupancy: dict[str, list[int]] = stats.get("zone_occupancy") or {}
        track_count: int = stats.get("track_count", 0)
        frame_idx: int   = stats.get("frame_index", 0)

        # Build / update cards
        for i, (zone_name, track_ids) in enumerate(occupancy.items()):
            if zone_name not in self._cards:
                card = _ZoneCard(zone_name, i)
                # Insert before the trailing stretch
                self._cards_layout.insertWidget(
                    self._cards_layout.count() - 1, card
                )
                self._cards[zone_name] = card
            self._cards[zone_name].update_count(track_ids)

        # Remove stale cards (zone deleted / session switched)
        for zone_name in list(self._cards):
            if zone_name not in occupancy:
                card = self._cards.pop(zone_name)
                self._cards_layout.removeWidget(card)
                card.deleteLater()

        # Update summary
        occupied = sum(1 for ids in occupancy.values() if ids)
        if occupancy:
            self._summary_label.setText(
                f"Frame {frame_idx} · {track_count} tracked · "
                f"{occupied}/{len(occupancy)} zones occupied"
            )
        else:
            self._summary_label.setText(f"Frame {frame_idx} · {track_count} tracked · no zones")

    def clear(self) -> None:
        """Reset panel when session changes or stops."""
        for card in self._cards.values():
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._summary_label.setText("No active session")
