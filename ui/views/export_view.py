"""
ChronoMate Desktop - Export View
Generate professional PDF reports, CSV files, and Excel (XLSX) datasets.
"""

from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSlider,
    QPushButton,
    QFrame,
    QFileDialog,
    QMessageBox,
    QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.session_manager import SessionManager
from core.exporter import Exporter
from core.i18n import tr


class ExportView(QWidget):
    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self._dark_mode = dark_mode
        self._sm = SessionManager.get_instance()

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # Title & Description
        self.lbl_title = QLabel(tr("export_session"))
        self.lbl_title.setObjectName("page_title")
        layout.addWidget(self.lbl_title)

        self.lbl_desc = QLabel(tr("export_desc"))
        self.lbl_desc.setObjectName("label_secondary")
        layout.addWidget(self.lbl_desc)

        # Settings Card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(14)

        self.lbl_card_title = QLabel(tr("report_settings"))
        self.lbl_card_title.setObjectName("section_title")
        card_layout.addWidget(self.lbl_card_title)

        # Gun Name
        lbl_gun = QLabel(tr("gun_name_label"))
        lbl_gun.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.edit_gun = QLineEdit()
        self.edit_gun.setPlaceholderText("e.g. Tokyo Marui MK18 Mod 1")
        card_layout.addWidget(lbl_gun)
        card_layout.addWidget(self.edit_gun)

        # Player Callsign
        lbl_player = QLabel(tr("player_name_label"))
        lbl_player.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.edit_player = QLineEdit()
        self.edit_player.setPlaceholderText("e.g. Ghost / Call-sign #42")
        card_layout.addWidget(lbl_player)
        card_layout.addWidget(self.edit_player)

        # Shot Count Slider
        slider_hdr = QHBoxLayout()
        lbl_shots = QLabel(tr("shots_to_include") + ":")
        lbl_shots.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_shot_count = QLabel("0")
        self.lbl_shot_count.setFont(QFont("Consolas, Courier New", 12, QFont.Bold))
        self.lbl_shot_count.setStyleSheet("color: #88FF11;")
        slider_hdr.addWidget(lbl_shots)
        slider_hdr.addStretch()
        slider_hdr.addWidget(self.lbl_shot_count)
        card_layout.addLayout(slider_hdr)

        self.slider_shots = QSlider(Qt.Horizontal)
        self.slider_shots.setRange(1, 1)
        self.slider_shots.setValue(1)
        self.slider_shots.valueChanged.connect(self._on_slider_changed)
        card_layout.addWidget(self.slider_shots)

        layout.addWidget(card)

        # Export Action Buttons Row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_pdf = QPushButton(f"📄 {tr('generate_pdf')}")
        self.btn_pdf.setObjectName("primary_btn")
        self.btn_pdf.setFixedHeight(40)
        self.btn_pdf.clicked.connect(self._export_pdf)
        btn_layout.addWidget(self.btn_pdf)

        self.btn_csv = QPushButton(f"📊 {tr('export_csv')}")
        self.btn_csv.setFixedHeight(40)
        self.btn_csv.clicked.connect(self._export_csv)
        btn_layout.addWidget(self.btn_csv)

        self.btn_xlsx = QPushButton(f"📈 {tr('export_xlsx')}")
        self.btn_xlsx.setFixedHeight(40)
        self.btn_xlsx.clicked.connect(self._export_xlsx)
        btn_layout.addWidget(self.btn_xlsx)

        layout.addLayout(btn_layout)

        # Summary Info Card
        self.info_card = QFrame()
        self.info_card.setObjectName("card")
        info_layout = QVBoxLayout(self.info_card)
        info_layout.setContentsMargins(16, 12, 16, 12)
        self.lbl_summary = QLabel("No shots available in current session.")
        self.lbl_summary.setFont(QFont("Segoe UI", 10))
        info_layout.addWidget(self.lbl_summary)
        layout.addWidget(self.info_card)

        layout.addStretch()
        scroll.setWidget(container)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        self.refresh()

    def _on_slider_changed(self, val: int):
        self.lbl_shot_count.setText(str(val))
        self._update_summary(val)

    def _get_export_shots(self) -> list:
        all_shots = self._sm.active_session.shots
        count = self.slider_shots.value()
        return all_shots[-count:] if all_shots else []

    def _get_stats(self, shots: list) -> dict:
        if not shots:
            return {}
        vels = [s.velocity for s in shots]
        avg = sum(vels) / len(vels)
        max_v = max(vels)
        min_v = min(vels)
        es = max_v - min_v
        sd = (sum((v - avg) ** 2 for v in vels) / len(vels)) ** 0.5 if len(vels) > 1 else 0.0
        return {"avg": avg, "max": max_v, "min": min_v, "es": es, "sd": sd, "rof": "0.0"}

    def _update_summary(self, count: int):
        shots = self._get_export_shots()
        if not shots:
            self.lbl_summary.setText("No shots in current session.")
            return

        stats = self._get_stats(shots)
        gun = self.edit_gun.text().strip() or "Standard Gun"
        self.lbl_summary.setText(
            f"Ready to export {len(shots)} shots for '{gun}'\n"
            f"Average: {stats.get('avg', 0.0):.1f} m/s  |  Max: {stats.get('max', 0.0):.1f} m/s  |  "
            f"Min: {stats.get('min', 0.0):.1f} m/s  |  Extreme Spread: {stats.get('es', 0.0):.1f} m/s"
        )

    def _export_pdf(self):
        shots = self._get_export_shots()
        if not shots:
            QMessageBox.warning(self, "Export", "No shots to export.")
            return

        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        gun_clean = "".join(c for c in self.edit_gun.text() if c.isalnum() or c in "_-")
        default_name = f"ChronoMate_{gun_clean}_{date_str}.pdf" if gun_clean else f"ChronoMate_Report_{date_str}.pdf"

        file_path, _ = QFileDialog.getSaveFileName(self, "Export PDF Report", default_name, "PDF Files (*.pdf)")
        if file_path:
            stats = self._get_stats(shots)
            if Exporter.export_pdf(Path(file_path), shots, self.edit_gun.text(), self.edit_player.text(), stats):
                QMessageBox.information(self, "Export Successful", f"PDF Report saved to:\n{file_path}")

    def _export_csv(self):
        shots = self._get_export_shots()
        if not shots:
            QMessageBox.warning(self, "Export", "No shots to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "ChronoMate_Session.csv", "CSV Files (*.csv)")
        if file_path:
            if Exporter.export_csv(Path(file_path), shots, self.edit_gun.text(), self.edit_player.text()):
                QMessageBox.information(self, "Export Successful", f"CSV file saved to:\n{file_path}")

    def _export_xlsx(self):
        shots = self._get_export_shots()
        if not shots:
            QMessageBox.warning(self, "Export", "No shots to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Export Excel", "ChronoMate_Session.xlsx", "Excel Files (*.xlsx)")
        if file_path:
            stats = self._get_stats(shots)
            if Exporter.export_xlsx(Path(file_path), shots, self.edit_gun.text(), self.edit_player.text(), stats):
                QMessageBox.information(self, "Export Successful", f"Excel workbook saved to:\n{file_path}")

    def refresh(self):
        total = len(self._sm.active_session.shots)
        self.slider_shots.setMaximum(max(1, total))
        self.slider_shots.setValue(max(1, min(10, total)))
        self.lbl_shot_count.setText(str(self.slider_shots.value()))
        self._update_summary(self.slider_shots.value())

    def set_theme(self, dark_mode: bool):
        self._dark_mode = dark_mode

    def retranslate(self):
        self.lbl_title.setText(tr("export_session"))
        self.lbl_desc.setText(tr("export_desc"))
        self.lbl_card_title.setText(tr("report_settings"))
        self.btn_pdf.setText(f"📄 {tr('generate_pdf')}")
        self.btn_csv.setText(f"📊 {tr('export_csv')}")
        self.btn_xlsx.setText(f"📈 {tr('export_xlsx')}")
        self.refresh()
