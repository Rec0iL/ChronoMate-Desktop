"""
ChronoMate Desktop - History & Session Management View
Table of recorded shots, session naming, on-demand save/load, and shot deletion.
"""

from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from core.models import Shot
from core.session_manager import SessionManager
from core.config import ConfigManager
from core.i18n import tr


class HistoryView(QWidget):
    session_changed = Signal()

    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self._dark_mode = dark_mode
        self._sm = SessionManager.get_instance()
        self._cfg = ConfigManager.get_instance()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Title & Action Bar
        top_bar = QHBoxLayout()
        self.lbl_title = QLabel(tr("history"))
        self.lbl_title.setObjectName("page_title")
        top_bar.addWidget(self.lbl_title)
        top_bar.addStretch()

        self.btn_save_session = QPushButton(tr("save_session"))
        self.btn_save_session.clicked.connect(self._save_session)
        top_bar.addWidget(self.btn_save_session)

        self.btn_load_session = QPushButton(tr("load_session"))
        self.btn_load_session.clicked.connect(self._load_session)
        top_bar.addWidget(self.btn_load_session)

        self.btn_clear_shots = QPushButton(tr("clear_session"))
        self.btn_clear_shots.setObjectName("danger_btn")
        self.btn_clear_shots.clicked.connect(self._clear_session)
        top_bar.addWidget(self.btn_clear_shots)

        main_layout.addLayout(top_bar)

        # Session Details Card (Session Name, Gun Name)
        meta_card = QFrame()
        meta_card.setObjectName("card")
        meta_layout = QHBoxLayout(meta_card)
        meta_layout.setContentsMargins(14, 10, 14, 10)
        meta_layout.setSpacing(12)

        self.lbl_sname = QLabel(tr("session_name_label"))
        self.lbl_sname.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.edit_session_name = QLineEdit(self._sm.active_session.name)
        self.edit_session_name.textChanged.connect(self._on_name_changed)

        self.lbl_gun = QLabel(tr("gun_name_label") + ":")
        self.lbl_gun.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.edit_gun_name = QLineEdit(self._sm.active_session.gun_name)
        self.edit_gun_name.textChanged.connect(self._on_gun_changed)

        meta_layout.addWidget(self.lbl_sname)
        meta_layout.addWidget(self.edit_session_name, stretch=2)
        meta_layout.addWidget(self.lbl_gun)
        meta_layout.addWidget(self.edit_gun_name, stretch=2)

        main_layout.addWidget(meta_card)

        # Shots Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["#", "Timestamp", "Weight", "Velocity", "Energy"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(False)
        main_layout.addWidget(self.table, stretch=1)

        # Bottom Bar: Delete Selected Shot
        bot_bar = QHBoxLayout()
        self.btn_del_shot = QPushButton(tr("delete_selected_shot"))
        self.btn_del_shot.clicked.connect(self._delete_selected_shot)
        bot_bar.addWidget(self.btn_del_shot)

        self.lbl_count = QLabel(tr("total_shots", 0))
        self.lbl_count.setObjectName("label_secondary")
        bot_bar.addStretch()
        bot_bar.addWidget(self.lbl_count)
        main_layout.addLayout(bot_bar)

        self.refresh()

    def _on_name_changed(self, text: str):
        self._sm.active_session.name = text

    def _on_gun_changed(self, text: str):
        self._sm.active_session.gun_name = text

    def _save_session(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Session",
            str(self._sm.sessions_dir / f"{self._sm.active_session.name}.json"),
            "JSON Files (*.json)",
        )
        if file_path:
            if self._sm.save_session_to_file(Path(file_path)):
                QMessageBox.information(self, "Saved", f"Session saved successfully to:\n{file_path}")

    def _load_session(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Session",
            str(self._sm.sessions_dir),
            "JSON Files (*.json)",
        )
        if file_path:
            if self._sm.load_session_from_file(Path(file_path)):
                self.edit_session_name.setText(self._sm.active_session.name)
                self.edit_gun_name.setText(self._sm.active_session.gun_name)
                self.refresh()
                self.session_changed.emit()

    def _clear_session(self):
        reply = QMessageBox.question(
            self,
            "Clear Session",
            "Are you sure you want to clear all shots in the current session?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._sm.clear_shots()
            self.refresh()
            self.session_changed.emit()

    def _delete_selected_shot(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        total = len(self._sm.active_session.shots)
        # Table displays reverse chronological order
        shot_idx = total - 1 - row
        self._sm.remove_shot(shot_idx)
        self.refresh()
        self.session_changed.emit()

    def refresh(self):
        shots = self._sm.active_session.shots
        self.lbl_count.setText(tr("total_shots", len(shots)))

        self.table.setRowCount(len(shots))
        max_joules = self._cfg.max_allowed_joule

        # Display reversed (newest first)
        for row_idx, shot in enumerate(reversed(shots)):
            real_num = len(shots) - row_idx
            dt_str = datetime.fromtimestamp(shot.timestamp).strftime("%H:%M:%S")

            item_num = QTableWidgetItem(f"#{real_num:02d}")
            item_num.setTextAlignment(Qt.AlignCenter)

            item_time = QTableWidgetItem(dt_str)
            item_time.setTextAlignment(Qt.AlignCenter)

            item_w = QTableWidgetItem(f"{shot.weight_grams:.2f}g")
            item_w.setTextAlignment(Qt.AlignCenter)

            item_v = QTableWidgetItem(f"{shot.velocity:.2f} m/s")
            item_v.setTextAlignment(Qt.AlignCenter)

            item_e = QTableWidgetItem(f"{shot.energy_joules:.2f} J")
            item_e.setTextAlignment(Qt.AlignCenter)

            self.table.setItem(row_idx, 0, item_num)
            self.table.setItem(row_idx, 1, item_time)
            self.table.setItem(row_idx, 2, item_w)
            self.table.setItem(row_idx, 3, item_v)
            self.table.setItem(row_idx, 4, item_e)

    def set_theme(self, dark_mode: bool):
        self._dark_mode = dark_mode
        self.refresh()

    def retranslate(self):
        self.lbl_title.setText(tr("history"))
        self.lbl_sname.setText(tr("session_name_label"))
        self.lbl_gun.setText(tr("gun_name_label") + ":")
        self.btn_del_shot.setText(tr("delete_selected_shot"))
        self.btn_save_session.setText(tr("save_session"))
        self.btn_load_session.setText(tr("load_session"))
        self.btn_clear_shots.setText(tr("clear_session"))
        self.refresh()
