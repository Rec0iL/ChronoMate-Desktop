"""
ChronoMate Desktop - Target Reticle Canvas
Custom QPainter widget rendering the circular tactical target reticle,
crosshairs, mil-dots, and point-of-impact at specified target distance.
"""

from typing import List, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from core.models import TrajectoryPoint
from core.i18n import tr


class TargetCanvas(QWidget):
    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 220)
        self._dark_mode = dark_mode
        self._trajectory: List[TrajectoryPoint] = []
        self._target_distance: float = 50.0
        self._target_height_m: float = 1.50
        self._relative_impact_cm: float = 0.0

    def update_data(self, trajectory: List[TrajectoryPoint], target_distance: float, target_height_m: float):
        self._trajectory = trajectory
        self._target_distance = target_distance
        self._target_height_m = target_height_m

        if trajectory:
            pt_at_dist = min(trajectory, key=lambda p: abs(p.x - target_distance))
            self._relative_impact_cm = (pt_at_dist.y - target_height_m) * 100.0
        else:
            self._relative_impact_cm = 0.0

        self.update()

    def set_theme(self, dark_mode: bool):
        self._dark_mode = dark_mode
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        bg_color = QColor("#0E1117") if self._dark_mode else QColor("#FFFFFF")
        crosshair_color = QColor(255, 255, 255, 60) if self._dark_mode else QColor(0, 0, 0, 70)
        grid_color = QColor(255, 255, 255, 15) if self._dark_mode else QColor(0, 0, 0, 15)
        text_color = QColor("#8B949E") if self._dark_mode else QColor("#656D76")
        accent_color = QColor("#88FF11") if self._dark_mode else QColor("#2E7D32")
        danger_color = QColor("#F44336") if self._dark_mode else QColor("#C62828")

        painter.setPen(Qt.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(0, 0, w, h, 8, 8)

        # Title at Top
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.setPen(text_color)
        painter.drawText(QRectF(0, 8, w, 18), Qt.AlignCenter, tr("target_view_label", self._target_distance))

        # Center for reticle
        reticle_size = min(w - 20, h - 60)
        reticle_radius = reticle_size / 2.0
        center_x = w / 2.0
        center_y = 30 + reticle_radius

        # Reticle Outer Circle
        painter.setPen(QPen(crosshair_color, 1.8))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(center_x, center_y), reticle_radius, reticle_radius)

        # Inner 50% ring
        painter.setPen(QPen(grid_color, 1))
        painter.drawEllipse(QPointF(center_x, center_y), reticle_radius * 0.5, reticle_radius * 0.5)

        # Crosshairs
        painter.setPen(QPen(crosshair_color, 1.2))
        painter.drawLine(QPointF(center_x - reticle_radius, center_y), QPointF(center_x + reticle_radius, center_y))
        painter.drawLine(QPointF(center_x, center_y - reticle_radius), QPointF(center_x, center_y + reticle_radius))

        # Mil-dot ticks
        tick_spacing = reticle_radius / 5.0
        painter.setPen(QPen(crosshair_color, 1))
        for i in range(-4, 5):
            if i == 0:
                continue
            # Horizontal ticks
            tx = center_x + i * tick_spacing
            painter.drawLine(QPointF(tx, center_y - 3), QPointF(tx, center_y + 3))
            # Vertical ticks
            ty = center_y + i * tick_spacing
            painter.drawLine(QPointF(center_x - 3, ty), QPointF(center_x + 3, ty))

        # Point of Impact Dot
        scale_cm_to_px = 3.5  # 1 cm = 3.5 px
        impact_y = center_y - (self._relative_impact_cm * scale_cm_to_px)

        dot_in_bounds = (center_y - reticle_radius) <= impact_y <= (center_y + reticle_radius)
        dot_color = accent_color if self._relative_impact_cm >= 0 else danger_color

        if dot_in_bounds:
            painter.setPen(Qt.NoPen)
            painter.setBrush(dot_color)
            painter.drawEllipse(QPointF(center_x, impact_y), 6.0, 6.0)

            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(QPointF(center_x, impact_y), 2.0, 2.0)
        else:
            # Clamped indicator arrow if off-reticle
            clamped_y = max(center_y - reticle_radius + 6, min(center_y + reticle_radius - 6, impact_y))
            painter.setPen(Qt.NoPen)
            painter.setBrush(dot_color)
            painter.drawEllipse(QPointF(center_x, clamped_y), 4.0, 4.0)

        # Hit readout text at bottom
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.setPen(dot_color)
        if self._relative_impact_cm >= 0:
            hit_text = tr("hit_above", self._relative_impact_cm)
        else:
            hit_text = tr("hit_below", abs(self._relative_impact_cm))

        painter.drawText(QRectF(0, h - 26, w, 20), Qt.AlignCenter, hit_text)
