"""
ChronoMate Desktop - Main Application Window
Coordinates sidebar navigation, view switching, poller signals,
audio triggers, and fullscreen HUD dialog.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
    QPushButton,
    QLabel,
    QFrame,
    QApplication,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QFont, QKeyEvent

from core.models import Shot, ConnectionState
from core.config import ConfigManager
from core.session_manager import SessionManager
from core.audio import AudioManager
from core.poller import ChronoPoller
from core.i18n import tr, I18n
from ui.theme import Theme
from ui.components.status_badge import StatusBadge
from ui.views.dashboard_view import DashboardView
from ui.views.orga_view import OrgaView
from ui.views.ballistics_view import BallisticsView
from ui.views.history_view import HistoryView
from ui.views.export_view import ExportView
from ui.views.settings_view import SettingsView
from ui.views.hud_dialog import HudDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChronoMate - Airsoft Ballistic Laboratory")
        self.resize(1180, 780)
        self.setMinimumSize(850, 550)

        self._cfg = ConfigManager.get_instance()
        self._sm = SessionManager.get_instance()
        self._audio = AudioManager.get_instance()
        self._hud_dialog: HudDialog = None

        # Apply initial language & theme
        I18n.set_language(self._cfg.language)
        self._audio.set_sound_type(self._cfg.sound_type)
        self._audio.set_volume(self._cfg.sound_volume)
        self._audio.set_muted(self._cfg.sound_muted)
        self._apply_theme(self._cfg.is_dark_mode)

        # Root Central Widget
        central_widget = QWidget(self)
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Sidebar Navigation
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(210)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 18, 12, 18)
        sidebar_layout.setSpacing(6)

        # Brand Header (Logo + App Name)
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        self.lbl_logo = QLabel()
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo.png"
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_logo.setPixmap(pix)
            self.setWindowIcon(QIcon(str(logo_path)))
        else:
            self.lbl_logo.setText("⚡")
            self.lbl_logo.setFont(QFont("Segoe UI", 18))

        self.lbl_app_name = QLabel("ChronoMate")
        self.lbl_app_name.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.lbl_app_name.setStyleSheet("color: #88FF11;" if self._cfg.is_dark_mode else "color: #2E7D32;")

        brand_row.addWidget(self.lbl_logo)
        brand_row.addWidget(self.lbl_app_name)
        brand_row.addStretch()
        sidebar_layout.addLayout(brand_row)

        sidebar_layout.addSpacing(18)

        # Navigation Buttons
        self.nav_buttons = []
        nav_items = [
            ("📊  " + tr("dashboard"), 0),
            ("🛡️  " + tr("orga_chrono"), 1),
            ("🏹  " + tr("trajectory"), 2),
            ("📋  " + tr("history"), 3),
            ("📄  " + tr("export"), 4),
            ("⚙️  " + tr("settings"), 5),
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("nav_btn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=index: self._navigate_to(idx))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Version at bottom of sidebar
        lbl_version = QLabel("ChronoMate Desktop v1.0")
        lbl_version.setObjectName("label_secondary")
        lbl_version.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(lbl_version)

        root_layout.addWidget(self.sidebar)

        # 2. Main Content Area (TopBar + Stacked Views)
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Top Bar
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(50)
        self.top_bar.setStyleSheet("border-bottom: 1px solid #21262D;" if self._cfg.is_dark_mode else "border-bottom: 1px solid #E0E0E0;")
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(20, 8, 20, 8)
        top_layout.setSpacing(12)

        self.lbl_page_title = QLabel(tr("dashboard"))
        self.lbl_page_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        top_layout.addWidget(self.lbl_page_title)
        top_layout.addStretch()

        # Demo Mode Toggle Button
        self.btn_demo = QPushButton("🎮 " + tr("demo_mode"))
        self.btn_demo.setObjectName("chip_btn")
        self.btn_demo.setCheckable(True)
        self.btn_demo.toggled.connect(self._on_demo_toggled)
        top_layout.addWidget(self.btn_demo)

        # Fullscreen HUD Button (F11)
        self.btn_hud = QPushButton("📺 " + tr("kiosk_hud"))
        self.btn_hud.setObjectName("chip_btn")
        self.btn_hud.clicked.connect(self.open_hud)
        top_layout.addWidget(self.btn_hud)

        # Theme Toggle Button
        self.btn_theme_toggle = QPushButton()
        self.btn_theme_toggle.setObjectName("theme_toggle_btn")
        self.btn_theme_toggle.setFixedSize(34, 28)
        self.btn_theme_toggle.setIcon(Theme.get_theme_icon(self._cfg.is_dark_mode))
        self.btn_theme_toggle.setIconSize(QSize(18, 18))
        self.btn_theme_toggle.setToolTip(tr("toggle_theme"))
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)
        top_layout.addWidget(self.btn_theme_toggle)

        # Status Badge
        self.status_badge = StatusBadge(dark_mode=self._cfg.is_dark_mode, parent=self)
        self.status_badge.clicked_reconnect.connect(self._reconnect_poller)
        top_layout.addWidget(self.status_badge)

        content_layout.addWidget(self.top_bar)

        # Stacked Views
        self.stack = QStackedWidget()
        self.dashboard_view = DashboardView(dark_mode=self._cfg.is_dark_mode, parent=self)
        self.orga_view = OrgaView(dark_mode=self._cfg.is_dark_mode, parent=self)
        self.ballistics_view = BallisticsView(dark_mode=self._cfg.is_dark_mode, parent=self)
        self.history_view = HistoryView(dark_mode=self._cfg.is_dark_mode, parent=self)
        self.export_view = ExportView(dark_mode=self._cfg.is_dark_mode, parent=self)
        self.settings_view = SettingsView(dark_mode=self._cfg.is_dark_mode, parent=self)

        # Connect inter-view signals
        self.settings_view.theme_changed.connect(self._apply_theme)
        self.settings_view.language_changed.connect(self._on_language_changed)
        self.settings_view.network_config_changed.connect(self._on_network_config_changed)
        self.settings_view.weight_type_changed.connect(self._on_weight_type_changed)
        self.settings_view.custom_weights_changed.connect(self._on_custom_weights_changed)
        self.settings_view.calibration_changed.connect(self._on_calibration_changed)

        self.dashboard_view.weight_changed.connect(self._on_weight_selected)
        self.ballistics_view.weight_changed.connect(self._on_weight_selected)
        self.history_view.session_changed.connect(self._on_session_changed)

        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.orga_view)
        self.stack.addWidget(self.ballistics_view)
        self.stack.addWidget(self.history_view)
        self.stack.addWidget(self.export_view)
        self.stack.addWidget(self.settings_view)

        content_layout.addWidget(self.stack, stretch=1)
        root_layout.addWidget(content_area, stretch=1)

        # Set default active navigation
        self._navigate_to(0)

        # Initialize and start background poller thread
        self.poller = ChronoPoller(self)
        self.poller.connection_changed.connect(self._on_connection_changed)
        self.poller.shot_detected.connect(self._on_shot_detected)
        self.poller.telemetry_updated.connect(self._on_telemetry_updated)
        self.poller.set_network_config(self._cfg.auto_ip_enabled, self._cfg.custom_ip, self._cfg.custom_port)
        self.poller.start()

    def _navigate_to(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        titles = [tr("dashboard"), tr("orga_chrono"), tr("trajectory"), tr("history"), tr("export"), tr("settings")]
        self.lbl_page_title.setText(titles[index])

        # Refresh relevant views when shown
        if index == 0:
            self.dashboard_view.refresh_stats()
        elif index == 1:
            self.orga_view.refresh()
        elif index == 2:
            self.ballistics_view.recalculate()
        elif index == 3:
            self.history_view.refresh()
        elif index == 4:
            self.export_view.refresh()

    def _on_connection_changed(self, state_str: str, error_msg: str):
        state = ConnectionState(state_str)
        self.status_badge.set_state(state, error_msg)

    def _on_shot_detected(self, raw_velocity: float):
        # If calibration recording is active, capture entry
        if self._cfg.is_calibration_active:
            self._cfg.add_calibration_entry(raw_velocity, None)
            self.settings_view.refresh_calibration_table()

        factor = self._cfg.get_compensation_factor()
        weight = self._cfg.selected_weight

        shot = Shot(
            raw_velocity=raw_velocity,
            weight_grams=weight,
            compensation_factor=factor,
        )
        self._sm.add_shot(shot)

        # Check over-joule for audio feedback
        max_joules = self._cfg.max_allowed_joule
        if shot.energy_joules > max_joules:
            self._audio.play_alert()
        else:
            self._audio.play_shot()

        # Update all active views
        self.dashboard_view.refresh_stats()
        self.orga_view.refresh()
        self.ballistics_view.update_from_new_shot(shot.velocity)
        self.history_view.refresh()
        self.export_view.refresh()

        if self._hud_dialog and self._hud_dialog.isVisible():
            self._hud_dialog.refresh()

    def _on_weight_type_changed(self, w_type_str: str):
        self.dashboard_view.rebuild_weight_chips()
        self.ballistics_view.rebuild_weight_chips()
        self.dashboard_view.refresh_stats()
        self.ballistics_view.recalculate()
        self.orga_view.refresh()

    def _on_custom_weights_changed(self):
        self.dashboard_view.rebuild_weight_chips()
        self.ballistics_view.rebuild_weight_chips()
        self.dashboard_view.refresh_stats()
        self.ballistics_view.recalculate()
        self.orga_view.refresh()

    def _on_weight_selected(self, weight: float):
        self.dashboard_view.set_active_weight(weight)
        self.ballistics_view.set_active_weight(weight)
        self.orga_view.refresh()

    def _on_calibration_changed(self, factor: float):
        self.dashboard_view.refresh_stats()
        self.orga_view.refresh()
        self.history_view.refresh()
        self.export_view.refresh()

    def _on_telemetry_updated(self, velocity_str: str, fire_rate_str: str):
        pass

    def _on_demo_toggled(self, checked: bool):
        self.poller.set_demo_mode(checked)

    def _reconnect_poller(self):
        self.poller.set_network_config(self._cfg.auto_ip_enabled, self._cfg.custom_ip, self._cfg.custom_port)

    def _on_network_config_changed(self, auto_ip: bool, custom_ip: str, custom_port: int):
        self.poller.set_network_config(auto_ip, custom_ip, custom_port)

    def _on_session_changed(self):
        self.dashboard_view.refresh_stats()
        self.orga_view.refresh()
        self.export_view.refresh()

    def _toggle_theme(self):
        new_dark = not self._cfg.is_dark_mode
        self._cfg.is_dark_mode = new_dark
        self._cfg.save()
        self.settings_view.chk_dark.setChecked(new_dark)
        self._apply_theme(new_dark)

    def _apply_theme(self, dark_mode: bool):
        qss = Theme.get_stylesheet(dark_mode)
        self.setStyleSheet(qss)
        if hasattr(self, "btn_theme_toggle"):
            self.btn_theme_toggle.setIcon(Theme.get_theme_icon(dark_mode))
        if hasattr(self, "lbl_app_name"):
            self.lbl_app_name.setStyleSheet("color: #88FF11;" if dark_mode else "color: #2E7D32;")
        if hasattr(self, "status_badge"):
            self.status_badge.set_theme(dark_mode)

        if hasattr(self, "dashboard_view"):
            self.dashboard_view.set_theme(dark_mode)
            self.orga_view.set_theme(dark_mode)
            self.ballistics_view.set_theme(dark_mode)
            self.history_view.set_theme(dark_mode)
            self.export_view.set_theme(dark_mode)

    def _on_language_changed(self, lang_code: str):
        I18n.set_language(lang_code)
        # Update sidebar texts
        nav_items = [
            ("📊  " + tr("dashboard"), 0),
            ("🛡️  " + tr("orga_chrono"), 1),
            ("🏹  " + tr("trajectory"), 2),
            ("📋  " + tr("history"), 3),
            ("📄  " + tr("export"), 4),
            ("⚙️  " + tr("settings"), 5),
        ]
        for (text, _), btn in zip(nav_items, self.nav_buttons):
            btn.setText(text)

        self.btn_demo.setText("🎮 " + tr("demo_mode"))
        self.btn_hud.setText("📺 " + tr("kiosk_hud"))
        self.btn_theme_toggle.setToolTip(tr("toggle_theme"))

        self.dashboard_view.retranslate()
        self.orga_view.retranslate()
        self.ballistics_view.retranslate()
        self.history_view.retranslate()
        self.export_view.retranslate()
        self._navigate_to(self.stack.currentIndex())

    def open_hud(self):
        self._hud_dialog = HudDialog(dark_mode=self._cfg.is_dark_mode, parent=self)
        self._hud_dialog.showFullScreen()
        self._hud_dialog.exec()
        self._hud_dialog = None

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_F11:
            self.open_hud()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.poller.stop()
        self.poller.wait(2500)
        self._cfg.save()
        event.accept()
