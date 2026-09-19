"""
ChronoMate Desktop - Hero Card Component
Displays prominent real-time Velocity and Energy readouts with automatic font scaling.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from core.i18n import tr


class HeroCard(QFrame):
    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("hero_card")
        self._dark_mode = dark_mode
        self._latest_vel = 0.0
        self._latest_energy = 0.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # Header label
        self.lbl_title = QLabel(tr("latest_shot").upper())
        self.lbl_title.setObjectName("label_secondary")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_title)

        # Velocity + Unit Row
        vel_row = QHBoxLayout()
        vel_row.setAlignment(Qt.AlignCenter)
        vel_row.setSpacing(4)

        self.lbl_velocity = QLabel("0.00")
        self.lbl_velocity.setAlignment(Qt.AlignCenter)

        self.lbl_unit = QLabel(" m/s")
        self.lbl_unit.setAlignment(Qt.AlignBottom)

        vel_row.addWidget(self.lbl_velocity)
        vel_row.addWidget(self.lbl_unit)
        layout.addLayout(vel_row)

        # Energy Label
        self.lbl_energy = QLabel("0.00 J")
        self.lbl_energy.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_energy)

        self.set_theme(dark_mode)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_font_size()

    def update_telemetry(self, velocity: float, energy: float):
        self._latest_vel = velocity
        self._latest_energy = energy
        self.lbl_velocity.setText(f"{velocity:.2f}")
        self.lbl_energy.setText(f"{energy:.2f} J")
        self._adjust_font_size()

    def set_theme(self, dark_mode: bool):
        self._dark_mode = dark_mode
        self._adjust_font_size()

    def _adjust_font_size(self):
        text = self.lbl_velocity.text()
        if not text:
            return

        margins = self.layout().contentsMargins()
        actual_w = max(self.width(), self.minimumWidth(), 260)
        avail_w = actual_w - margins.left() - margins.right() - 8

        accent = "#88FF11" if self._dark_mode else "#1B5E20"

        max_px = 54
        min_px = 20
        chosen_px = min_px

        for px in range(max_px, min_px - 1, -2):
            f_vel = QFont("Consolas, Courier New, monospace")
            f_vel.setPixelSize(px)
            f_vel.setWeight(QFont.Black)

            f_unit = QFont("Segoe UI")
            f_unit.setPixelSize(max(11, int(px * 0.32)))
            f_unit.setWeight(QFont.Bold)

            fm_v = QFontMetrics(f_vel)
            fm_u = QFontMetrics(f_unit)

            total_w = fm_v.horizontalAdvance(text) + fm_u.horizontalAdvance(" m/s") + 4
            if total_w <= avail_w:
                chosen_px = px
                break

        unit_px = max(11, int(chosen_px * 0.32))
        margin_b = max(4, int(chosen_px * 0.14))
        energy_px = max(16, int(chosen_px * 0.48))

        self.lbl_velocity.setStyleSheet(
            f"color: {accent}; font-size: {chosen_px}px; font-weight: 900; font-family: Consolas, 'Courier New', monospace; border: none; background: transparent;"
        )
        self.lbl_unit.setStyleSheet(
            f"color: {accent}; opacity: 0.85; font-size: {unit_px}px; font-weight: 700; font-family: 'Segoe UI', sans-serif; border: none; background: transparent; margin-bottom: {margin_b}px;"
        )
        self.lbl_energy.setStyleSheet(
            f"color: {accent}; font-size: {energy_px}px; font-weight: 700; font-family: 'Segoe UI', sans-serif; border: none; background: transparent;"
        )
