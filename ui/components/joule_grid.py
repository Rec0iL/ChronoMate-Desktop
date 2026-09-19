"""
ChronoMate Desktop - Orga Chrono Joule Reference Grid
Color-coded reference cards for all standard/custom BB weights
Green = Safe, Orange = Practical Limit, Red = Over Limit / Illegal.
"""

from typing import List, Tuple
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QGridLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from core.i18n import tr


class JouleCard(QFrame):
    def __init__(self, weight: float, label: str, parent=None):
        super().__init__(parent)
        self.weight = weight
        self.label_text = label

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        self.lbl_weight = QLabel(label)
        self.lbl_weight.setAlignment(Qt.AlignCenter)
        self.lbl_weight.setFont(QFont("Segoe UI", 9, QFont.Bold))

        self.lbl_joules = QLabel("0.00 J")
        self.lbl_joules.setAlignment(Qt.AlignCenter)
        self.lbl_joules.setFont(QFont("Consolas, Courier New", 14, QFont.Bold))

        layout.addWidget(self.lbl_weight)
        layout.addWidget(self.lbl_joules)
        self.update_state(0.0, 0.0, True)

    def update_state(self, energy: float, practical_weight: float, dark_mode: bool):
        self.lbl_joules.setText(f"{energy:.2f} J" if energy > 0 else "-- J")

        if energy <= 0:
            bg = "#161B22" if dark_mode else "#ECEFF1"
            border = "#30363D" if dark_mode else "#CFD8DC"
            text_color = "#8B949E" if dark_mode else "#546E7A"
            joule_color = "#F0F6FC" if dark_mode else "#263238"
        elif self.weight < practical_weight:
            # Safe (Green)
            bg = "rgba(46, 125, 50, 0.22)" if dark_mode else "rgba(46, 125, 50, 0.12)"
            border = "#2E7D32" if dark_mode else "#4CAF50"
            text_color = "#88FF11" if dark_mode else "#1B5E20"
            joule_color = "#88FF11" if dark_mode else "#1B5E20"
        elif self.weight == practical_weight:
            # Limit (Orange)
            bg = "rgba(230, 81, 0, 0.28)" if dark_mode else "rgba(239, 108, 0, 0.15)"
            border = "#FF9800" if dark_mode else "#EF6C00"
            text_color = "#FFB74D" if dark_mode else "#E65100"
            joule_color = "#FFB74D" if dark_mode else "#E65100"
        else:
            # Illegal / Over limit (Red)
            bg = "rgba(183, 28, 28, 0.25)" if dark_mode else "rgba(198, 40, 40, 0.12)"
            border = "#F44336" if dark_mode else "#C62828"
            text_color = "#EF5350" if dark_mode else "#B71C1C"
            joule_color = "#EF5350" if dark_mode else "#B71C1C"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1.5px solid {border};
                border-radius: 8px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        self.lbl_weight.setStyleSheet(f"color: {text_color};")
        self.lbl_joules.setStyleSheet(f"color: {joule_color};")


class JouleGrid(QWidget):
    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self._dark_mode = dark_mode
        self._grid_layout = QGridLayout(self)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(10)
        self._cards: List[JouleCard] = []

    def set_weights(self, weights: List[Tuple[float, str]], columns: int = 5):
        # Clear existing
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._cards.clear()

        for idx, (w, label) in enumerate(weights):
            card = JouleCard(w, label, self)
            row = idx // columns
            col = idx % columns
            self._grid_layout.addWidget(card, row, col)
            self._cards.append(card)

    def update_velocity(self, velocity: float, max_allowed_joule: float):
        if not self._cards:
            return

        # Calculate max practical weight
        max_weight_kg = (2.0 * max_allowed_joule) / (velocity ** 2) if velocity > 0 else 0.0
        max_weight_grams = max_weight_kg * 1000.0

        weights_list = [c.weight for c in self._cards]
        legal_weights = [w for w in weights_list if w <= max_weight_grams]
        practical_weight = max(legal_weights) if legal_weights else 0.0

        for card in self._cards:
            energy = 0.5 * (card.weight / 1000.0) * (velocity ** 2) if velocity > 0 else 0.0
            card.update_state(energy, practical_weight, self._dark_mode)

    def set_theme(self, dark_mode: bool):
        self._dark_mode = dark_mode
        for card in self._cards:
            card.update_state(0.0, 0.0, dark_mode)
