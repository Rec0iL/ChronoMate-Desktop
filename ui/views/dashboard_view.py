"""
ChronoMate Desktop - Dashboard View
Main telemetry hub: Quick weight chips, Hero readout, Stats Grid, and Shot Chart.
"""

from typing import List, Tuple
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.models import Shot, WeightType, STANDARD_BB_WEIGHTS, STANDARD_DIABLO_WEIGHTS
from core.config import ConfigManager
from core.session_manager import SessionManager
from core.i18n import tr
from ui.components.hero_card import HeroCard
from ui.components.stats_grid import StatsGrid
from ui.components.shot_chart import ShotChart


class DashboardView(QWidget):
    weight_changed = Signal(float)

    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self._dark_mode = dark_mode
        self._cfg = ConfigManager.get_instance()
        self._sm = SessionManager.get_instance()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Title & Subtitle
        header_row = QHBoxLayout()
        self.lbl_title = QLabel("HT-X3000 Shot Chronograph")
        self.lbl_title.setObjectName("section_title")
        header_row.addWidget(self.lbl_title)
        header_row.addStretch()
        main_layout.addLayout(header_row)

        # Weight Selection Chips
        self.weight_container = QHBoxLayout()
        self.weight_container.setSpacing(6)
        self._weight_chips: List[QPushButton] = []
        main_layout.addLayout(self.weight_container)
        self.rebuild_weight_chips()

        # Telemetry Row (HeroCard + StatsGrid)
        telemetry_row = QHBoxLayout()
        telemetry_row.setSpacing(14)

        self.hero_card = HeroCard(dark_mode=dark_mode, parent=self)
        self.hero_card.setMinimumWidth(240)
        self.stats_grid = StatsGrid(parent=self)

        telemetry_row.addWidget(self.hero_card, stretch=2)
        telemetry_row.addWidget(self.stats_grid, stretch=3)
        main_layout.addLayout(telemetry_row)

        # Trend Chart Header
        chart_header = QHBoxLayout()
        self.lbl_trend = QLabel(tr("velocity_trend"))
        self.lbl_trend.setObjectName("section_title")
        chart_header.addWidget(self.lbl_trend)

        chart_header.addStretch()
        self.btn_reset_zoom = QPushButton("Reset Zoom")
        self.btn_reset_zoom.setFixedHeight(26)
        self.btn_reset_zoom.clicked.connect(self._reset_chart_zoom)
        chart_header.addWidget(self.btn_reset_zoom)
        main_layout.addLayout(chart_header)

        # Interactive Shot Chart
        self.shot_chart = ShotChart(dark_mode=dark_mode, parent=self)
        main_layout.addWidget(self.shot_chart, stretch=1)

    def _reset_chart_zoom(self):
        self.shot_chart.reset_view()

    def rebuild_weight_chips(self):
        # Cleanly clear all widgets and spacer items
        while self.weight_container.count():
            item = self.weight_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._weight_chips.clear()

        # Collect available weights based on active weight category
        weights_data: List[Tuple[float, str]] = []
        if self._cfg.weight_type == WeightType.BB:
            weights_data = [(w, f"{w:.2f}g") for w in STANDARD_BB_WEIGHTS]
        elif self._cfg.weight_type == WeightType.DIABLO:
            weights_data = [(w, f"{w:.2f}g") for w in STANDARD_DIABLO_WEIGHTS]
        else:
            weights_data = [(cw.weight, f"{cw.name} {cw.weight:.2f}g") for cw in self._cfg.custom_weights]
            if not weights_data:
                weights_data = [(0.20, "0.20g")]

        for weight, label in weights_data:
            chip = QPushButton(label)
            chip.setObjectName("chip_btn")
            chip.setCheckable(True)
            chip.setProperty("weight", weight)
            chip.setChecked(abs(weight - self._cfg.selected_weight) < 0.001)
            chip.clicked.connect(lambda checked, w=weight: self._on_chip_clicked(w))
            self.weight_container.addWidget(chip)
            self._weight_chips.append(chip)

        self.weight_container.addStretch()

    def _on_chip_clicked(self, weight: float):
        self._cfg.selected_weight = weight
        self._cfg.save()
        self.set_active_weight(weight)
        self.weight_changed.emit(weight)

    def set_active_weight(self, weight: float):
        for chip in self._weight_chips:
            w_val = chip.property("weight")
            if w_val is not None:
                chip.setChecked(abs(float(w_val) - weight) < 0.001)
        self.refresh_stats()

    def refresh_stats(self):
        shots = self._sm.active_session.shots
        self.shot_chart.set_shots(shots)

        if shots:
            latest = shots[-1]
            self.hero_card.update_telemetry(latest.velocity, latest.energy_joules)

            vels = [s.velocity for s in shots]
            avg_v = sum(vels) / len(vels)
            max_v = max(vels)
            min_v = min(vels)
            es = max_v - min_v

            mean = avg_v
            var_val = sum((v - mean) ** 2 for v in vels) / len(vels) if len(vels) > 1 else 0.0
            sd = var_val ** 0.5

            self.stats_grid.update_stats(avg_v, max_v, min_v, es, sd, "0.0")
        else:
            self.hero_card.update_telemetry(0.0, 0.0)
            self.stats_grid.update_stats(0.0, 0.0, 0.0, 0.0, 0.0, "0.0")

    def set_theme(self, dark_mode: bool):
        self._dark_mode = dark_mode
        self.hero_card.set_theme(dark_mode)
        self.shot_chart.set_theme(dark_mode)

    def retranslate(self):
        self.lbl_title.setText(f"{self._cfg.chrono_type.display_name} Shot Chronograph")
        self.lbl_trend.setText(tr("velocity_trend"))
        self.stats_grid.retranslate()
        self.rebuild_weight_chips()
