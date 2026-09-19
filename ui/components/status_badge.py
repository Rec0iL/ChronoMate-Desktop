"""
ChronoMate Desktop - Status Badge Component
Clickable status badge with pulse indicator for Chrono connection state.
"""

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from core.models import ConnectionState


class StatusBadge(QPushButton):
    clicked_reconnect = Signal()

    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(28)
        self.setMinimumWidth(120)
        self._dark_mode = dark_mode
        self._state: ConnectionState = ConnectionState.DISCONNECTED
        self.clicked.connect(self.clicked_reconnect)

        self.set_state(ConnectionState.DISCONNECTED)

    def set_state(self, state: ConnectionState, error_msg: str = ""):
        self._state = state

        if state == ConnectionState.CONNECTED:
            badge_color = "#88FF11" if self._dark_mode else "#2E7D32"
            bg_color = "rgba(136, 255, 17, 0.12)" if self._dark_mode else "rgba(46, 125, 50, 0.12)"
            text = "● LIVE"
        elif state in (ConnectionState.CONNECTING, ConnectionState.LINKED):
            badge_color = "#FFD600" if self._dark_mode else "#F57F17"
            bg_color = "rgba(255, 214, 0, 0.12)" if self._dark_mode else "rgba(245, 127, 23, 0.12)"
            text = "● CONNECTING…"
        else:
            badge_color = "#F44336" if self._dark_mode else "#C62828"
            bg_color = "rgba(244, 67, 54, 0.12)" if self._dark_mode else "rgba(198, 40, 40, 0.12)"
            text = "● OFFLINE"

        self.setText(text)
        self.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {badge_color};
                border: 1px solid {badge_color};
                border-radius: 14px;
                padding: 3px 12px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {badge_color};
                color: #000000;
            }}
        """)
        self.setToolTip("Click to test / reconnect to Chronograph")

    def set_theme(self, dark_mode: bool):
        self._dark_mode = dark_mode
        self.set_state(self._state)
