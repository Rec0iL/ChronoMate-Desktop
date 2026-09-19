"""
ChronoMate Desktop - Stats Grid Component
Displays Average, Max, Min, Extreme Spread, Standard Deviation, and Rate of Fire.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from core.i18n import tr


class StatItemWidget(QFrame):
    def __init__(self, label: str, value: str = "--", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        self.lbl_title = QLabel(label)
        self.lbl_title.setObjectName("label_secondary")
        self.lbl_title.setAlignment(Qt.AlignCenter)

        self.lbl_value = QLabel(value)
        val_font = QFont("Consolas, Courier New, monospace", 16, QFont.Bold)
        self.lbl_value.setFont(val_font)
        self.lbl_value.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)

    def set_value(self, value: str):
        self.lbl_value.setText(value)

    def set_label(self, label: str):
        self.lbl_title.setText(label)


class StatsGrid(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(6)

        self.item_avg = StatItemWidget(tr("stat_average"))
        self.item_max = StatItemWidget(tr("stat_max"))
        self.item_min = StatItemWidget(tr("stat_min"))
        self.item_es = StatItemWidget(tr("stat_es"))
        self.item_sd = StatItemWidget(tr("stat_sd"))
        self.item_rof = StatItemWidget(tr("stat_rof"))

        grid.addWidget(self.item_avg, 0, 0)
        grid.addWidget(self.item_max, 0, 1)
        grid.addWidget(self.item_min, 0, 2)
        grid.addWidget(self.item_es, 1, 0)
        grid.addWidget(self.item_sd, 1, 1)
        grid.addWidget(self.item_rof, 1, 2)

        main_layout.addLayout(grid)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_font_size()

    def _adjust_font_size(self):
        w = self.width()
        font_px = 15 if w >= 460 else (13 if w >= 360 else 11)
        font_title_px = 11 if w >= 460 else 10
        for item in [self.item_avg, self.item_max, self.item_min, self.item_es, self.item_sd, self.item_rof]:
            item.lbl_value.setStyleSheet(f"font-size: {font_px}px; font-weight: 700; font-family: Consolas, monospace;")
            item.lbl_title.setStyleSheet(f"font-size: {font_title_px}px;")

    def update_stats(self, avg: float, max_v: float, min_v: float, es: float, sd: float, rof: str):
        self.item_avg.set_value(f"{avg:.1f} m/s" if avg > 0 else "--")
        self.item_max.set_value(f"{max_v:.1f} m/s" if max_v > 0 else "--")
        self.item_min.set_value(f"{min_v:.1f} m/s" if min_v > 0 else "--")
        self.item_es.set_value(f"{es:.1f} m/s" if es > 0 else "--")
        self.item_sd.set_value(f"{sd:.2f} m/s" if sd > 0 else "--")
        self.item_rof.set_value(f"{rof} r/m" if rof and rof != "0.0" else "--")

    def retranslate(self):
        self.item_avg.set_label(tr("stat_average"))
        self.item_max.set_label(tr("stat_max"))
        self.item_min.set_label(tr("stat_min"))
        self.item_es.set_label(tr("stat_es"))
        self.item_sd.set_label(tr("stat_sd"))
        self.item_rof.set_label(tr("stat_rof"))
