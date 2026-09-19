"""
ChronoMate Desktop - Trajectory Simulation Canvas
Custom QPainter widget rendering the 2D side-view ballistic flight path,
line-of-sight aim line, target vertical plane, and interactive mouse probe.
"""

from typing import List, Optional, Callable
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QMouseEvent
from core.models import TrajectoryPoint, ProbeResult


class TrajectoryCanvas(QWidget):
    probe_updated = Signal(object)  # Emits ProbeResult or None

    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(240)
        self._dark_mode = dark_mode

        self._trajectory: List[TrajectoryPoint] = []
        self._target_distance: float = 50.0
        self._eye_height_m: float = 1.55
        self._target_height_m: float = 1.50
        self._probe_x: Optional[float] = None
        self._pinned_probe: bool = False

    def update_data(
        self,
        trajectory: List[TrajectoryPoint],
        target_distance: float,
        eye_height_m: float,
        target_height_m: float,
    ):
        self._trajectory = trajectory
        self._target_distance = target_distance
        self._eye_height_m = eye_height_m
        self._target_height_m = target_height_m
        self.update()

    def set_theme(self, dark_mode: bool):
        self._dark_mode = dark_mode
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            self._pinned_probe = False
            self._probe_x = None
            self.probe_updated.emit(None)
            self.update()
            return

        if event.button() == Qt.LeftButton:
            self._pinned_probe = not self._pinned_probe
            self._update_probe_from_mouse(event.position().x())

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self._pinned_probe:
            self._update_probe_from_mouse(event.position().x())

    def leaveEvent(self, event):
        if not self._pinned_probe:
            self._probe_x = None
            self.probe_updated.emit(None)
            self.update()

    def _update_probe_from_mouse(self, mouse_x: float):
        if not self._trajectory:
            return

        left_m = 50.0
        right_m = 25.0
        chart_w = self.width() - left_m - right_m
        if chart_w <= 0:
            return

        max_x = max(1.0, max(p.x for p in self._trajectory))
        rel_x = mouse_x - left_m
        if 0 <= rel_x <= chart_w:
            x_val = (rel_x / chart_w) * max_x
            self._probe_x = x_val

            # Find closest trajectory point
            pt = min(self._trajectory, key=lambda p: abs(p.x - x_val))
            aim_line_y = self._eye_height_m + (pt.x / max(self._target_distance, 0.001)) * (self._target_height_m - self._eye_height_m)

            result = ProbeResult(
                distance=pt.x,
                bb_height_cm=pt.y * 100.0,
                energy_j=pt.energy_joules,
                time_s=pt.time,
                relative_impact_cm=(pt.y - aim_line_y) * 100.0,
                hold_over_cm=(self._target_height_m - pt.y) * 100.0,
            )
            self.probe_updated.emit(result)
        else:
            self._probe_x = None
            self.probe_updated.emit(None)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        left_m = 55.0
        right_m = 25.0
        top_m = 25.0
        bottom_m = 35.0

        chart_w = w - left_m - right_m
        chart_h = h - top_m - bottom_m

        bg_color = QColor("#0E1117") if self._dark_mode else QColor("#FFFFFF")
        grid_color = QColor(255, 255, 255, 18) if self._dark_mode else QColor(0, 0, 0, 20)
        text_color = QColor("#8B949E") if self._dark_mode else QColor("#656D76")
        accent_color = QColor("#88FF11") if self._dark_mode else QColor("#2E7D32")
        aim_color = QColor("#FFD600") if self._dark_mode else QColor("#E65100")
        target_marker_color = QColor("#F44336")

        painter.setPen(Qt.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(0, 0, w, h, 8, 8)

        if not self._trajectory:
            painter.setPen(text_color)
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "No trajectory calculated")
            return

        max_x = max(1.0, max(p.x for p in self._trajectory))
        max_y = max(2.0, max(p.y for p in self._trajectory))
        range_y = max_y

        # Draw Distance Grid (X-axis meters)
        painter.setFont(QFont("Consolas, Courier New", 9))
        x_step = 10.0 if max_x <= 70 else 20.0
        cur_x = 0.0
        while cur_x <= max_x:
            x_pos = left_m + (cur_x / max_x) * chart_w
            painter.setPen(QPen(grid_color, 1))
            painter.drawLine(QPointF(x_pos, top_m), QPointF(x_pos, top_m + chart_h))

            painter.setPen(text_color)
            painter.drawText(QRectF(x_pos - 20, top_m + chart_h + 8, 40, 16), Qt.AlignCenter, f"{cur_x:.0f}m")
            cur_x += x_step

        # Draw Height Grid (Y-axis cm)
        y_step = 0.5  # 50cm
        cur_y = 0.0
        while cur_y <= max_y:
            y_pos = top_m + chart_h - (cur_y / range_y) * chart_h
            painter.setPen(QPen(grid_color, 1))
            painter.drawLine(QPointF(left_m, y_pos), QPointF(left_m + chart_w, y_pos))

            painter.setPen(text_color)
            painter.drawText(QRectF(left_m - 48, y_pos - 7, 42, 14), Qt.AlignRight, f"{cur_y * 100:.0f}cm")
            cur_y += y_step

        # Ground line
        painter.setPen(QPen(grid_color, 1.5))
        painter.drawLine(QPointF(left_m, top_m + chart_h), QPointF(left_m + chart_w, top_m + chart_h))

        # Aim Line (Line of Sight)
        aim_x1 = left_m
        aim_y1 = top_m + chart_h - (self._eye_height_m / range_y) * chart_h
        aim_x2 = left_m + (min(self._target_distance, max_x) / max_x) * chart_w
        aim_y2 = top_m + chart_h - (self._target_height_m / range_y) * chart_h

        aim_pen = QPen(aim_color, 1.2, Qt.DashLine)
        painter.setPen(aim_pen)
        painter.drawLine(QPointF(aim_x1, aim_y1), QPointF(aim_x2, aim_y2))

        # Trajectory Path
        path = QPainterPath()
        points: List[QPointF] = []
        for i, pt in enumerate(self._trajectory):
            px = left_m + (pt.x / max_x) * chart_w
            py = top_m + chart_h - (pt.y / range_y) * chart_h
            points.append(QPointF(px, py))
            if i == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)

        painter.setPen(QPen(accent_color, 2.4))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        # Target Distance Marker Line
        target_x_px = left_m + (min(self._target_distance, max_x) / max_x) * chart_w
        target_y_px = top_m + chart_h - (self._target_height_m / range_y) * chart_h

        target_pen = QPen(QColor(244, 67, 54, 120), 1.2, Qt.DotLine)
        painter.setPen(target_pen)
        painter.drawLine(QPointF(target_x_px, top_m), QPointF(target_x_px, top_m + chart_h))

        # Red crosshair marker at target
        painter.setPen(QPen(target_marker_color, 2.5))
        painter.drawLine(QPointF(target_x_px - 6, target_y_px), QPointF(target_x_px + 6, target_y_px))

        # Interactive Probe Marker
        if self._probe_x is not None:
            px = left_m + (self._probe_x / max_x) * chart_w
            probe_pt = min(self._trajectory, key=lambda p: abs(p.x - self._probe_x))
            py = top_m + chart_h - (probe_pt.y / range_y) * chart_h

            probe_line_color = QColor("#00E5FF") if self._dark_mode else QColor("#00838F")
            painter.setPen(QPen(probe_line_color, 1.2, Qt.DashLine))
            painter.drawLine(QPointF(px, top_m), QPointF(px, top_m + chart_h))

            # Circle marker on curve
            painter.setPen(Qt.NoPen)
            painter.setBrush(probe_line_color)
            painter.drawEllipse(QPointF(px, py), 5.0, 5.0)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(QPointF(px, py), 2.0, 2.0)
