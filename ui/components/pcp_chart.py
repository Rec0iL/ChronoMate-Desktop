"""
ChronoMate Desktop - PCP trajectory chart
Pellet path relative to the line of sight (the scope's cross-hair = 0 cm), with the kill zone band,
zero markers and a hover / click probe.
"""

import math
from typing import List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from core.pcp_ballistics import PcpPoint, PcpResult


def _nice_step(span: float, target_ticks: int = 6) -> float:
    raw = span / max(1, target_ticks)
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


class PcpChart(QWidget):
    probe_changed = Signal(object)   # PcpPoint or None

    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(260)
        self._dark = dark_mode
        self._result: Optional[PcpResult] = None
        self._max_range = 100.0
        self._kill_zone_cm = 3.0
        self._probe: Optional[PcpPoint] = None
        self._pinned = False

    def set_theme(self, dark: bool):
        self._dark = dark
        self.update()

    def set_result(self, result: PcpResult, max_range: float, kill_zone_cm: float):
        self._result = result
        self._max_range = max(5.0, max_range)
        self._kill_zone_cm = kill_zone_cm
        if self._probe is not None:
            self._probe = result.point_at(self._probe.range_m) if result else None
            self.probe_changed.emit(self._probe)
        self.update()

    # --- geometry -------------------------------------------------------------------------------
    def _plot_rect(self) -> QRectF:
        return QRectF(58, 14, max(10, self.width() - 72), max(10, self.height() - 46))

    def _y_range(self):
        pts = self._result.points if self._result else []
        drops = [p.drop_cm for p in pts if p.range_m <= self._max_range]
        lo = min(drops + [-self._kill_zone_cm])
        hi = max(drops + [self._kill_zone_cm])
        pad = max(1.0, (hi - lo) * 0.08)
        return lo - pad, hi + pad

    def _map(self, rect: QRectF, x: float, y: float, y_lo: float, y_hi: float) -> QPointF:
        px = rect.left() + x / self._max_range * rect.width()
        py = rect.bottom() - (y - y_lo) / (y_hi - y_lo) * rect.height()
        return QPointF(px, py)

    # --- events ---------------------------------------------------------------------------------
    def mouseMoveEvent(self, e):
        if not self._pinned:
            self._probe_at(e.position().x())

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self._pinned = False
            self._probe = None
            self.probe_changed.emit(None)
            self.update()
            return
        self._pinned = not self._pinned
        self._probe_at(e.position().x())

    def leaveEvent(self, e):
        if not self._pinned:
            self._probe = None
            self.probe_changed.emit(None)
            self.update()

    def _probe_at(self, px: float):
        if not self._result or not self._result.points:
            return
        rect = self._plot_rect()
        x = (px - rect.left()) / rect.width() * self._max_range
        x = max(0.0, min(self._max_range, x))
        self._probe = self._result.point_at(x)
        self.probe_changed.emit(self._probe)
        self.update()

    # --- painting -------------------------------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        dark = self._dark
        bg = QColor("#0B0E14") if dark else QColor("#FFFFFF")
        grid = QColor(255, 255, 255, 22) if dark else QColor(0, 0, 0, 22)
        text = QColor("#8B949E") if dark else QColor("#57606A")
        accent = QColor("#88FF11") if dark else QColor("#2E7D32")
        cyan = QColor("#00E5FF") if dark else QColor("#00838F")
        p.fillRect(self.rect(), bg)

        rect = self._plot_rect()
        if not self._result or not self._result.points:
            p.setPen(text)
            p.drawText(rect, Qt.AlignCenter, "—")
            return
        y_lo, y_hi = self._y_range()

        # Grid + axis labels
        p.setFont(QFont("Consolas, Courier New", 8))
        x_step = _nice_step(self._max_range, 10)
        x = 0.0
        while x <= self._max_range + 1e-6:
            pt = self._map(rect, x, 0, y_lo, y_hi)
            p.setPen(QPen(grid, 1))
            p.drawLine(QPointF(pt.x(), rect.top()), QPointF(pt.x(), rect.bottom()))
            p.setPen(text)
            p.drawText(QRectF(pt.x() - 20, rect.bottom() + 4, 40, 14), Qt.AlignCenter, f"{x:.0f}")
            x += x_step
        y_step = _nice_step(y_hi - y_lo, 6)
        y = math.ceil(y_lo / y_step) * y_step
        while y <= y_hi:
            pt = self._map(rect, 0, y, y_lo, y_hi)
            p.setPen(QPen(grid, 1))
            p.drawLine(QPointF(rect.left(), pt.y()), QPointF(rect.right(), pt.y()))
            p.setPen(text)
            p.drawText(QRectF(4, pt.y() - 7, rect.left() - 8, 14), Qt.AlignRight | Qt.AlignVCenter, f"{y:+.0f}")
            y += y_step
        p.drawText(QRectF(rect.left(), rect.bottom() + 18, rect.width(), 14), Qt.AlignCenter, "m")
        p.drawText(QRectF(4, rect.top() - 12, 50, 12), Qt.AlignRight, "cm")

        # Kill zone band around the line of sight
        top = self._map(rect, 0, self._kill_zone_cm / 2, y_lo, y_hi).y()
        bot = self._map(rect, 0, -self._kill_zone_cm / 2, y_lo, y_hi).y()
        band = QColor(cyan)
        band.setAlpha(28)
        p.fillRect(QRectF(rect.left(), top, rect.width(), bot - top), band)

        # Line of sight
        los = self._map(rect, 0, 0, y_lo, y_hi).y()
        p.setPen(QPen(cyan, 1.2, Qt.DashLine))
        p.drawLine(QPointF(rect.left(), los), QPointF(rect.right(), los))

        # Pellet path
        path = QPainterPath()
        first = True
        for pt in self._result.points:
            if pt.range_m > self._max_range:
                break
            q = self._map(rect, pt.range_m, pt.drop_cm, y_lo, y_hi)
            if first:
                path.moveTo(q)
                first = False
            else:
                path.lineTo(q)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(accent, 2.2))
        p.drawPath(path)

        # Zero markers
        for z in (self._result.near_zero_m, self._result.far_zero_m):
            if z is not None and z <= self._max_range:
                q = self._map(rect, z, 0, y_lo, y_hi)
                p.setPen(QPen(cyan, 1.5))
                p.setBrush(bg)
                p.drawEllipse(q, 4, 4)

        # Probe
        if self._probe is not None:
            q = self._map(rect, self._probe.range_m, self._probe.drop_cm, y_lo, y_hi)
            p.setPen(QPen(QColor("#FFB74D"), 1, Qt.DotLine))
            p.drawLine(QPointF(q.x(), rect.top()), QPointF(q.x(), rect.bottom()))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#FFB74D"))
            p.drawEllipse(q, 5, 5)
        p.end()
