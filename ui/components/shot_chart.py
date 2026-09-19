"""
ChronoMate Desktop - Interactive Velocity Trend Chart
Custom QPainter widget providing smooth rendering, glowing curves,
average line, zoom/pan controls, and interactive shot inspection cards.
"""

from typing import List, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
    QPainterPath,
    QLinearGradient,
    QMouseEvent,
    QWheelEvent,
)
from core.models import Shot


class ShotChart(QWidget):
    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(220)
        self._dark_mode = dark_mode
        self._shots: List[Shot] = []
        self._hovered_index: Optional[int] = None

        # Zoom & Pan State
        self._zoom: float = 1.0
        self._pan_offset: float = 0.0
        self._is_dragging: bool = False
        self._last_mouse_x: float = 0.0

    def set_shots(self, shots: List[Shot]):
        self._shots = shots
        if self._hovered_index is not None and self._hovered_index >= len(shots):
            self._hovered_index = None
        self.update()

    def set_theme(self, dark_mode: bool):
        self._dark_mode = dark_mode
        self.update()

    def reset_view(self):
        self._zoom = 1.0
        self._pan_offset = 0.0
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._last_mouse_x = event.position().x()
        elif event.button() == Qt.RightButton:
            self.reset_view()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        if self._is_dragging:
            dx = pos.x() - self._last_mouse_x
            self._pan_offset += dx
            self._last_mouse_x = pos.x()
            self.update()
            return

        # Find closest shot index on hover
        left_m = 50.0
        right_m = 20.0
        chart_w = self.width() - left_m - right_m
        if chart_w > 0 and len(self._shots) > 0:
            x_rel = pos.x() - left_m - self._pan_offset
            total_w = chart_w * self._zoom
            if len(self._shots) > 1:
                step = total_w / (len(self._shots) - 1)
                idx = int(round(x_rel / step))
                if 0 <= idx < len(self._shots):
                    self._hovered_index = idx
                else:
                    self._hovered_index = None
            else:
                self._hovered_index = 0
        else:
            self._hovered_index = None

        self.update()

    def leaveEvent(self, event):
        self._hovered_index = None
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        zoom_factor = 1.15 if delta > 0 else (1.0 / 1.15)
        new_zoom = max(1.0, min(5.0, self._zoom * zoom_factor))

        if new_zoom != self._zoom:
            mouse_x = event.position().x()
            self._pan_offset = mouse_x - (mouse_x - self._pan_offset) * (new_zoom / self._zoom)
            self._zoom = new_zoom
            if self._zoom == 1.0:
                self._pan_offset = 0.0
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        left_margin = 55.0
        right_margin = 25.0
        top_margin = 20.0
        bottom_margin = 35.0

        chart_w = w - left_margin - right_margin
        chart_h = h - top_margin - bottom_margin

        # Theme Colors
        bg_color = QColor("#12161E") if self._dark_mode else QColor("#F8F9FA")
        grid_color = QColor(255, 255, 255, 15) if self._dark_mode else QColor(0, 0, 0, 15)
        text_color = QColor("#8B949E") if self._dark_mode else QColor("#656D76")
        accent_color = QColor("#88FF11") if self._dark_mode else QColor("#2E7D32")
        avg_line_color = QColor("#FF9800")

        # Background card fill
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(0, 0, w, h, 8, 8)

        if not self._shots:
            painter.setPen(text_color)
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "No shots recorded yet")
            return

        velocities = [s.velocity for s in self._shots]
        min_v = min(velocities)
        max_v = max(velocities)
        range_v = max(1.0, max_v - min_v)
        display_min = max(0.0, min_v - range_v * 0.25)
        display_max = max_v + range_v * 0.25
        display_range = max(0.1, display_max - display_min)
        avg_v = sum(velocities) / len(velocities)

        # Clip chart area for pan & zoom
        clip_rect = QRectF(left_margin, top_margin, chart_w, chart_h)
        painter.setClipRect(clip_rect)

        total_w = chart_w * self._zoom
        x_step = total_w / max(1, len(self._shots) - 1) if len(self._shots) > 1 else total_w / 2.0

        # Draw Grid lines inside chart
        painter.setPen(QPen(grid_color, 1))
        for step_frac in [0.25, 0.5, 0.75, 1.0]:
            y_line = top_margin + chart_h * (1.0 - step_frac)
            painter.drawLine(QPointF(left_margin, y_line), QPointF(left_margin + chart_w, y_line))

        # Draw Average Line (Orange Dashed)
        avg_y = top_margin + chart_h - ((avg_v - display_min) / display_range) * chart_h
        avg_pen = QPen(avg_line_color, 1.2, Qt.DashLine)
        painter.setPen(avg_pen)
        painter.drawLine(QPointF(left_margin, avg_y), QPointF(left_margin + chart_w, avg_y))

        # Build Points
        points: List[QPointF] = []
        for i, s in enumerate(self._shots):
            x = left_margin + self._pan_offset + (i * x_step if len(self._shots) > 1 else chart_w / 2.0)
            norm_y = (s.velocity - display_min) / display_range
            y = top_margin + chart_h - (norm_y * chart_h)
            points.append(QPointF(x, y))

        # Gradient fill under curve
        if len(points) > 1:
            fill_path = QPainterPath()
            fill_path.moveTo(points[0].x(), top_margin + chart_h)
            fill_path.lineTo(points[0].x(), points[0].y())
            for pt in points[1:]:
                fill_path.lineTo(pt.x(), pt.y())
            fill_path.lineTo(points[-1].x(), top_margin + chart_h)
            fill_path.closeSubpath()

            grad = QLinearGradient(0, top_margin, 0, top_margin + chart_h)
            grad.setColorAt(0, QColor(136, 255, 17, 70) if self._dark_mode else QColor(46, 125, 50, 60))
            grad.setColorAt(1, QColor(136, 255, 17, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(grad)
            painter.drawPath(fill_path)

            # Trend line
            line_pen = QPen(accent_color, 2.2)
            painter.setPen(line_pen)
            line_path = QPainterPath()
            line_path.moveTo(points[0])
            for pt in points[1:]:
                line_path.lineTo(pt)
            painter.drawPath(line_path)

        # Draw Points
        for i, pt in enumerate(points):
            is_hovered = (self._hovered_index == i)
            radius = 5.0 if is_hovered else 3.0
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#FFFFFF") if is_hovered else accent_color)
            painter.drawEllipse(pt, radius, radius)

        # Unclip for axes and tooltips
        painter.setClipping(False)

        # Draw Axis Labels
        painter.setFont(QFont("Consolas, Courier New", 9))
        painter.setPen(text_color)
        painter.drawText(QRectF(left_margin - 50, top_margin - 5, 45, 15), Qt.AlignRight, f"{display_max:.1f}")
        painter.drawText(QRectF(left_margin - 50, top_margin + chart_h - 10, 45, 15), Qt.AlignRight, f"{display_min:.1f}")
        painter.drawText(QRectF(left_margin - 50, avg_y - 7, 45, 15), Qt.AlignRight, f"AVG")

        # X-Axis Bottom Text
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(QRectF(left_margin, h - bottom_margin + 8, chart_w, 20), Qt.AlignCenter, "SHOT #")

        # Hover Tooltip Card
        if self._hovered_index is not None and 0 <= self._hovered_index < len(self._shots):
            shot = self._shots[self._hovered_index]
            pt = points[self._hovered_index]

            card_w = 140.0
            card_h = 56.0
            card_x = max(left_margin, min(w - right_margin - card_w, pt.x() - card_w / 2.0))
            card_y = top_margin + 8.0

            # Card background
            card_bg = QColor("#0B0E14") if self._dark_mode else QColor("#FFFFFF")
            card_border = accent_color
            painter.setPen(QPen(card_border, 1.2))
            painter.setBrush(card_bg)
            painter.drawRoundedRect(QRectF(card_x, card_y, card_w, card_h), 6, 6)

            # Tooltip Text
            painter.setPen(accent_color)
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(QRectF(card_x + 8, card_y + 4, card_w - 16, 16), Qt.AlignLeft, f"Shot #{self._hovered_index + 1}")

            painter.setPen(QColor("#FFFFFF") if self._dark_mode else QColor("#000000"))
            painter.setFont(QFont("Consolas, Courier New", 12, QFont.Bold))
            painter.drawText(QRectF(card_x + 8, card_y + 19, card_w - 16, 18), Qt.AlignLeft, f"{shot.velocity:.2f} m/s")

            painter.setPen(text_color)
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(QRectF(card_x + 8, card_y + 37, card_w - 16, 15), Qt.AlignLeft, f"{shot.energy_joules:.2f} J  ({shot.weight_grams:.2f}g)")
