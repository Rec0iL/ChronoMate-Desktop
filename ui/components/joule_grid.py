"""
ChronoMate Desktop - Orga Chrono Joule Reference Grid
Color-coded reference cards for all standard/custom BB weights
Green = Safe, Orange = Practical Limit, Red = Over Limit / Illegal.
"""

from typing import List, Tuple
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QGridLayout, QLabel, QLayout, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from core.i18n import tr
from ui.components.stable_text import reserve_text_space, equalize_widths


class JouleCard(QFrame):
    clicked = Signal(int)

    def __init__(self, weight: float, label: str, parent=None, index: int = 0):
        super().__init__(parent)
        self.weight = weight
        self.index = index
        self.label_text = label
        self.is_selected = False      # the weight the shots / alert sound use right now
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tr("joule_tile_tooltip"))

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
        reserve_text_space(self.lbl_weight, [label, f"★ {label}"])
        reserve_text_space(self.lbl_joules, ["-- J", "88.88 J"])
        self.update_state(0.0, 0.0, True)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
        super().mouseReleaseEvent(event)

    def update_state(self, energy: float, practical_weight: float, dark_mode: bool):
        self.lbl_joules.setText(f"{energy:.2f} J" if energy > 0 else "-- J")
        self.lbl_weight.setText(f"★ {self.label_text}" if self.is_selected else self.label_text)

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
                border: {"3.5px" if self.is_selected else "1.5px"} solid {("#00E5FF" if dark_mode else "#00838F") if self.is_selected else border};
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
    tile_clicked = Signal(int)   # index into the weights given to set_weights()

    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self._dark_mode = dark_mode
        self._grid_layout = QGridLayout(self)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(10)
        # Fewer columns on narrow windows: the grid itself must not force its full width
        self._grid_layout.setSizeConstraint(QLayout.SetNoConstraint)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._cards: List[JouleCard] = []
        self._last_velocity = 0.0
        self._last_limit = 1.5
        self._max_cols = 5
        self._shown_cols = 5

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._cards and self._fit_columns() != self._shown_cols:
            self._place()

    def _fit_columns(self) -> int:
        if not self._cards or self.width() <= 0:
            return self._max_cols
        spacing = self._grid_layout.spacing()
        cell = self._cards[0].minimumWidth() + spacing
        return max(1, min(self._max_cols, (self.width() + spacing) // max(1, cell)))

    def _place(self):
        cols = self._fit_columns()
        self._shown_cols = cols
        for card in self._cards:
            self._grid_layout.removeWidget(card)
        for idx, card in enumerate(self._cards):
            self._grid_layout.addWidget(card, idx // cols, idx % cols)
        for c in range(max(self._grid_layout.columnCount(), self._max_cols)):
            self._grid_layout.setColumnStretch(c, 1 if c < cols else 0)
        if self._cards:
            rows = (len(self._cards) + cols - 1) // cols
            h = max(c.sizeHint().height() for c in self._cards)
            self.setMinimumHeight(rows * h + (rows - 1) * self._grid_layout.spacing())
            self.setMinimumWidth(self._cards[0].minimumWidth())

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
            card = JouleCard(w, label, self, index=idx)
            card.clicked.connect(self.tile_clicked)
            row = idx // columns
            col = idx % columns
            self._grid_layout.addWidget(card, row, col)
            self._cards.append(card)

        # Equal, content-independent columns: "-- J" → "1.23 J" must not move anything.
        equalize_widths(self._cards)
        self._max_cols = columns
        self._place()

    def set_selected_flags(self, flags):
        for card, flag in zip(self._cards, flags):
            card.is_selected = bool(flag)
        self.update_velocity(self._last_velocity, self._last_limit)

    def update_velocity(self, velocity: float, max_allowed_joule: float):
        self._last_velocity, self._last_limit = velocity, max_allowed_joule
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
