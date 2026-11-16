"""
ChronoMate Desktop - Ballistics & Trajectory Simulation View
Side-by-side flight path & target reticle, interactive telemetry probing,
live parameter sliders, and one-click Hop-Up Optimizer.
"""

import math
from typing import List, Tuple, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QSlider,
    QDoubleSpinBox,
    QPushButton,
    QScrollArea,
    QFrame,
    QSplitter,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from core.models import BallisticParams, TrajectoryPoint, ProbeResult, WeightType, STANDARD_BB_WEIGHTS, STANDARD_DIABLO_WEIGHTS
from core.ballistics import BallisticsEngine
from core.config import ConfigManager
from core.session_manager import SessionManager
from core.i18n import tr
from ui.components.trajectory_canvas import TrajectoryCanvas
from ui.components.target_canvas import TargetCanvas
from ui.components.weight_chips import WeightChipBar
from ui.components.environment_card import EnvironmentCard
from ui.components.responsive import ResponsiveGrid, ResponsiveRow


class BallisticsView(QWidget):
    weight_changed = Signal(float)

    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self._dark_mode = dark_mode
        self._cfg = ConfigManager.get_instance()
        self._sm = SessionManager.get_instance()
        self._engine = BallisticsEngine()

        # State Variables
        self._speed_mps: float = 100.0
        self._hop_up_rad_s: float = 1000.0
        self._target_distance_m: float = 50.0
        self._shooter_height_m: float = 1.50
        self._target_height_m: float = 1.50
        self._sight_height_cm: float = 5.0
        self._couple_heights: bool = True

        self._trajectory: List[TrajectoryPoint] = []

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)   # the page fits the window

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Title
        self.lbl_title = QLabel(tr("trajectory_sim"))
        self.lbl_title.setObjectName("page_title")
        layout.addWidget(self.lbl_title)

        # Side view and target view: side by side when wide, stacked on narrow windows
        self.canvas_splitter = ResponsiveRow(threshold=860)

        self.trajectory_canvas = TrajectoryCanvas(dark_mode=dark_mode, parent=self)
        self.trajectory_canvas.probe_updated.connect(self._on_probe_updated)
        self.target_canvas = TargetCanvas(dark_mode=dark_mode, parent=self)

        self.trajectory_canvas.setMinimumHeight(300)
        self.target_canvas.setMinimumHeight(300)
        self.canvas_splitter.add_widget(self.trajectory_canvas, 3)
        self.canvas_splitter.add_widget(self.target_canvas, 2)
        layout.addWidget(self.canvas_splitter)

        # Probe Readout Banner
        self.probe_card = QFrame()
        self.probe_card.setObjectName("card")
        # Always shown (with a hint until you hover), so probing never pushes the page around
        self.probe_layout = QHBoxLayout(self.probe_card)
        self.probe_layout.setContentsMargins(14, 8, 14, 8)
        self.lbl_probe_info = QLabel(tr("bb_probe_hint"))
        self.lbl_probe_info.setFont(QFont("Consolas, Courier New", 10, QFont.Bold))
        self.lbl_probe_info.setWordWrap(True)
        self.probe_layout.addWidget(self.lbl_probe_info)
        layout.addWidget(self.probe_card)

        # Telemetry Stats Ribbon Card
        stats_ribbon = QFrame()
        stats_ribbon.setObjectName("card")
        ribbon_outer = QVBoxLayout(stats_ribbon)
        ribbon_outer.setContentsMargins(14, 10, 14, 10)
        ribbon_grid = ResponsiveGrid(min_col_width=120, max_cols=7, min_cols=2, spacing=10)
        ribbon_outer.addWidget(ribbon_grid)

        self.lbl_eff_range = QLabel("--")
        self.lbl_max_range = QLabel("--")
        self.lbl_holdover = QLabel("--")
        self.lbl_target_energy = QLabel("--")
        self.lbl_max_overhop = QLabel("--")
        self.lbl_overhop_dist = QLabel("--")
        self.lbl_drift = QLabel("--")

        items = [
            ("stat_eff_range", self.lbl_eff_range),
            ("stat_max_range", self.lbl_max_range),
            ("stat_hold_over", self.lbl_holdover),
            ("stat_target_e", self.lbl_target_energy),
            ("stat_max_oh", self.lbl_max_overhop),
            ("stat_oh_dist", self.lbl_overhop_dist),
            ("stat_wind_drift", self.lbl_drift),
        ]

        self._ribbon_headers = []
        for idx, (key, val_lbl) in enumerate(items):
            cell = QWidget()
            col_box = QVBoxLayout(cell)
            col_box.setContentsMargins(0, 0, 0, 0)
            col_box.setSpacing(2)
            lbl_hdr = QLabel(tr(key))
            self._ribbon_headers.append((key, lbl_hdr))
            lbl_hdr.setObjectName("label_secondary")
            val_lbl.setFont(QFont("Consolas, Courier New", 12, QFont.Bold))
            col_box.addWidget(lbl_hdr)
            col_box.addWidget(val_lbl)
            ribbon_grid.add_widget(cell)

        layout.addWidget(stats_ribbon)

        # Controls Section
        ctrl_frame = QFrame()
        ctrl_frame.setObjectName("card")
        ctrl_layout = QVBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(16, 14, 16, 14)
        ctrl_layout.setSpacing(12)

        # Weight Chips Row (loaded weights, then custom weights when enabled)
        self.weight_bar = WeightChipBar(self)
        self.weight_bar.weight_clicked.connect(self._set_weight)
        ctrl_layout.addWidget(self.weight_bar)

        # Sliders Grid (Distance, Heights, Velocity, Energy, Hop-Up, Sight)
        sliders_grid = QGridLayout()
        sliders_grid.setSpacing(14)

        # Row 1: Target Distance
        self.lbl_dist_slider = QLabel(tr("target_distance_label", self._target_distance_m))
        self.lbl_dist_slider.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.slider_dist = QSlider(Qt.Horizontal)
        self.slider_dist.setRange(5, 100)
        self.slider_dist.setValue(int(self._target_distance_m))
        self.slider_dist.valueChanged.connect(self._on_dist_changed)

        sliders_grid.addWidget(self.lbl_dist_slider, 0, 0)
        sliders_grid.addWidget(self.slider_dist, 0, 1)

        # Row 2: Velocity & Energy Interlocked
        self.lbl_speed_slider = QLabel(tr("speed_label", self._speed_mps))
        self.lbl_speed_slider.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(50, 200)
        self.slider_speed.setValue(int(self._speed_mps))
        self.slider_speed.valueChanged.connect(self._on_speed_changed)

        sliders_grid.addWidget(self.lbl_speed_slider, 1, 0)
        sliders_grid.addWidget(self.slider_speed, 1, 1)

        # Row 3: Hop-Up
        self.lbl_hop_slider = QLabel(tr("hopup_label", self._hop_up_rad_s))
        self.lbl_hop_slider.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.slider_hop = QSlider(Qt.Horizontal)
        self.slider_hop.setRange(0, 2000)
        self.slider_hop.setValue(int(self._hop_up_rad_s))
        self.slider_hop.valueChanged.connect(self._on_hop_changed)

        sliders_grid.addWidget(self.lbl_hop_slider, 2, 0)
        sliders_grid.addWidget(self.slider_hop, 2, 1)

        ctrl_layout.addLayout(sliders_grid)

        # Overhop Limit & Optimize Button Row
        opt_row = QHBoxLayout()
        opt_row.setSpacing(12)

        self.lbl_max_oh_limit = QLabel(tr("max_overhop", self._cfg.max_allowed_overhop_cm))
        self.lbl_max_oh_limit.setFont(QFont("Segoe UI", 10, QFont.Bold))
        opt_row.addWidget(self.lbl_max_oh_limit)

        self.spin_overhop = QDoubleSpinBox()
        self.spin_overhop.setRange(1.0, 50.0)
        self.spin_overhop.setValue(self._cfg.max_allowed_overhop_cm)
        self.spin_overhop.setSuffix(" cm")
        self.spin_overhop.valueChanged.connect(self._on_overhop_limit_changed)
        opt_row.addWidget(self.spin_overhop)

        self.btn_optimize = QPushButton(f"★ {tr('optimize_hopup')}")
        self.btn_optimize.setObjectName("primary_btn")
        self.btn_optimize.setFixedHeight(36)
        self.btn_optimize.clicked.connect(self._optimize_hopup)
        opt_row.addWidget(self.btn_optimize)

        ctrl_layout.addLayout(opt_row)
        layout.addWidget(ctrl_frame)

        # Weather & wind (shared with the PCP calculator): air density and crosswind drift
        self.env_card = EnvironmentCard(self)
        self.env_card.changed.connect(self.recalculate)
        layout.addWidget(self.env_card)

        # GWC Leipzig Attribution
        self.lbl_attr = QLabel(tr("powered_by"))
        self.lbl_attr.setObjectName("label_secondary")
        self.lbl_attr.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_attr)

        layout.addStretch()
        scroll.setWidget(container)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroll)

        self.recalculate()

    @property
    def _weight_chips(self) -> List[QPushButton]:
        return self.weight_bar.chips()

    def rebuild_weight_chips(self):
        self.weight_bar.rebuild()

    def _set_weight(self, weight: float):
        self._cfg.selected_weight = weight
        self._cfg.save()
        self.set_active_weight(weight)
        self.weight_changed.emit(weight)

    def set_active_weight(self, weight: float):
        self.weight_bar.set_active(weight)
        self.recalculate()

    def _on_dist_changed(self, val: int):
        self._target_distance_m = float(val)
        self.lbl_dist_slider.setText(tr("target_distance_label", self._target_distance_m))
        self.recalculate()

    def _on_speed_changed(self, val: int):
        self._speed_mps = float(val)
        self.lbl_speed_slider.setText(tr("speed_label", self._speed_mps))
        self.recalculate()

    def _on_hop_changed(self, val: int):
        self._hop_up_rad_s = float(val)
        self.lbl_hop_slider.setText(tr("hopup_label", self._hop_up_rad_s))
        self.recalculate()

    def _on_overhop_limit_changed(self, val: float):
        self._cfg.max_allowed_overhop_cm = val
        self._cfg.save()
        self.lbl_max_oh_limit.setText(tr("max_overhop", val))

    def _optimize_hopup(self):
        """Immediately switches all values to optimal hop."""
        eye_height_m = self._shooter_height_m + (self._sight_height_cm / 100.0)
        aim_angle_deg = math.degrees(math.atan2(self._target_height_m - eye_height_m, self._target_distance_m))

        base_params = BallisticParams(
            mass_grams=self._cfg.selected_weight,
            muzzle_velocity_mps=self._speed_mps,
            hop_up_rad_s=self._hop_up_rad_s,
            starting_height_m=self._shooter_height_m,
            launch_angle_deg=aim_angle_deg,
            diameter_mm=self._cfg.diameter_mm,
            air_density_rho=self._cfg.effective_air_density(),
            wind_speed_mps=self._cfg.environment.wind_speed_mps,
            wind_clock=self._cfg.environment.wind_clock,
            drag_coefficient_cw=self._cfg.drag_coefficient_cw,
            magnus_coefficient_k=self._cfg.magnus_coefficient_k,
            spin_damping_cr=self._cfg.spin_damping_cr,
            gravity=self._cfg.gravity,
        )

        best_hop = self._engine.optimize_hopup(
            base_params=base_params,
            shooter_height_m=self._shooter_height_m,
            sight_height_cm=self._sight_height_cm,
            target_height_m=self._target_height_m,
            target_distance_m=self._target_distance_m,
            max_allowed_overhop_cm=self._cfg.max_allowed_overhop_cm,
        )

        self._hop_up_rad_s = best_hop
        self.slider_hop.setValue(int(best_hop))
        self.lbl_hop_slider.setText(tr("hopup_label", best_hop))
        self.recalculate()

    def _on_probe_updated(self, probe: Optional[ProbeResult]):
        if probe:
            self.lbl_probe_info.setText(
                f"PROBE @ {probe.distance:.1f}m | H: {probe.bb_height_cm:.1f}cm | E: {probe.energy_j:.2f}J | "
                f"T: {probe.time_s:.2f}s | Rel: {probe.relative_impact_cm:+.1f}cm | Holdover: {probe.hold_over_cm:+.1f}cm"
                + (f" | {tr('stat_wind_drift')}: {self._drift_text(probe.drift_cm)}" if abs(probe.drift_cm) >= 0.05 else "")
            )
        else:
            self.lbl_probe_info.setText(tr("bb_probe_hint"))

    def recalculate(self):
        eye_height_m = self._shooter_height_m + (self._sight_height_cm / 100.0)
        aim_angle_deg = math.degrees(math.atan2(self._target_height_m - eye_height_m, self._target_distance_m))

        params = BallisticParams(
            mass_grams=self._cfg.selected_weight,
            muzzle_velocity_mps=self._speed_mps,
            launch_angle_deg=aim_angle_deg,
            starting_height_m=self._shooter_height_m,
            hop_up_rad_s=self._hop_up_rad_s,
            diameter_mm=self._cfg.diameter_mm,
            air_density_rho=self._cfg.effective_air_density(),
            wind_speed_mps=self._cfg.environment.wind_speed_mps,
            wind_clock=self._cfg.environment.wind_clock,
            drag_coefficient_cw=self._cfg.drag_coefficient_cw,
            magnus_coefficient_k=self._cfg.magnus_coefficient_k,
            spin_damping_cr=self._cfg.spin_damping_cr,
            gravity=self._cfg.gravity,
        )

        self._trajectory = self._engine.calculate_trajectory(params)

        self.trajectory_canvas.update_data(
            trajectory=self._trajectory,
            target_distance=self._target_distance_m,
            eye_height_m=eye_height_m,
            target_height_m=self._target_height_m,
        )
        self.target_canvas.update_data(
            trajectory=self._trajectory,
            target_distance=self._target_distance_m,
            target_height_m=self._target_height_m,
        )

        metrics = self._engine.calculate_metrics(
            trajectory=self._trajectory,
            eye_height_m=eye_height_m,
            target_height_m=self._target_height_m,
            target_distance_m=self._target_distance_m,
        )

        self.lbl_eff_range.setText(f"{metrics['effective_range']:.1f} m")
        self.lbl_max_range.setText(f"{metrics['max_range']:.1f} m")
        self.lbl_holdover.setText(f"{metrics['hold_over_cm']:.1f} cm")
        self.lbl_target_energy.setText(f"{metrics['energy_at_target']:.2f} J")
        self.lbl_max_overhop.setText(f"{metrics['max_overhop_cm']:.1f} cm")
        self.lbl_overhop_dist.setText(f"{metrics['overhop_dist_m']:.1f} m")
        self.lbl_drift.setText(self._drift_text(metrics["drift_cm"]))

    @staticmethod
    def _drift_text(cm: float) -> str:
        if abs(cm) < 0.05:
            return "0.0 cm"
        return f"{abs(cm):.1f} cm {'L' if cm < 0 else 'R'}"

    def reload_environment(self):
        self.env_card.reload()
        self.recalculate()

    def update_from_new_shot(self, velocity: float):
        if velocity > 0:
            self._speed_mps = velocity
            self.slider_speed.setValue(int(velocity))
            self.lbl_speed_slider.setText(tr("speed_label", velocity))
            self.recalculate()

    def set_theme(self, dark_mode: bool):
        self._dark_mode = dark_mode
        self.trajectory_canvas.set_theme(dark_mode)
        self.target_canvas.set_theme(dark_mode)
        self.recalculate()

    def retranslate(self):
        self.lbl_title.setText(tr("trajectory_sim"))
        self.lbl_dist_slider.setText(tr("target_distance_label", self._target_distance_m))
        self.lbl_speed_slider.setText(tr("speed_label", self._speed_mps))
        self.lbl_hop_slider.setText(tr("hopup_label", self._hop_up_rad_s))
        self.lbl_max_oh_limit.setText(tr("max_overhop", self._cfg.max_allowed_overhop_cm))
        self.btn_optimize.setText(f"★ {tr('optimize_hopup')}")
        self.lbl_attr.setText(tr("powered_by"))
        for key, lbl in self._ribbon_headers:
            lbl.setText(tr(key))
        self.env_card.retranslate()
        self.lbl_probe_info.setText(tr("bb_probe_hint"))
        self.rebuild_weight_chips()
        self.recalculate()
