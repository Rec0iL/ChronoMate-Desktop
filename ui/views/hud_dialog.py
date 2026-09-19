"""
ChronoMate Desktop - Field Station Full-Screen HUD View
Massive high-visibility telemetry for chrono stations, stage monitors, or projectors.
Supports responsive auto-scaling for any screen resolution (1080p, 1440p, 4K, laptops).
Supports both standard Dashboard HUD and Orga Marshaling HUD (Legal/Illegal per weapon class).
"""

from typing import List, Tuple
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent

from core.session_manager import SessionManager
from core.config import ConfigManager
from core.models import WeaponClass, STANDARD_BB_WEIGHTS
from core.i18n import tr
from ui.components.joule_grid import JouleGrid


class ScaledHudCard(QFrame):
    clicked = Signal(object)

    def __init__(self, wc: WeaponClass, dark_mode: bool = True, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.weapon_class = wc
        self._dark_mode = dark_mode
        self._is_active = is_active
        self._latest_vel = 0.0
        self._latest_scale = 1.0

        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tr("active_ref_hud_tooltip"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        self.lbl_name = QLabel(wc.name)
        self.lbl_name.setAlignment(Qt.AlignCenter)

        self.lbl_limit = QLabel(f"≤ {wc.max_joules:.2f} J")
        self.lbl_limit.setAlignment(Qt.AlignCenter)

        self.lbl_status = QLabel(tr("awaiting_shot"))
        self.lbl_status.setAlignment(Qt.AlignCenter)

        self.lbl_detail = QLabel("--")
        self.lbl_detail.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.lbl_name)
        layout.addWidget(self.lbl_limit)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.lbl_detail)

        self.update_velocity(0.0, 1.0)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.weapon_class)
        super().mousePressEvent(event)

    def set_active(self, is_active: bool):
        self._is_active = is_active
        self.update_velocity(self._latest_vel, self._latest_scale)

    def update_velocity(self, vel: float, card_scale: float = 1.0):
        self._latest_vel = vel
        self._latest_scale = card_scale

        font_name = max(13, int(17 * card_scale))
        font_limit = max(10, int(13 * card_scale))
        font_status = max(13, int(19 * card_scale))
        font_detail = max(10, int(13 * card_scale))
        radius = max(8, int(12 * card_scale))

        active_accent = "#00E5FF" if self._dark_mode else "#00838F"

        if vel <= 0.0:
            bg = "#161B22" if self._dark_mode else "#ECEFF1"
            border = active_accent if self._is_active else ("#30363D" if self._dark_mode else "#CFD8DC")
            text_c = "#8B949E" if self._dark_mode else "#607D8B"
            status_text = tr("awaiting_shot")
            detail_text = "--"
        else:
            e_20 = 0.5 * 0.00020 * (vel ** 2)
            max_w = (2.0 * self.weapon_class.max_joules / (vel ** 2)) * 1000.0
            if e_20 <= self.weapon_class.max_joules:
                bg = "rgba(46, 125, 50, 0.28)" if self._dark_mode else "rgba(46, 125, 50, 0.15)"
                border = active_accent if self._is_active else ("#2E7D32" if self._dark_mode else "#4CAF50")
                text_c = "#88FF11" if self._dark_mode else "#1B5E20"
                status_text = f"{tr('legal')} ✓"
                detail_text = tr("max_bb_weight_label", max_w)
            else:
                bg = "rgba(244, 67, 54, 0.28)" if self._dark_mode else "rgba(244, 67, 54, 0.15)"
                border = active_accent if self._is_active else ("#F44336" if self._dark_mode else "#C62828")
                text_c = "#F44336" if self._dark_mode else "#C62828"
                status_text = f"{tr('illegal')} ✕"
                detail_text = tr("exceeds_limit_20")

        border_w = "3px" if self._is_active else "2px"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: {border_w} solid {border};
                border-radius: {radius}px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        display_name = f"★ {self.weapon_class.name}" if self._is_active else self.weapon_class.name
        self.lbl_name.setText(display_name)
        name_c = active_accent if self._is_active else text_c
        self.lbl_name.setStyleSheet(f"color: {name_c}; font-size: {font_name}px; font-weight: 800;")
        self.lbl_limit.setText(f"≤ {self.weapon_class.max_joules:.2f} J")
        self.lbl_limit.setStyleSheet(f"color: #8B949E; font-size: {font_limit}px;")
        self.lbl_status.setText(status_text)
        self.lbl_status.setStyleSheet(f"color: {text_c}; font-size: {font_status}px; font-weight: 900;")
        self.lbl_detail.setText(detail_text)
        self.lbl_detail.setStyleSheet(f"color: {text_c}; font-size: {font_detail}px;")


class HudDialog(QDialog):
    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ChronoMate - Field Station HUD")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: #05070A; color: #FFFFFF;")

        self._dark_mode = dark_mode
        self._is_orga_mode: bool = False
        self._sm = SessionManager.get_instance()
        self._cfg = ConfigManager.get_instance()
        self._cards: List[ScaledHudCard] = []

        # Find or default active weapon class for Joule Reference Grid
        self._active_weapon_class = None
        for wc in self._cfg.weapon_classes:
            if wc.name == self._cfg.selected_weapon_class:
                self._active_weapon_class = wc
                break
        if not self._active_weapon_class and self._cfg.weapon_classes:
            self._active_weapon_class = self._cfg.weapon_classes[0]

        self.main_layout = QVBoxLayout(self)

        # Top Bar: Mode Switcher & Exit hint
        self.top_bar = QHBoxLayout()
        self.lbl_title = QLabel(tr("hud_title"))
        self.top_bar.addWidget(self.lbl_title)
        self.top_bar.addStretch()

        self.btn_toggle_mode = QPushButton(f"🛡️ {tr('hud_switch_orga')}")
        self.btn_toggle_mode.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_mode.clicked.connect(self._toggle_mode)
        self.top_bar.addWidget(self.btn_toggle_mode)

        self.lbl_hint = QLabel(tr("hud_exit_hint"))
        self.top_bar.addWidget(self.lbl_hint)

        self.main_layout.addLayout(self.top_bar)

        # Center Display Area
        self.center_frame = QFrame()
        self.center_frame.setObjectName("hud_center_frame")
        self.center_layout = QVBoxLayout(self.center_frame)
        self.center_layout.setAlignment(Qt.AlignCenter)
        self.center_layout.setSpacing(12)

        # Massive Velocity Readout Row
        self.vel_row = QHBoxLayout()
        self.vel_row.setAlignment(Qt.AlignCenter)
        self.vel_row.setSpacing(12)

        self.lbl_vel = QLabel("0.00")
        self.lbl_vel.setAlignment(Qt.AlignCenter)

        self.lbl_unit = QLabel("m/s")
        self.lbl_unit.setAlignment(Qt.AlignBottom)

        self.vel_row.addWidget(self.lbl_vel)
        self.vel_row.addWidget(self.lbl_unit)
        self.center_layout.addLayout(self.vel_row)

        # Big Energy Readout (Visible in Dashboard Mode)
        self.lbl_energy = QLabel("0.00 J")
        self.lbl_energy.setAlignment(Qt.AlignCenter)
        self.center_layout.addWidget(self.lbl_energy)

        # Weapon Class Compliance Row (Visible in Orga Mode)
        self.cards_container = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignCenter)
        self.center_layout.addWidget(self.cards_container)
        self.cards_container.setVisible(False)

        # Joule Reference Grid Container (Visible in Orga Mode)
        self.joule_container = QWidget()
        self.joule_layout = QVBoxLayout(self.joule_container)
        self.joule_layout.setAlignment(Qt.AlignCenter)
        self.joule_layout.setContentsMargins(0, 0, 0, 0)
        self.joule_layout.setSpacing(6)

        self.lbl_hud_grid_title = QLabel("")
        self.lbl_hud_grid_title.setAlignment(Qt.AlignCenter)
        self.joule_layout.addWidget(self.lbl_hud_grid_title)

        self.hud_joule_grid = JouleGrid(dark_mode=self._dark_mode, parent=self.joule_container)
        weights = [(weight, f"{weight:.2f}g") for weight in STANDARD_BB_WEIGHTS]
        self.hud_joule_grid.set_weights(weights, columns=10)
        self.joule_layout.addWidget(self.hud_joule_grid)

        self.center_layout.addWidget(self.joule_container)
        self.joule_container.setVisible(False)

        # Subtitle (Weight / Shot # or All-Class Compliance)
        self.lbl_sub = QLabel("")
        self.lbl_sub.setAlignment(Qt.AlignCenter)
        self.center_layout.addWidget(self.lbl_sub)

        self.main_layout.addWidget(self.center_frame, stretch=1)

        self.rebuild_cards()
        self.refresh()

    def rebuild_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self._cards.clear()

        # Re-verify active weapon class exists
        if self._active_weapon_class not in self._cfg.weapon_classes:
            self._active_weapon_class = None
            for wc in self._cfg.weapon_classes:
                if wc.name == self._cfg.selected_weapon_class:
                    self._active_weapon_class = wc
                    break
            if not self._active_weapon_class and self._cfg.weapon_classes:
                self._active_weapon_class = self._cfg.weapon_classes[0]

        active_name = self._active_weapon_class.name if self._active_weapon_class else ""

        for wc in self._cfg.weapon_classes:
            is_active = (wc.name == active_name)
            card = ScaledHudCard(wc, dark_mode=self._dark_mode, is_active=is_active, parent=self.cards_container)
            card.clicked.connect(self._on_hud_card_clicked)
            self.cards_layout.addWidget(card)
            self._cards.append(card)

    def _on_hud_card_clicked(self, wc: WeaponClass):
        self._active_weapon_class = wc
        self._cfg.selected_weapon_class = wc.name
        self._cfg.save()
        for card in self._cards:
            card.set_active(card.weapon_class.name == wc.name)
        self._update_hud_joule_grid()

    def _update_hud_joule_grid(self):
        shots = self._sm.active_session.shots
        latest_vel = shots[-1].velocity if shots else 0.0
        limit = self._active_weapon_class.max_joules if self._active_weapon_class else 1.50
        name = self._active_weapon_class.name if self._active_weapon_class else "AR"
        self.lbl_hud_grid_title.setText(f"{tr('joule_grid_title')} — {name} (≤ {limit:.2f} J)")
        if hasattr(self, "hud_joule_grid"):
            self.hud_joule_grid.update_velocity(latest_vel, limit)

    def _toggle_mode(self):
        self._is_orga_mode = not self._is_orga_mode
        if self._is_orga_mode:
            self.btn_toggle_mode.setText(f"📊 {tr('hud_switch_dash')}")
            self.lbl_energy.setVisible(False)
            self.cards_container.setVisible(True)
            self.joule_container.setVisible(True)
        else:
            self.btn_toggle_mode.setText(f"🛡️ {tr('hud_switch_orga')}")
            self.lbl_energy.setVisible(True)
            self.cards_container.setVisible(False)
            self.joule_container.setVisible(False)

        self.refresh()
        self._apply_scaling()

    def refresh(self):
        shots = self._sm.active_session.shots
        accent = "#88FF11" if self._dark_mode else "#2E7D32"

        if shots:
            latest = shots[-1]
            vel = latest.velocity
            energy = latest.energy_joules
            self.lbl_vel.setText(f"{vel:.1f}")
            self.lbl_energy.setText(f"{energy:.2f} J")

            if self._is_orga_mode:
                self.lbl_sub.setText(f"{tr('shot_num_label', len(shots))} | {tr('hud_all_classes')}")
            else:
                self.lbl_sub.setText(f"{latest.weight_grams:.2f}g BB | {tr('shot_num_label', len(shots))}")
        else:
            vel = 0.0
            self.lbl_vel.setText("0.00")
            self.lbl_energy.setText("0.00 J")
            if self._is_orga_mode:
                self.lbl_sub.setText(f"{tr('hud_ready')} | {tr('hud_all_classes')}")
            else:
                self.lbl_sub.setText(f"{self._cfg.selected_weight:.2f}g BB | {tr('hud_ready')}")

        for card in self._cards:
            card.update_velocity(vel, getattr(self, "_card_scale", 1.0))

        if self._is_orga_mode:
            self._update_hud_joule_grid()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_scaling()

    def _apply_scaling(self):
        w = self.width()
        h = self.height()

        margin_h = max(24, int(w * 0.035))
        margin_v = max(16, int(h * 0.025))
        self.main_layout.setContentsMargins(margin_h, margin_v, margin_h, margin_v)
        self.main_layout.setSpacing(max(8, int(h * 0.012)))

        radius = max(14, int(h * 0.024))
        self.center_frame.setStyleSheet(f"""
            QFrame#hud_center_frame {{
                background-color: #0B0E14;
                border: 2px solid #21262D;
                border-radius: {radius}px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        accent = "#88FF11" if self._dark_mode else "#2E7D32"

        # Responsive velocity sizing based on viewport aspect & mode
        if self._is_orga_mode:
            vel_size = max(42, int(min(w * 0.10, h * 0.15)))
        else:
            vel_size = max(60, int(min(w * 0.17, h * 0.27)))

        unit_size = max(18, int(vel_size * 0.28))
        energy_size = max(26, int(vel_size * 0.38))
        sub_size = max(13, int(vel_size * 0.13))

        title_size = max(14, int(min(w * 0.015, h * 0.026)))
        btn_size = max(12, int(min(w * 0.012, h * 0.020)))
        hint_size = max(11, int(min(w * 0.011, h * 0.018)))

        self.lbl_title.setText(tr("hud_title"))
        self.lbl_title.setStyleSheet(f"""
            color: {accent};
            font-size: {title_size}px;
            font-weight: 800;
            letter-spacing: 2px;
            border: none;
            background: transparent;
        """)

        self.btn_toggle_mode.setStyleSheet(f"""
            QPushButton {{
                background-color: #161B22;
                color: {accent};
                border: 2px solid {accent};
                border-radius: 8px;
                padding: {max(4, int(h * 0.008))}px {max(10, int(w * 0.012))}px;
                font-size: {btn_size}px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {accent};
                color: #000000;
            }}
        """)

        self.lbl_hint.setText(tr("hud_exit_hint"))
        self.lbl_hint.setStyleSheet(f"""
            color: #8B949E;
            font-size: {hint_size}px;
            border: none;
            background: transparent;
            margin-left: 20px;
        """)

        self.lbl_vel.setStyleSheet(f"""
            color: {accent};
            font-size: {vel_size}px;
            font-weight: 900;
            font-family: Consolas, 'Courier New', monospace;
            border: none;
            background: transparent;
        """)

        self.lbl_unit.setStyleSheet(f"""
            color: {accent};
            font-size: {unit_size}px;
            font-weight: 700;
            font-family: 'Segoe UI', sans-serif;
            border: none;
            background: transparent;
            margin-bottom: {int(vel_size * 0.12)}px;
        """)

        self.lbl_energy.setStyleSheet(f"""
            color: #FFFFFF;
            font-size: {energy_size}px;
            font-weight: 700;
            font-family: 'Segoe UI', sans-serif;
            border: none;
            background: transparent;
        """)

        self.lbl_sub.setStyleSheet(f"""
            color: #8B949E;
            font-size: {sub_size}px;
            font-family: 'Segoe UI', sans-serif;
            border: none;
            background: transparent;
            margin-top: {int(h * 0.008)}px;
        """)

        # Auto-scale compliance cards
        if self._is_orga_mode:
            self._card_scale = min(w / 1920.0, h / 1080.0) * 1.05
        else:
            self._card_scale = min(w / 1920.0, h / 1080.0) * 1.3
        self.cards_layout.setSpacing(max(8, int(14 * self._card_scale)))

        shots = self._sm.active_session.shots
        vel = shots[-1].velocity if shots else 0.0
        for card in self._cards:
            card.update_velocity(vel, self._card_scale)

        # Joule Reference Grid columns & styling
        grid_cols = 10 if w >= 1100 else 5
        if getattr(self, "_current_grid_cols", None) != grid_cols:
            self._current_grid_cols = grid_cols
            weights = [(weight, f"{weight:.2f}g") for weight in STANDARD_BB_WEIGHTS]
            self.hud_joule_grid.set_weights(weights, columns=grid_cols)
            self._update_hud_joule_grid()

        grid_title_size = max(11, int(min(w * 0.011, h * 0.018)))
        active_accent = "#00E5FF" if self._dark_mode else "#00838F"
        self.lbl_hud_grid_title.setStyleSheet(f"""
            color: {active_accent};
            font-size: {grid_title_size}px;
            font-weight: 800;
            letter-spacing: 1px;
            border: none;
            background: transparent;
        """)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Escape, Qt.Key_F11):
            self.accept()
        elif event.key() == Qt.Key_Space:
            self._toggle_mode()
        else:
            super().keyPressEvent(event)
