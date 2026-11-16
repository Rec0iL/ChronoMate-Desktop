"""
ChronoMate Desktop - PCP Ballistics View
Airgun calculator for pellets and slugs (Settings → Ballistic model → PCP): trajectory against the
line of sight, a range card with holdovers and clicks, wind, weather, the kill-zone window and a
BC tool that works the ballistic coefficient out of two chrono readings.
"""

from typing import List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QSizePolicy,
)

from core.config import ConfigManager
from core.i18n import tr
from core.models import ClickUnit, CustomWeight, VelocitySource
from core.pcp_ballistics import (
    Atmosphere, PcpBallistics, PcpParams, PcpPoint, PcpResult, GRAIN_TO_GRAM, J_TO_FTLB, MPS_TO_FPS,
    MRAD_PER_MOA,
)
from core.pellets import CALIBERS, pellets_for
from core.weights import (KIND_PELLET, add_to_active, available_weights, new_own_id, normalize_active,
                          resolve, select_option)
from core.session_manager import SessionManager
from ui.components.pcp_chart import PcpChart
from ui.components.target_canvas import TargetCanvas
from ui.components.responsive import ResponsiveGrid, ResponsiveRow
from ui.components.environment_card import EnvironmentCard

M_TO_YD = 1.0936133


def spin(lo: float, hi: float, value: float, decimals: int = 2, step: float = 1.0, suffix: str = "") -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(decimals)
    s.setSingleStep(step)
    s.setValue(value)
    if suffix:
        s.setSuffix(f" {suffix}")
    s.setKeyboardTracking(False)   # recalculate when typing is done, not on every key
    return s


class PcpView(QWidget):
    weight_selected = Signal(float)       # the selected weight changed here ("save as custom")
    selection_changed = Signal()          # a pellet / custom weight was picked: weight type, caliber, chips
    custom_weights_changed = Signal()     # "save as custom weight"

    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self._dark = dark_mode
        self._cfg = ConfigManager.get_instance()
        self._sm = SessionManager.get_instance()
        self._engine = PcpBallistics()
        self._result: Optional[PcpResult] = None
        self._loading = True

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self.recalculate)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)   # the page fits the window
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        self.lbl_title = QLabel(tr("pcp_title"))
        self.lbl_title.setObjectName("page_title")
        layout.addWidget(self.lbl_title)

        self.lbl_atmo = QLabel("")
        self.lbl_atmo.setObjectName("label_secondary")
        self.lbl_atmo.setWordWrap(True)
        layout.addWidget(self.lbl_atmo)

        # Chart and target view side by side, stacked on narrow windows
        self.chart = PcpChart(dark_mode, self)
        self.chart.probe_changed.connect(self._on_probe)
        self.target = TargetCanvas(dark_mode=dark_mode, parent=self)
        top = ResponsiveRow(threshold=860)
        top.add_widget(self.chart, 3)
        top.add_widget(self.target, 1)
        layout.addWidget(top)

        self.lbl_probe = QLabel(tr("pcp_probe_hint"))
        self.lbl_probe.setFont(QFont("Consolas, Courier New", 10, QFont.Bold))
        self.lbl_probe.setObjectName("label_secondary")
        self.lbl_probe.setWordWrap(True)
        layout.addWidget(self.lbl_probe)

        # Summary ribbon
        ribbon = QFrame()
        ribbon.setObjectName("card")
        rl = QGridLayout(ribbon)
        rl.setContentsMargins(14, 10, 14, 10)
        self._stat_labels = {}
        for i, key in enumerate(["pcp_stat_me", "pcp_stat_zero_e", "pcp_stat_near", "pcp_stat_far",
                                 "pcp_stat_maxord", "pcp_stat_kz"]):
            hdr = QLabel(tr(key))
            hdr.setObjectName("label_secondary")
            val = QLabel("--")
            val.setFont(QFont("Consolas, Courier New", 11, QFont.Bold))
            rl.addWidget(hdr, (i // 3) * 2, i % 3)
            rl.addWidget(val, (i // 3) * 2 + 1, i % 3)
            self._stat_labels[key] = (hdr, val)
        self.lbl_best_zero = QLabel("")
        self.lbl_best_zero.setObjectName("label_secondary")
        self.btn_best_zero = QPushButton(tr("pcp_use_best_zero"))
        self.btn_best_zero.clicked.connect(self._use_best_zero)
        self.lbl_best_zero.setWordWrap(True)
        rl.addWidget(self.lbl_best_zero, 4, 0, 1, 2)
        rl.addWidget(self.btn_best_zero, 4, 2)
        layout.addWidget(ribbon)

        self.lbl_warnings = QLabel("")
        self.lbl_warnings.setWordWrap(True)
        self.lbl_warnings.setStyleSheet("color: #FF9800; font-weight: 600;")
        layout.addWidget(self.lbl_warnings)

        # Input cards
        # Input cards: two columns when there's room, one below the other on narrow windows
        cards = ResponsiveGrid(min_col_width=420, max_cols=2)
        for card in (self._build_projectile_card(), self._build_shot_card(),
                     self._build_environment_card(), self._build_bc_card()):
            cards.add_widget(card)
        layout.addWidget(cards)

        # Range card
        self.lbl_card_title = QLabel(tr("pcp_range_card"))
        self.lbl_card_title.setObjectName("section_title")
        layout.addWidget(self.lbl_card_title)
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(360)
        self.table.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)   # scrolls inside, not the page
        layout.addWidget(self.table)

        layout.addStretch()
        scroll.setWidget(container)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        self._loading = False
        self.recalculate()

    # --- cards ----------------------------------------------------------------------------------
    def _card(self, title_key: str):
        frame = QFrame()
        frame.setObjectName("card")
        grid = QGridLayout(frame)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setVerticalSpacing(8)
        title = QLabel(tr(title_key))
        title.setObjectName("section_title")
        grid.addWidget(title, 0, 0, 1, 2)
        return frame, grid

    def _row(self, grid: QGridLayout, row: int, label_key: str, widget):
        lbl = QLabel(tr(label_key))
        grid.addWidget(lbl, row, 0)
        grid.addWidget(widget, row, 1)
        return lbl

    def _build_projectile_card(self):
        frame, g = self._card("pcp_card_projectile")
        pc = self._cfg.pcp
        self.combo_projectile = QComboBox()
        # entries are long ("JSB … — 18.13 gr / 1.175 g — BC …"): don't let them widen the page
        self.combo_projectile.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_projectile.setMinimumContentsLength(18)
        self._fill_projectiles()
        self.combo_projectile.activated.connect(self._on_projectile_picked)
        g.addWidget(self.combo_projectile, 1, 0, 1, 2)

        self.spin_mass = spin(0.1, 20.0, pc.mass_grams, 3, 0.005, "g")
        self.lbl_grains = QLabel("")
        self.lbl_grains.setObjectName("label_secondary")
        self.spin_caliber = spin(4.0, 12.0, pc.caliber_mm, 2, 0.01, "mm")
        self.spin_bc = spin(0.005, 1.0, pc.bc, 3, 0.001)
        self.combo_model = QComboBox()
        self.combo_model.addItems(["G1", "G7"])
        self.combo_model.setCurrentText(pc.drag_model)
        self._row(g, 2, "pcp_mass", self.spin_mass)
        g.addWidget(self.lbl_grains, 3, 1)
        self._row(g, 4, "pcp_caliber", self.spin_caliber)
        self._row(g, 5, "pcp_bc", self.spin_bc)
        self._row(g, 6, "pcp_drag_model", self.combo_model)
        self.btn_save_custom = QPushButton(tr("pcp_save_custom"))
        self.btn_save_custom.clicked.connect(self._save_as_custom)
        g.addWidget(self.btn_save_custom, 7, 0, 1, 2)
        self.lbl_preset_note = QLabel(tr("pcp_preset_note"))
        self.lbl_preset_note.setObjectName("label_secondary")
        self.lbl_preset_note.setWordWrap(True)
        g.addWidget(self.lbl_preset_note, 8, 0, 1, 2)
        for w in (self.spin_mass, self.spin_caliber, self.spin_bc):
            w.valueChanged.connect(self._on_input)
        self.combo_model.currentTextChanged.connect(self._on_input)
        return frame

    def _build_shot_card(self):
        frame, g = self._card("pcp_card_shot")
        pc = self._cfg.pcp
        self.combo_vsource = QComboBox()
        self.combo_vsource.addItem(tr("pcp_v_latest"), VelocitySource.LATEST.value)
        self.combo_vsource.addItem(tr("pcp_v_average"), VelocitySource.AVERAGE.value)
        self.combo_vsource.addItem(tr("pcp_v_manual"), VelocitySource.MANUAL.value)
        self.combo_vsource.setCurrentIndex(max(0, self.combo_vsource.findData(pc.velocity_source)))
        self.spin_velocity = spin(30.0, 450.0, pc.manual_velocity_mps, 1, 1.0, "m/s")
        self.spin_zero = spin(5.0, 150.0, pc.zero_range_m, 0, 1.0, "m")
        self.spin_sight = spin(0.0, 15.0, pc.sight_height_cm, 1, 0.1, "cm")
        self.combo_click = QComboBox()
        self.combo_click.addItem("0.1 MRAD", ClickUnit.MRAD_01.value)
        self.combo_click.addItem("1/4 MOA", ClickUnit.MOA_025.value)
        self.combo_click.addItem("1/8 MOA", ClickUnit.MOA_0125.value)
        self.combo_click.setCurrentIndex(max(0, self.combo_click.findData(pc.click_unit)))
        self.spin_angle = spin(-60.0, 60.0, pc.shot_angle_deg, 0, 1.0, "°")
        self.spin_kz = spin(0.5, 20.0, pc.kill_zone_cm, 1, 0.5, "cm")
        self.spin_step = spin(1.0, 25.0, pc.step_m, 0, 1.0, "m")
        self.spin_max = spin(10.0, 250.0, pc.max_range_m, 0, 5.0, "m")
        self.spin_elimit = spin(0.0, 200.0, pc.energy_limit_j, 1, 0.5, "J")
        self.spin_target = spin(5.0, 250.0, pc.target_distance_m, 0, 5.0, "m")
        self.spin_elimit.setSpecialValueText(tr("pcp_off"))
        self.spin_elimit.setToolTip(tr("pcp_energy_limit_tip"))
        self._row(g, 1, "pcp_velocity_source", self.combo_vsource)
        self._row(g, 2, "pcp_velocity", self.spin_velocity)
        self._row(g, 3, "pcp_zero", self.spin_zero)
        self._row(g, 4, "pcp_sight_height", self.spin_sight)
        self._row(g, 5, "pcp_click", self.combo_click)
        self._row(g, 6, "pcp_shot_angle", self.spin_angle)
        self._row(g, 7, "pcp_kill_zone", self.spin_kz)
        self._row(g, 8, "pcp_step", self.spin_step)
        self._row(g, 9, "pcp_max_range", self.spin_max)
        self._row(g, 10, "pcp_energy_limit", self.spin_elimit)
        self._row(g, 11, "pcp_target_distance", self.spin_target)
        for w in (self.spin_velocity, self.spin_zero, self.spin_sight, self.spin_angle, self.spin_kz,
                  self.spin_step, self.spin_max, self.spin_elimit, self.spin_target):
            w.valueChanged.connect(self._on_input)
        self.combo_vsource.currentIndexChanged.connect(self._on_input)
        self.combo_click.currentIndexChanged.connect(self._on_input)
        return frame

    def _build_environment_card(self):
        self.env_card = EnvironmentCard(self)
        self.env_card.changed.connect(self._timer.start)
        return self.env_card

    def _build_bc_card(self):
        frame, g = self._card("pcp_card_bc")
        desc = QLabel(tr("pcp_bc_desc"))
        desc.setObjectName("label_secondary")
        desc.setWordWrap(True)
        g.addWidget(desc, 1, 0, 1, 2)
        self.spin_v1 = spin(30.0, 450.0, 274.0, 1, 1.0, "m/s")
        self.spin_d1 = spin(0.0, 50.0, 1.0, 1, 0.5, "m")
        self.spin_v2 = spin(30.0, 450.0, 250.0, 1, 1.0, "m/s")
        self.spin_d2 = spin(1.0, 150.0, 20.0, 1, 1.0, "m")
        for i, (key, w) in enumerate([("pcp_bc_v1", self.spin_v1), ("pcp_bc_d1", self.spin_d1),
                                      ("pcp_bc_v2", self.spin_v2), ("pcp_bc_d2", self.spin_d2)]):
            g.addWidget(QLabel(tr(key)), 2 + i, 0)
            g.addWidget(w, 2 + i, 1)
        self.btn_bc_latest = QPushButton(tr("pcp_bc_take_last_two"))
        self.btn_bc_latest.setToolTip(tr("pcp_bc_take_last_two_tip"))
        self.btn_bc_latest.clicked.connect(self._bc_from_last_two)
        self.btn_bc_calc = QPushButton(tr("pcp_bc_calc"))
        self.btn_bc_calc.setObjectName("primary_btn")
        self.btn_bc_calc.clicked.connect(self._calc_bc)
        self.lbl_bc_result = QLabel("")
        self.lbl_bc_result.setWordWrap(True)
        self.lbl_bc_result.setFont(QFont("Consolas, Courier New", 11, QFont.Bold))
        self.btn_bc_use = QPushButton(tr("pcp_bc_use"))
        self.btn_bc_use.setEnabled(False)
        self.btn_bc_use.clicked.connect(self._use_bc)
        g.addWidget(self.btn_bc_latest, 6, 0)
        g.addWidget(self.btn_bc_calc, 6, 1)
        g.addWidget(self.lbl_bc_result, 7, 0, 1, 2)
        g.addWidget(self.btn_bc_use, 8, 1)
        self._bc_value: Optional[float] = None
        return frame

    # --- projectile list --------------------------------------------------------------------------
    def _fill_projectiles(self):
        """Your active list first (what the chips show), then the whole pellet & slug library grouped
        by caliber. Picking from the library adds it to the active list."""
        self.combo_projectile.blockSignals(True)
        self.combo_projectile.clear()
        self.combo_projectile.addItem(tr("pcp_pick_projectile"), None)
        model = self.combo_projectile.model()

        def header(text):
            self.combo_projectile.addItem(text, None)
            model.item(self.combo_projectile.count() - 1).setEnabled(False)

        header(f"── {tr('active_list_title')} ──")
        for opt in available_weights(self._cfg, KIND_PELLET):
            self.combo_projectile.addItem(("★ " if opt.is_custom else "") + opt.label + self._bc_text(opt), ("id", opt.id))
        for key, mm in CALIBERS:
            header(f"── {tr('library_title')} · {mm:g} mm ({key}) ──")
            for p in pellets_for(key):
                kind = tr("pcp_slug") if p.slug else ""
                bc = f"BC ≈{p.bc:.3f} ({p.bc_model or '?'}, {p.source})" if p.bc is not None else tr("pcp_bc_unknown")
                self.combo_projectile.addItem(f"{p.name}{kind} — {p.grains:g} gr / {p.mass_grams:.3f} g — {bc}",
                                              ("id", "pellet:" + p.name))
        self.combo_projectile.setCurrentIndex(0)
        self.combo_projectile.blockSignals(False)

    @staticmethod
    def _bc_text(opt) -> str:
        if opt.pellet is not None:
            return f" — BC ≈{opt.pellet.bc:.3f}" if opt.pellet.bc is not None else f" — {tr('pcp_bc_unknown')}"
        return ""

    def _on_projectile_picked(self, idx: int):
        data = self.combo_projectile.itemData(idx)
        if not data:
            return
        opt = resolve(self._cfg, data[1])
        if opt is None:
            return
        add_to_active(self._cfg, opt.id)     # picked from the library: now also a chip
        select_option(self._cfg, opt)
        if opt.pellet is not None and opt.pellet.bc is None:
            self.lbl_preset_note.setText(tr("pcp_bc_unknown_note", opt.pellet.name))
        self._cfg.save()
        self.load_inputs()
        self.selection_changed.emit()
        self.recalculate()

    def load_inputs(self):
        """Show the PCP settings in the input fields (after a pick here or a chip elsewhere)."""
        pc = self._cfg.pcp
        self._loading = True
        self.spin_mass.setValue(pc.mass_grams)
        self.spin_caliber.setValue(pc.caliber_mm)
        self.spin_bc.setValue(pc.bc)
        self.combo_model.setCurrentText(pc.drag_model)
        self._loading = False

    def _save_as_custom(self):
        """The PCP projectile (with its BC) becomes one of your own pellets, active and selected."""
        pc = self._cfg.pcp
        name = pc.projectile_name or "Pellet"
        cw = next((c for c in self._cfg.custom_weights
                   if c.kind == KIND_PELLET and c.name == name and abs(c.weight - pc.mass_grams) < 1e-4), None)
        if cw is None:
            cw = CustomWeight(name=name, weight=round(pc.mass_grams, 3), id=new_own_id(), kind=KIND_PELLET)
            self._cfg.custom_weights.append(cw)
        cw.caliber, cw.caliber_unit, cw.bc, cw.drag_model = pc.caliber_mm, "mm", pc.bc, pc.drag_model
        normalize_active(self._cfg)
        select_option(self._cfg, resolve(self._cfg, "own:" + cw.id))
        self._cfg.save()
        self._fill_projectiles()
        self.custom_weights_changed.emit()
        self.weight_selected.emit(self._cfg.selected_weight)

    # --- inputs → settings ------------------------------------------------------------------------
    def _on_input(self, *_):
        if self._loading:
            return
        self.spin_velocity.setEnabled(self.combo_vsource.currentData() == VelocitySource.MANUAL.value)
        self._store_inputs()
        self._timer.start()

    def _store_inputs(self):
        pc = self._cfg.pcp
        pc.mass_grams = self.spin_mass.value()
        pc.caliber_mm = self.spin_caliber.value()
        pc.bc = self.spin_bc.value()
        pc.drag_model = self.combo_model.currentText()
        pc.velocity_source = self.combo_vsource.currentData()
        pc.manual_velocity_mps = self.spin_velocity.value()
        pc.zero_range_m = self.spin_zero.value()
        pc.sight_height_cm = self.spin_sight.value()
        pc.click_unit = self.combo_click.currentData()
        pc.shot_angle_deg = self.spin_angle.value()
        pc.kill_zone_cm = self.spin_kz.value()
        pc.step_m = self.spin_step.value()
        pc.max_range_m = self.spin_max.value()
        pc.energy_limit_j = self.spin_elimit.value()
        pc.target_distance_m = self.spin_target.value()
        self._cfg.save()

    # --- calculation ------------------------------------------------------------------------------
    def muzzle_velocity(self) -> float:
        pc = self._cfg.pcp
        shots = self._sm.active_session.shots
        if pc.velocity_source == VelocitySource.LATEST.value and shots:
            return shots[-1].velocity
        if pc.velocity_source == VelocitySource.AVERAGE.value and shots:
            return sum(s.velocity for s in shots) / len(shots)
        return pc.manual_velocity_mps

    def params(self) -> PcpParams:
        pc, env = self._cfg.pcp, self._cfg.environment
        return PcpParams(
            mass_grams=pc.mass_grams, caliber_mm=pc.caliber_mm, bc=pc.bc, drag_model=pc.drag_model,
            muzzle_velocity_mps=self.muzzle_velocity(), sight_height_cm=pc.sight_height_cm,
            zero_range_m=pc.zero_range_m, shot_angle_deg=pc.shot_angle_deg,
            wind_speed_mps=env.wind_speed_mps, wind_clock=env.wind_clock,
            max_range_m=pc.max_range_m, step_m=pc.step_m, kill_zone_cm=pc.kill_zone_cm,
            gravity=self._cfg.gravity,
        )

    def atmosphere(self) -> Atmosphere:
        env = self._cfg.environment
        return Atmosphere(env.temperature_c, env.pressure_hpa, env.humidity_pct, env.altitude_m, env.use_altitude)

    def recalculate(self):
        p, atm = self.params(), self.atmosphere()
        self._result = self._engine.solve(p, atm)
        r = self._result
        imp = self._cfg.show_imperial

        if self.combo_vsource.currentData() != VelocitySource.MANUAL.value:
            self.spin_velocity.blockSignals(True)
            self.spin_velocity.setValue(p.muzzle_velocity_mps)
            self.spin_velocity.blockSignals(False)
        self.spin_velocity.setEnabled(self.combo_vsource.currentData() == VelocitySource.MANUAL.value)
        self.lbl_grains.setText(f"= {p.mass_grams / GRAIN_TO_GRAM:.2f} gr")

        self.lbl_atmo.setText(tr("pcp_atmo_line", self._v(p.muzzle_velocity_mps), r.muzzle_mach,
                                 r.air_density, r.speed_of_sound_mps))
        self.chart.set_result(r, p.max_range_m, p.kill_zone_cm)
        tp = r.point_at(self._cfg.pcp.target_distance_m)
        self.target.set_impact(self._cfg.pcp.target_distance_m, tp.drop_cm if tp else 0.0, tp.drift_cm if tp else 0.0)

        st = self._stat_labels
        st["pcp_stat_me"][1].setText(self._e(r.muzzle_energy_j))
        zp = r.point_at(p.zero_range_m)
        st["pcp_stat_zero_e"][1].setText(self._e(zp.energy_j) if zp else "--")
        st["pcp_stat_near"][1].setText(self._d(r.near_zero_m))
        st["pcp_stat_far"][1].setText(self._d(r.far_zero_m))
        st["pcp_stat_maxord"][1].setText(f"{r.max_ordinate_cm:+.1f} cm @ {r.max_ordinate_range_m:.0f} m" if r.points else "--")
        kz = (f"{r.kill_zone_from_m:.0f}–{r.kill_zone_to_m:.0f} m"
              if r.kill_zone_from_m is not None and r.kill_zone_to_m is not None else "--")
        st["pcp_stat_kz"][1].setText(kz)

        best = self._engine.best_zero_for_kill_zone(p, atm, r if (p.shot_angle_deg == 0 and p.wind_speed_mps == 0) else None)
        self._best_zero = best
        if best:
            self.lbl_best_zero.setText(tr("pcp_best_zero", p.kill_zone_cm, best[0], best[1], best[2]))
        else:
            self.lbl_best_zero.setText("")
        self.btn_best_zero.setEnabled(bool(best) and abs(best[0] - p.zero_range_m) >= 0.5)

        warns = []
        if "pcp_warn_transonic" in r.warnings:
            warns.append(tr("pcp_warn_transonic", r.muzzle_mach))
        if "pcp_warn_short" in r.warnings:
            warns.append(tr("pcp_warn_short"))
        if "pcp_warn_overhop_kz" in r.warnings:
            warns.append(tr("pcp_warn_overhop_kz", r.max_ordinate_cm, p.kill_zone_cm / 2))
        if pc_limit := self._cfg.pcp.energy_limit_j:
            if r.muzzle_energy_j > pc_limit:
                warns.append(tr("pcp_warn_energy", self._e(r.muzzle_energy_j), self._e(pc_limit)))
        self.lbl_warnings.setText("\n".join("⚠ " + w for w in warns))
        self.lbl_warnings.setVisible(bool(warns))

        self._fill_table(r, imp)

    def _fill_table(self, r: PcpResult, imp: bool):
        click_mrad = ClickUnit(self._cfg.pcp.click_unit).mrad_per_click
        headers = [tr("pcp_col_range"), tr("pcp_col_drop"), "MRAD", "MOA", tr("pcp_col_clicks"),
                   tr("pcp_col_drift"), tr("pcp_col_drift_clicks"), tr("pcp_col_velocity"),
                   tr("pcp_col_energy"), tr("pcp_col_time")]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setRowCount(len(r.range_card))
        zero = self._cfg.pcp.zero_range_m
        for row, pt in enumerate(r.range_card):
            hold = pt.hold_mrad()
            drift = pt.drift_mrad()
            cells = [
                f"{pt.range_m:.0f} m" + (f"  ({pt.range_m * M_TO_YD:.0f} yd)" if imp else ""),
                self._drop_text(pt.drop_cm, imp),
                f"{hold:+.2f}" if abs(hold) >= 0.005 else "0.00",
                f"{hold / MRAD_PER_MOA:+.2f}" if abs(hold) >= 0.005 else "0.00",
                self._clicks(hold / click_mrad, "↑", "↓"),
                self._drift_text(pt.drift_cm, imp),
                self._clicks(drift / click_mrad, "R", "L"),
                self._v(pt.velocity_mps),
                self._e(pt.energy_j),
                f"{pt.time_s:.3f} s",
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if abs(pt.range_m - zero) < 0.01:
                    item.setForeground(QColor("#00E5FF" if self._dark else "#00838F"))
                self.table.setItem(row, col, item)

    # --- formatting -------------------------------------------------------------------------------
    def _v(self, mps: float) -> str:
        return f"{mps:.1f} m/s" + (f" ({mps * MPS_TO_FPS:.0f} fps)" if self._cfg.show_imperial else "")

    def _e(self, j: float) -> str:
        return f"{j:.2f} J" + (f" ({j * J_TO_FTLB:.1f} ft-lb)" if self._cfg.show_imperial else "")

    def _d(self, m: Optional[float]) -> str:
        if m is None:
            return "--"
        return f"{m:.1f} m" + (f" ({m * M_TO_YD:.1f} yd)" if self._cfg.show_imperial else "")

    @staticmethod
    def _drop_text(cm: float, imp: bool) -> str:
        if abs(cm) < 0.05:
            return "0.0 cm" + ('  (0.0")' if imp else "")
        return f"{cm:+.1f} cm" + (f"  ({cm / 2.54:+.1f}\")" if imp else "")

    @staticmethod
    def _clicks(n: float, plus: str, minus: str) -> str:
        """Whole clicks with the direction to dial / hold (no '-0')."""
        k = int(round(n))
        if k == 0:
            return "0"
        return f"{abs(k)} {plus if k > 0 else minus}"

    @staticmethod
    def _drift_text(cm: float, imp: bool) -> str:
        if abs(cm) < 0.05:
            return "0.0 cm"
        side = "L" if cm < 0 else "R"
        return f"{abs(cm):.1f} cm {side}" + (f"  ({abs(cm) / 2.54:.1f}\")" if imp else "")

    # --- probe, best zero, BC tool ------------------------------------------------------------------
    def _on_probe(self, pt: Optional[PcpPoint]):
        if pt is None:
            self.lbl_probe.setText(tr("pcp_probe_hint"))
            return
        click_mrad = ClickUnit(self._cfg.pcp.click_unit).mrad_per_click
        self.lbl_probe.setText(tr("pcp_probe_line", self._d(pt.range_m), pt.drop_cm, pt.hold_mrad(),
                                  pt.hold_mrad() / click_mrad, self._v(pt.velocity_mps), self._e(pt.energy_j),
                                  pt.time_s))

    def _use_best_zero(self):
        if getattr(self, "_best_zero", None):
            self.spin_zero.setValue(self._best_zero[0])

    def _bc_from_last_two(self):
        """Two chronos (or one moved): the last two shots are the near and the far reading."""
        shots = self._sm.active_session.shots
        if len(shots) >= 2:
            self.spin_v1.setValue(shots[-2].velocity)
            self.spin_v2.setValue(shots[-1].velocity)

    def _calc_bc(self):
        bc = self._engine.solve_bc(self.params(), self.atmosphere(), self.spin_v1.value(), self.spin_d1.value(),
                                   self.spin_v2.value(), self.spin_d2.value())
        self._bc_value = bc
        if bc is None:
            self.lbl_bc_result.setText(tr("pcp_bc_invalid"))
            self.btn_bc_use.setEnabled(False)
        else:
            self.lbl_bc_result.setText(tr("pcp_bc_result", bc, self._cfg.pcp.drag_model))
            self.btn_bc_use.setEnabled(True)

    def _use_bc(self):
        if self._bc_value:
            self.spin_bc.setValue(round(self._bc_value, 3))

    # --- app hooks ------------------------------------------------------------------------------
    def update_from_new_shot(self):
        if self._cfg.pcp.velocity_source != VelocitySource.MANUAL.value:
            self._timer.start()

    def refresh_settings(self):
        """Units switch, weights, the selected pellet or the weather changed elsewhere."""
        self._fill_projectiles()
        self.load_inputs()
        self.env_card.reload()
        self.recalculate()

    def set_theme(self, dark: bool):
        self._dark = dark
        self.chart.set_theme(dark)
        self.target.set_theme(dark)
        self.recalculate()
