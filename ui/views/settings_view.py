"""
ChronoMate Desktop - Settings View
Customization of Theme, Language (EN/DE), Audio Effects, Network Auto/Manual IP,
Weight categories (BB / Diablo / Custom), Calibration & Reference shots, and Physics Constants.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QSlider,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
    QInputDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from core.models import (
    WeightType,
    ChronoType,
    CompensationMode,
    CustomWeight,
    CalibrationEntry,
    SoundType,
    STANDARD_BB_WEIGHTS,
    STANDARD_DIABLO_WEIGHTS,
)
from core.config import ConfigManager
from core.session_manager import SessionManager
from core.audio import AudioManager
from core.i18n import tr, I18n


class SettingsView(QWidget):
    theme_changed = Signal(bool)
    language_changed = Signal(str)
    network_config_changed = Signal(bool, str, int)
    weight_type_changed = Signal(str)
    custom_weights_changed = Signal()
    calibration_changed = Signal(float)  # Emits new compensation factor

    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self._dark_mode = dark_mode
        self._cfg = ConfigManager.get_instance()
        self._sm = SessionManager.get_instance()
        self._audio = AudioManager.get_instance()

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(18)

        # Title
        self.lbl_title = QLabel(tr("general_settings"))
        self.lbl_title.setObjectName("page_title")
        layout.addWidget(self.lbl_title)

        # 1. Appearance & Language Card
        app_card = QFrame()
        app_card.setObjectName("card")
        app_layout = QGridLayout(app_card)
        app_layout.setContentsMargins(16, 14, 16, 14)
        app_layout.setSpacing(12)

        # Dark Mode Switch
        self.chk_dark = QCheckBox(tr("dark_mode"))
        self.chk_dark.setChecked(self._cfg.is_dark_mode)
        self.chk_dark.toggled.connect(self._on_theme_toggled)
        app_layout.addWidget(self.chk_dark, 0, 0)

        lbl_dark_desc = QLabel(tr("dark_mode_desc"))
        lbl_dark_desc.setObjectName("label_secondary")
        app_layout.addWidget(lbl_dark_desc, 0, 1)

        # Language Selector
        lbl_lang = QLabel(tr("language") + ":")
        lbl_lang.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("English", "en")
        self.combo_lang.addItem("Deutsch", "de")
        idx = self.combo_lang.findData(self._cfg.language)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        self.combo_lang.currentIndexChanged.connect(self._on_lang_changed)

        app_layout.addWidget(lbl_lang, 1, 0)
        app_layout.addWidget(self.combo_lang, 1, 1)

        layout.addWidget(app_card)

        # 2. Audio Feedback Card
        audio_card = QFrame()
        audio_card.setObjectName("card")
        audio_layout = QGridLayout(audio_card)
        audio_layout.setContentsMargins(16, 14, 16, 14)
        audio_layout.setSpacing(12)

        lbl_audio_hdr = QLabel(tr("sound_effects"))
        lbl_audio_hdr.setObjectName("section_title")
        audio_layout.addWidget(lbl_audio_hdr, 0, 0, 1, 2)

        lbl_sound_type = QLabel(tr("sound_type_label") + ":")
        lbl_sound_type.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.combo_sound = QComboBox()
        self.combo_sound.addItem("Pew (Tactical Sweep)", SoundType.PEW.value)
        self.combo_sound.addItem("Beep (Electronic Chirp)", SoundType.BEEP.value)
        self.combo_sound.addItem("Plink (BB on Steel Target)", SoundType.PLINK.value)
        self.combo_sound.addItem("Mute (Silent)", SoundType.MUTE.value)

        sound_idx = self.combo_sound.findData(self._cfg.sound_type.value)
        if sound_idx >= 0:
            self.combo_sound.setCurrentIndex(sound_idx)
        self.combo_sound.currentIndexChanged.connect(self._on_sound_changed)

        self.btn_test_sound = QPushButton(f"▶ {tr('test_sound')}")
        self.btn_test_sound.clicked.connect(self._test_sound)

        audio_layout.addWidget(lbl_sound_type, 1, 0)
        sound_ctrl_row = QHBoxLayout()
        sound_ctrl_row.addWidget(self.combo_sound, stretch=2)
        sound_ctrl_row.addWidget(self.btn_test_sound, stretch=1)
        audio_layout.addLayout(sound_ctrl_row, 1, 1)

        # Volume Slider
        lbl_vol = QLabel(tr("sound_volume_label") + ":")
        lbl_vol.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.slider_vol = QSlider(Qt.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(int(self._cfg.sound_volume * 100))
        self.slider_vol.valueChanged.connect(self._on_volume_changed)

        audio_layout.addWidget(lbl_vol, 2, 0)
        audio_layout.addWidget(self.slider_vol, 2, 1)

        layout.addWidget(audio_card)

        # 3. Network & Chrono Connection Card
        net_card = QFrame()
        net_card.setObjectName("card")
        net_layout = QGridLayout(net_card)
        net_layout.setContentsMargins(16, 14, 16, 14)
        net_layout.setSpacing(12)

        lbl_net_hdr = QLabel("Chrono Connection & Network")
        lbl_net_hdr.setObjectName("section_title")
        net_layout.addWidget(lbl_net_hdr, 0, 0, 1, 2)

        # Chrono Model Selector
        lbl_model = QLabel("Chrono Model:")
        lbl_model.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.combo_model = QComboBox()
        self.combo_model.addItem(ChronoType.HT_X3000.display_name, ChronoType.HT_X3000.value)
        self.combo_model.addItem(ChronoType.HT_50.display_name, ChronoType.HT_50.value)
        idx_model = self.combo_model.findData(self._cfg.chrono_type.value)
        if idx_model >= 0:
            self.combo_model.setCurrentIndex(idx_model)
        self.combo_model.currentIndexChanged.connect(self._on_model_changed)
        net_layout.addWidget(lbl_model, 1, 0)
        net_layout.addWidget(self.combo_model, 1, 1)

        # Auto IP Switch
        self.chk_auto_ip = QCheckBox(tr("auto_ip") + " (Auto-scan 8.8.8.8, 192.168.4.1…)")
        self.chk_auto_ip.setChecked(self._cfg.auto_ip_enabled)
        self.chk_auto_ip.toggled.connect(self._on_auto_ip_toggled)
        net_layout.addWidget(self.chk_auto_ip, 2, 0, 1, 2)

        # Manual IP & Port Inputs
        self.lbl_ip = QLabel("Manual IP / Host:")
        self.lbl_ip.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.edit_ip = QLineEdit(self._cfg.custom_ip)
        self.edit_ip.textChanged.connect(self._on_manual_ip_changed)

        self.lbl_port = QLabel("Port:")
        self.lbl_port.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.spin_port = QDoubleSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setDecimals(0)
        self.spin_port.setValue(self._cfg.custom_port)
        self.spin_port.valueChanged.connect(self._on_manual_port_changed)

        manual_row = QHBoxLayout()
        manual_row.addWidget(self.edit_ip, stretch=3)
        manual_row.addWidget(self.lbl_port)
        manual_row.addWidget(self.spin_port, stretch=1)

        net_layout.addWidget(self.lbl_ip, 3, 0)
        net_layout.addLayout(manual_row, 3, 1)

        self._update_network_input_visibility()
        layout.addWidget(net_card)

        # 4. Weight Type & Custom Weights Table Card
        weight_card = QFrame()
        weight_card.setObjectName("card")
        weight_layout = QVBoxLayout(weight_card)
        weight_layout.setContentsMargins(16, 14, 16, 14)
        weight_layout.setSpacing(12)

        lbl_w_hdr = QLabel(tr("weight_config_title"))
        lbl_w_hdr.setObjectName("section_title")
        weight_layout.addWidget(lbl_w_hdr)

        # Weight type buttons
        w_type_row = QHBoxLayout()
        self.btn_bb = QPushButton(tr("weight_type_bbs"))
        self.btn_bb.setCheckable(True)
        self.btn_bb.setChecked(self._cfg.weight_type == WeightType.BB)
        self.btn_bb.clicked.connect(lambda: self._set_weight_type(WeightType.BB))

        self.btn_diablo = QPushButton(tr("weight_type_diablos"))
        self.btn_diablo.setCheckable(True)
        self.btn_diablo.setChecked(self._cfg.weight_type == WeightType.DIABLO)
        self.btn_diablo.clicked.connect(lambda: self._set_weight_type(WeightType.DIABLO))

        self.btn_custom = QPushButton(tr("weight_type_custom"))
        self.btn_custom.setCheckable(True)
        self.btn_custom.setChecked(self._cfg.weight_type == WeightType.CUSTOM)
        self.btn_custom.clicked.connect(lambda: self._set_weight_type(WeightType.CUSTOM))

        w_type_row.addWidget(self.btn_bb)
        w_type_row.addWidget(self.btn_diablo)
        w_type_row.addWidget(self.btn_custom)
        weight_layout.addLayout(w_type_row)

        # Custom Weights Table
        self.custom_table = QTableWidget()
        self.custom_table.setColumnCount(4)
        self.custom_table.setHorizontalHeaderLabels(["Name", "Weight (g)", "Caliber (mm)", "Action"])
        self.custom_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.custom_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.custom_table.setFixedHeight(140)
        weight_layout.addWidget(self.custom_table)

        btn_add_w = QPushButton(f"+ {tr('add_row_button')}")
        btn_add_w.clicked.connect(self._add_custom_weight)
        weight_layout.addWidget(btn_add_w)
        self._refresh_custom_weights_table()

        layout.addWidget(weight_card)

        # 5. Calibration & Reference Shots Card
        cal_card = QFrame()
        cal_card.setObjectName("card")
        cal_layout = QVBoxLayout(cal_card)
        cal_layout.setContentsMargins(16, 14, 16, 14)
        cal_layout.setSpacing(12)

        lbl_cal_hdr = QLabel(tr("calibration_title"))
        lbl_cal_hdr.setObjectName("section_title")
        cal_layout.addWidget(lbl_cal_hdr)

        lbl_cal_desc = QLabel(
            "Calibrate your chronograph against a trusted reference chronograph. "
            "Click 'Start Calibration' to auto-record chrono shots, or add reference shots manually."
        )
        lbl_cal_desc.setObjectName("label_secondary")
        lbl_cal_desc.setWordWrap(True)
        cal_layout.addWidget(lbl_cal_desc)

        # Calibration Controls Row (Start Recording, Add Pair, Import, Clear)
        cal_actions = QHBoxLayout()
        self.btn_record_cal = QPushButton("▶ " + tr("start_calibration"))
        self.btn_record_cal.setObjectName("primary_btn")
        self.btn_record_cal.clicked.connect(self._toggle_calibration_recording)
        cal_actions.addWidget(self.btn_record_cal)

        self.btn_add_cal_entry = QPushButton(tr("add_reference_pair"))
        self.btn_add_cal_entry.clicked.connect(self._add_manual_calibration_entry)
        cal_actions.addWidget(self.btn_add_cal_entry)

        self.btn_import_cal = QPushButton(tr("import_session_shots"))
        self.btn_import_cal.clicked.connect(self._import_session_shots)
        cal_actions.addWidget(self.btn_import_cal)

        self.btn_clear_cal = QPushButton(tr("clear_calibration"))
        self.btn_clear_cal.setObjectName("danger_btn")
        self.btn_clear_cal.clicked.connect(self._clear_calibration)
        cal_actions.addWidget(self.btn_clear_cal)

        cal_layout.addLayout(cal_actions)

        # Calibration Recording Status Banner
        self.lbl_cal_status = QLabel("")
        self.lbl_cal_status.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_cal_status.setVisible(False)
        cal_layout.addWidget(self.lbl_cal_status)

        # Compensation Mode & Current Factor
        comp_row = QHBoxLayout()
        lbl_comp = QLabel(tr("comp_mode_label") + ":")
        lbl_comp.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.combo_comp = QComboBox()
        self.combo_comp.addItem(tr("comp_mode_none"), CompensationMode.NONE.value)
        self.combo_comp.addItem(tr("comp_mode_median"), CompensationMode.MEDIAN.value)
        self.combo_comp.addItem(tr("comp_mode_external"), CompensationMode.TRUST_EXTERNAL.value)
        idx_comp = self.combo_comp.findData(self._cfg.compensation_mode.value)
        if idx_comp >= 0:
            self.combo_comp.setCurrentIndex(idx_comp)
        self.combo_comp.currentIndexChanged.connect(self._on_comp_mode_changed)

        comp_row.addWidget(lbl_comp)
        comp_row.addWidget(self.combo_comp, stretch=2)

        self.lbl_factor = QLabel(tr("comp_factor_display", self._cfg.get_compensation_factor()))
        self.lbl_factor.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.lbl_factor.setStyleSheet("color: #88FF11;")
        comp_row.addWidget(self.lbl_factor)

        cal_layout.addLayout(comp_row)

        # Calibration Entries Table
        self.cal_table = QTableWidget()
        self.cal_table.setColumnCount(5)
        self.cal_table.setHorizontalHeaderLabels([
            "#",
            "HT-X Chrono (m/s)",
            "Control Reference (m/s)",
            "Ratio (Ctrl/Chrono)",
            "Actions"
        ])
        self.cal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cal_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.cal_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.cal_table.setFixedHeight(180)
        self.cal_table.cellChanged.connect(self._on_cal_cell_changed)
        self.cal_table.cellDoubleClicked.connect(self._on_cal_double_clicked)
        cal_layout.addWidget(self.cal_table)
        self.refresh_calibration_table()

        layout.addWidget(cal_card)

        # 6. Ballistics Physics Constants Card
        phys_card = QFrame()
        phys_card.setObjectName("card")
        phys_layout = QGridLayout(phys_card)
        phys_layout.setContentsMargins(16, 14, 16, 14)
        phys_layout.setSpacing(12)

        lbl_phys_hdr = QLabel(tr("ballistics_engine_params"))
        lbl_phys_hdr.setObjectName("section_title")
        phys_layout.addWidget(lbl_phys_hdr, 0, 0, 1, 2)

        # Air density
        lbl_rho = QLabel("Air Density (rho, kg/m³):")
        self.spin_rho = QDoubleSpinBox()
        self.spin_rho.setRange(0.5, 2.0)
        self.spin_rho.setValue(self._cfg.air_density_rho)
        self.spin_rho.valueChanged.connect(lambda v: self._update_phys(air_density_rho=v))
        phys_layout.addWidget(lbl_rho, 1, 0)
        phys_layout.addWidget(self.spin_rho, 1, 1)

        # Drag Cw
        lbl_cw = QLabel("Drag Coefficient (Cw):")
        self.spin_cw = QDoubleSpinBox()
        self.spin_cw.setRange(0.1, 1.0)
        self.spin_cw.setSingleStep(0.01)
        self.spin_cw.setValue(self._cfg.drag_coefficient_cw)
        self.spin_cw.valueChanged.connect(lambda v: self._update_phys(drag_coefficient_cw=v))
        phys_layout.addWidget(lbl_cw, 2, 0)
        phys_layout.addWidget(self.spin_cw, 2, 1)

        # Magnus K
        lbl_k = QLabel("Magnus Coefficient (K):")
        self.spin_k = QDoubleSpinBox()
        self.spin_k.setRange(0.0001, 0.01)
        self.spin_k.setDecimals(4)
        self.spin_k.setSingleStep(0.0005)
        self.spin_k.setValue(self._cfg.magnus_coefficient_k)
        self.spin_k.valueChanged.connect(lambda v: self._update_phys(magnus_coefficient_k=v))
        phys_layout.addWidget(lbl_k, 3, 0)
        phys_layout.addWidget(self.spin_k, 3, 1)

        layout.addWidget(phys_card)
        layout.addStretch()

        scroll.setWidget(container)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _on_theme_toggled(self, checked: bool):
        self._cfg.is_dark_mode = checked
        self._cfg.save()
        self.theme_changed.emit(checked)

    def _on_lang_changed(self, idx: int):
        code = self.combo_lang.currentData()
        self._cfg.language = code
        self._cfg.save()
        I18n.set_language(code)
        self.language_changed.emit(code)
        self.retranslate()

    def _on_sound_changed(self, idx: int):
        val = self.combo_sound.currentData()
        st = SoundType(val)
        self._cfg.sound_type = st
        self._cfg.save()
        self._audio.set_sound_type(st)

    def _on_volume_changed(self, val: int):
        vol = val / 100.0
        self._cfg.sound_volume = vol
        self._cfg.save()
        self._audio.set_volume(vol)

    def _test_sound(self):
        val = self.combo_sound.currentData()
        st = SoundType(val)
        self._audio.play_test(st)

    def _on_model_changed(self, idx: int):
        val = self.combo_model.currentData()
        self._cfg.chrono_type = ChronoType(val)
        self._cfg.save()

    def _on_auto_ip_toggled(self, checked: bool):
        self._cfg.auto_ip_enabled = checked
        self._cfg.save()
        self._update_network_input_visibility()
        self.network_config_changed.emit(checked, self._cfg.custom_ip, self._cfg.custom_port)

    def _update_network_input_visibility(self):
        visible = not self.chk_auto_ip.isChecked()
        self.lbl_ip.setVisible(visible)
        self.edit_ip.setVisible(visible)
        self.lbl_port.setVisible(visible)
        self.spin_port.setVisible(visible)

    def _on_manual_ip_changed(self, text: str):
        self._cfg.custom_ip = text.strip()
        self._cfg.save()
        self.network_config_changed.emit(self._cfg.auto_ip_enabled, self._cfg.custom_ip, self._cfg.custom_port)

    def _on_manual_port_changed(self, val: float):
        self._cfg.custom_port = int(val)
        self._cfg.save()
        self.network_config_changed.emit(self._cfg.auto_ip_enabled, self._cfg.custom_ip, self._cfg.custom_port)

    def _set_weight_type(self, w_type: WeightType):
        self._cfg.weight_type = w_type

        # Adjust selected weight to fit new category
        if w_type == WeightType.BB:
            if self._cfg.selected_weight not in STANDARD_BB_WEIGHTS:
                self._cfg.selected_weight = 0.20
        elif w_type == WeightType.DIABLO:
            if self._cfg.selected_weight not in STANDARD_DIABLO_WEIGHTS:
                self._cfg.selected_weight = 0.50
        elif w_type == WeightType.CUSTOM:
            if self._cfg.custom_weights:
                self._cfg.selected_weight = self._cfg.custom_weights[0].weight
            else:
                self._cfg.selected_weight = 0.20

        self._cfg.save()
        self.btn_bb.setChecked(w_type == WeightType.BB)
        self.btn_diablo.setChecked(w_type == WeightType.DIABLO)
        self.btn_custom.setChecked(w_type == WeightType.CUSTOM)

        # Notify other views!
        self.weight_type_changed.emit(w_type.value)

    def _add_custom_weight(self):
        name, ok1 = QInputDialog.getText(self, "Add Custom Weight", "Weight Name:", text=f"Custom #{len(self._cfg.custom_weights)+1}")
        if not ok1 or not name:
            return
        weight, ok2 = QInputDialog.getDouble(self, "Add Custom Weight", "Weight in Grams (g):", value=0.25, minValue=0.01, maxValue=10.0, decimals=2)
        if not ok2:
            return

        cw = CustomWeight(name=name.strip(), weight=weight, caliber=6.0)
        self._cfg.custom_weights.append(cw)
        self._cfg.save()
        self._refresh_custom_weights_table()
        self.custom_weights_changed.emit()

    def _delete_custom_weight(self, index: int):
        if 0 <= index < len(self._cfg.custom_weights):
            self._cfg.custom_weights.pop(index)
            self._cfg.save()
            self._refresh_custom_weights_table()
            self.custom_weights_changed.emit()

    def _refresh_custom_weights_table(self):
        self.custom_table.setRowCount(len(self._cfg.custom_weights))
        for idx, cw in enumerate(self._cfg.custom_weights):
            self.custom_table.setItem(idx, 0, QTableWidgetItem(cw.name))
            self.custom_table.setItem(idx, 1, QTableWidgetItem(f"{cw.weight:.2f}"))
            self.custom_table.setItem(idx, 2, QTableWidgetItem(f"{cw.caliber:.2f}"))

            btn_del = QPushButton("✕")
            btn_del.setFixedWidth(28)
            btn_del.setObjectName("danger_btn")
            btn_del.clicked.connect(lambda _, i=idx: self._delete_custom_weight(i))
            self.custom_table.setCellWidget(idx, 3, btn_del)

    # --- Calibration System ---
    def _toggle_calibration_recording(self):
        self._cfg.is_calibration_active = not self._cfg.is_calibration_active
        if self._cfg.is_calibration_active:
            self.btn_record_cal.setText("■ " + tr("stop_calibration"))
            self.btn_record_cal.setObjectName("danger_btn")
            self.btn_record_cal.setStyleSheet("background-color: #F44336; color: #FFFFFF; font-weight: bold; padding: 6px 14px;")
            self.lbl_cal_status.setText("🔴 CALIBRATION RECORDING ACTIVE — Shoot through chronograph to log calibration shots automatically.")
            self.lbl_cal_status.setStyleSheet("color: #F44336; padding: 4px 0;")
            self.lbl_cal_status.setVisible(True)
        else:
            self.btn_record_cal.setText("▶ " + tr("start_calibration"))
            self.btn_record_cal.setObjectName("primary_btn")
            self.btn_record_cal.setStyleSheet("")
            self.lbl_cal_status.setVisible(False)

    def _add_manual_calibration_entry(self):
        chrono_val, ok1 = QInputDialog.getDouble(
            self,
            "Add Reference Shot Pair",
            "1. HT-X Chronograph Measured Speed (m/s):",
            value=100.0,
            minValue=10.0,
            maxValue=350.0,
            decimals=2,
        )
        if not ok1:
            return
        control_val, ok2 = QInputDialog.getDouble(
            self,
            "Add Reference Shot Pair",
            "2. Control Reference Chronograph Speed (m/s):",
            value=chrono_val,
            minValue=10.0,
            maxValue=350.0,
            decimals=2,
        )
        if not ok2:
            control_val = None

        self._cfg.add_calibration_entry(chrono_val, control_val)
        self.refresh_calibration_table()
        self._apply_calibration_update()

    def _import_session_shots(self):
        shots = self._sm.active_session.shots
        if not shots:
            QMessageBox.information(self, "No Shots", "Active session has no shots to import.\nShoot some rounds or enable Demo Mode first.")
            return

        # Import the latest up to 15 shots
        count = 0
        for s in shots[-15:]:
            self._cfg.add_calibration_entry(s.raw_velocity, None)
            count += 1

        self.refresh_calibration_table()
        QMessageBox.information(
            self,
            "Shots Imported",
            f"Successfully imported {count} shot(s) from current session!\n\n"
            "Now click 'Set Ref' on each shot or double-click to enter the reference chronograph velocity.",
        )

    def _prompt_set_control_ref(self, index: int):
        if not (0 <= index < len(self._cfg.calibration_entries)):
            return
        entry = self._cfg.calibration_entries[index]
        default_val = entry.control_value if entry.control_value is not None else entry.chrono_value

        val, ok = QInputDialog.getDouble(
            self,
            f"Set Reference Control Speed - Shot #{index+1}",
            f"HT-X Chrono Speed: {entry.chrono_value:.2f} m/s\n\nEnter Control Reference Chrono Speed (m/s):",
            value=default_val,
            minValue=10.0,
            maxValue=350.0,
            decimals=2,
        )
        if ok:
            self._cfg.update_calibration_control(index, val)
            self.refresh_calibration_table()
            self._apply_calibration_update()

    def _on_cal_double_clicked(self, row: int, col: int):
        # Open control entry prompt on double-click on any cell
        self._prompt_set_control_ref(row)

    def _clear_calibration(self):
        reply = QMessageBox.question(self, "Clear Calibration", "Remove all calibration entries?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._cfg.clear_calibration()
            self.refresh_calibration_table()
            self._apply_calibration_update()

    def _delete_cal_entry(self, index: int):
        self._cfg.remove_calibration_entry(index)
        self.refresh_calibration_table()
        self._apply_calibration_update()

    def refresh_calibration_table(self):
        self.cal_table.blockSignals(True)
        entries = self._cfg.calibration_entries
        self.cal_table.setRowCount(len(entries))

        for idx, entry in enumerate(entries):
            item_num = QTableWidgetItem(f"#{idx+1:02d}")
            item_num.setFlags(item_num.flags() & ~Qt.ItemIsEditable)
            item_num.setTextAlignment(Qt.AlignCenter)

            item_chrono = QTableWidgetItem(f"{entry.chrono_value:.2f}")
            item_chrono.setFlags(item_chrono.flags() & ~Qt.ItemIsEditable)
            item_chrono.setTextAlignment(Qt.AlignCenter)

            # Editable Control value
            ctrl_str = f"{entry.control_value:.2f}" if entry.control_value is not None else "Enter Control m/s"
            item_ctrl = QTableWidgetItem(ctrl_str)
            item_ctrl.setTextAlignment(Qt.AlignCenter)
            if entry.control_value is None:
                item_ctrl.setForeground(QColor("#FF9800"))
            else:
                item_ctrl.setForeground(QColor("#88FF11" if self._dark_mode else "#2E7D32"))
            item_ctrl.setToolTip("Click 'Set Ref' or double click cell to enter control reference speed")

            # Ratio
            if entry.control_value is not None and entry.chrono_value > 0:
                ratio = entry.control_value / entry.chrono_value
                ratio_str = f"{ratio:.4f}"
            else:
                ratio_str = "--"
            item_ratio = QTableWidgetItem(ratio_str)
            item_ratio.setFlags(item_ratio.flags() & ~Qt.ItemIsEditable)
            item_ratio.setTextAlignment(Qt.AlignCenter)

            # Action container with Set Ref & Delete
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)
            act_layout.setSpacing(6)

            btn_set_ref = QPushButton(tr("set_reference"))
            btn_set_ref.setFixedHeight(24)
            btn_set_ref.setStyleSheet("padding: 2px 8px; font-size: 11px;")
            btn_set_ref.clicked.connect(lambda _, i=idx: self._prompt_set_control_ref(i))

            btn_del = QPushButton("✕")
            btn_del.setFixedSize(24, 24)
            btn_del.setObjectName("danger_btn")
            btn_del.clicked.connect(lambda _, i=idx: self._delete_cal_entry(i))

            act_layout.addWidget(btn_set_ref)
            act_layout.addWidget(btn_del)

            self.cal_table.setItem(idx, 0, item_num)
            self.cal_table.setItem(idx, 1, item_chrono)
            self.cal_table.setItem(idx, 2, item_ctrl)
            self.cal_table.setItem(idx, 3, item_ratio)
            self.cal_table.setCellWidget(idx, 4, act_widget)

        self.cal_table.blockSignals(False)
        self.lbl_factor.setText(tr("comp_factor_display", self._cfg.get_compensation_factor()))

    def _on_cal_cell_changed(self, row: int, col: int):
        if col == 2:
            item = self.cal_table.item(row, col)
            if item:
                val_str = item.text().strip().replace("Enter Control m/s", "")
                try:
                    val = float(val_str) if val_str else None
                    self._cfg.update_calibration_control(row, val)
                except ValueError:
                    pass
                self.refresh_calibration_table()
                self._apply_calibration_update()

    def _on_comp_mode_changed(self, idx: int):
        val = self.combo_comp.currentData()
        self._cfg.compensation_mode = CompensationMode(val)
        self._cfg.save()
        self.lbl_factor.setText(tr("comp_factor_display", self._cfg.get_compensation_factor()))
        self._apply_calibration_update()

    def _apply_calibration_update(self):
        factor = self._cfg.get_compensation_factor()
        self._sm.update_compensation_factor(factor)
        self.calibration_changed.emit(factor)

    def _update_phys(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self._cfg, k, v)
        self._cfg.save()

    def retranslate(self):
        self.lbl_title.setText(tr("general_settings"))
        self.chk_dark.setText(tr("dark_mode"))
        self.btn_test_sound.setText(f"▶ {tr('test_sound')}")
        self.btn_record_cal.setText("■ " + tr("stop_calibration") if self._cfg.is_calibration_active else "▶ " + tr("start_calibration"))
        self.btn_add_cal_entry.setText(tr("add_reference_pair"))
        self.btn_import_cal.setText(tr("import_session_shots"))
        self.btn_clear_cal.setText(tr("clear_calibration"))
        self.lbl_factor.setText(tr("comp_factor_display", self._cfg.get_compensation_factor()))
        self.refresh_calibration_table()
