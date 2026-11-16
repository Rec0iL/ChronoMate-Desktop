"""
ChronoMate Desktop - Weather & wind card
One card for both trajectory screens (airsoft BB and PCP). It edits the shared
ConfigManager.environment, so the weather is set once for both models.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QFrame, QGridLayout, QLabel

from core.config import ConfigManager
from core.i18n import tr


def _spin(lo, hi, value, decimals, step, suffix):
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(decimals)
    s.setSingleStep(step)
    s.setValue(value)
    s.setSuffix(f" {suffix}")
    s.setKeyboardTracking(False)
    return s


class EnvironmentCard(QFrame):
    changed = Signal()

    def __init__(self, parent=None, show_hint: bool = True):
        super().__init__(parent)
        self.setObjectName("card")
        self._cfg = ConfigManager.get_instance()
        env = self._cfg.environment
        g = QGridLayout(self)
        g.setContentsMargins(14, 12, 14, 12)
        g.setVerticalSpacing(8)
        self.lbl_title = QLabel(tr("pcp_card_environment"))
        self.lbl_title.setObjectName("section_title")
        g.addWidget(self.lbl_title, 0, 0, 1, 2)

        self.spin_temp = _spin(-30.0, 50.0, env.temperature_c, 1, 1.0, "°C")
        self.chk_altitude = QCheckBox(tr("pcp_use_altitude"))
        self.chk_altitude.setChecked(env.use_altitude)
        self.spin_pressure = _spin(600.0, 1100.0, env.pressure_hpa, 1, 1.0, "hPa")
        self.spin_altitude = _spin(-400.0, 5000.0, env.altitude_m, 0, 50.0, "m")
        self.spin_humidity = _spin(0.0, 100.0, env.humidity_pct, 0, 5.0, "%")
        self.spin_wind = _spin(0.0, 20.0, env.wind_speed_mps, 1, 0.5, "m/s")
        self.spin_clock = _spin(1.0, 12.0, env.wind_clock if env.wind_clock >= 1 else 12.0, 1, 0.5, tr("pcp_oclock"))
        self.spin_clock.setWrapping(True)

        rows = [("pcp_temperature", self.spin_temp), (None, self.chk_altitude),
                ("pcp_pressure", self.spin_pressure), ("pcp_altitude", self.spin_altitude),
                ("pcp_humidity", self.spin_humidity), ("pcp_wind_speed", self.spin_wind),
                ("pcp_wind_dir", self.spin_clock)]
        self._labels = {}
        for i, (key, w) in enumerate(rows, start=1):
            if key is None:
                g.addWidget(w, i, 0, 1, 2)
            else:
                lbl = QLabel(tr(key))
                self._labels[key] = lbl
                g.addWidget(lbl, i, 0)
                g.addWidget(w, i, 1)
        self.lbl_hint = QLabel(tr("pcp_wind_hint"))
        self.lbl_hint.setObjectName("label_secondary")
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setVisible(show_hint)
        g.addWidget(self.lbl_hint, len(rows) + 1, 0, 1, 2)

        for w in (self.spin_temp, self.spin_pressure, self.spin_altitude, self.spin_humidity,
                  self.spin_wind, self.spin_clock):
            w.valueChanged.connect(self._store)
        self.chk_altitude.toggled.connect(self._store)
        self._update_visibility()

    def _update_visibility(self):
        alt = self.chk_altitude.isChecked()
        self._labels["pcp_altitude"].setVisible(alt)
        self.spin_altitude.setVisible(alt)
        self._labels["pcp_pressure"].setVisible(not alt)
        self.spin_pressure.setVisible(not alt)

    def _store(self, *_):
        env = self._cfg.environment
        env.temperature_c = self.spin_temp.value()
        env.use_altitude = self.chk_altitude.isChecked()
        env.pressure_hpa = self.spin_pressure.value()
        env.altitude_m = self.spin_altitude.value()
        env.humidity_pct = self.spin_humidity.value()
        env.wind_speed_mps = self.spin_wind.value()
        env.wind_clock = self.spin_clock.value() % 12.0
        self._cfg.save()
        self._update_visibility()
        self.changed.emit()

    def reload(self):
        """Show the shared settings again (the other screen may have changed them)."""
        env = self._cfg.environment
        widgets = (self.spin_temp, self.chk_altitude, self.spin_pressure, self.spin_altitude,
                   self.spin_humidity, self.spin_wind, self.spin_clock)
        for w in widgets:
            w.blockSignals(True)
        self.spin_temp.setValue(env.temperature_c)
        self.chk_altitude.setChecked(env.use_altitude)
        self.spin_pressure.setValue(env.pressure_hpa)
        self.spin_altitude.setValue(env.altitude_m)
        self.spin_humidity.setValue(env.humidity_pct)
        self.spin_wind.setValue(env.wind_speed_mps)
        self.spin_clock.setValue(env.wind_clock if env.wind_clock >= 1 else 12.0)
        for w in widgets:
            w.blockSignals(False)
        self._update_visibility()

    def retranslate(self):
        self.lbl_title.setText(tr("pcp_card_environment"))
        for key, lbl in self._labels.items():
            lbl.setText(tr(key))
        self.chk_altitude.setText(tr("pcp_use_altitude"))
        self.lbl_hint.setText(tr("pcp_wind_hint"))
        self.spin_clock.setSuffix(f" {tr('pcp_oclock')}")
