"""
ChronoMate Desktop - Orga Chrono View
Airsoft field marshaling station:
Shows actual velocity (m/s) and energy (J), and automatically evaluates
compliance for ALL weapon classes (BACKUP, AR, LMG, DMR, SNIPER, etc.) simultaneously.
"""

from typing import List, Tuple, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QDialog,
    QLineEdit,
    QDoubleSpinBox,
    QFormLayout,
    QDialogButtonBox,
    QMenu,
    QMessageBox,
    QApplication,
)
from PySide6.QtCore import Qt, Signal, QMimeData, QPoint
from PySide6.QtGui import QFont, QColor, QDrag, QPixmap

from core.models import (
    WeaponClass,
    WeightType,
    STANDARD_BB_WEIGHTS,
    STANDARD_DIABLO_WEIGHTS,
    DEFAULT_WEAPON_CLASSES,
)
from core.config import ConfigManager
from core.session_manager import SessionManager
from core.i18n import tr
from ui.components.joule_grid import JouleGrid


class WeaponClassDialog(QDialog):
    def __init__(self, wc: Optional[WeaponClass] = None, can_delete: bool = False, parent=None):
        super().__init__(parent)
        self.wc = wc
        self.is_edit = (wc is not None)
        self.deleted = False

        self.setWindowTitle(tr("dialog_edit_weapon_class") if self.is_edit else tr("dialog_add_weapon_class"))
        self.setFixedWidth(360)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        form = QFormLayout()

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("e.g. HPA, SMG, CQB")
        if wc:
            self.edit_name.setText(wc.name)

        self.spin_joules = QDoubleSpinBox()
        self.spin_joules.setRange(0.1, 10.0)
        self.spin_joules.setSingleStep(0.05)
        self.spin_joules.setValue(wc.max_joules if wc else 1.50)
        self.spin_joules.setSuffix(" J")

        self.edit_desc = QLineEdit()
        self.edit_desc.setPlaceholderText(tr("description_label"))
        if wc:
            self.edit_desc.setText(wc.description)

        form.addRow(tr("class_name_label"), self.edit_name)
        form.addRow(tr("max_joules_label"), self.spin_joules)
        form.addRow(tr("description_label"), self.edit_desc)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        if self.is_edit and can_delete:
            self.btn_delete = QPushButton(f"🗑️ {tr('delete')}")
            self.btn_delete.setCursor(Qt.PointingHandCursor)
            self.btn_delete.setStyleSheet("""
                QPushButton {
                    color: #F44336;
                    border: 1px solid #F44336;
                    background: transparent;
                    padding: 4px 10px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(244, 67, 54, 0.15);
                }
            """)
            self.btn_delete.clicked.connect(self._on_delete)
            btn_row.addWidget(self.btn_delete)

        btn_row.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        btn_row.addWidget(buttons)
        layout.addLayout(btn_row)

    def _on_delete(self):
        class_name = self.edit_name.text().strip() or (self.wc.name if self.wc else "")
        reply = QMessageBox.question(
            self,
            tr("delete"),
            tr("confirm_delete_class", class_name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.deleted = True
            self.accept()

    def get_weapon_class(self) -> WeaponClass:
        return WeaponClass(
            name=self.edit_name.text().strip().upper() or "CUSTOM",
            max_joules=self.spin_joules.value(),
            description=self.edit_desc.text().strip(),
        )


class AddWeaponClassDialog(WeaponClassDialog):
    """Backwards-compatible alias for WeaponClassDialog in add mode."""
    def __init__(self, parent=None):
        super().__init__(wc=None, can_delete=False, parent=parent)


class ClassComplianceCard(QFrame):
    clicked = Signal(object)
    edit_requested = Signal(object)
    reorder_requested = Signal(str, str)  # (source_name, target_name)

    def __init__(self, wc: WeaponClass, dark_mode: bool = True, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.weapon_class = wc
        self._dark_mode = dark_mode
        self._is_active = is_active
        self._latest_velocity = 0.0
        self._drag_start_pos = None
        self._is_dragging = False
        self._is_drop_target = False

        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignCenter)

        # Top row: Left Drag Handle, center Active Badge, right Edit button
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(0)

        self.lbl_drag_handle = QLabel("⋮⋮")
        self.lbl_drag_handle.setFixedSize(20, 20)
        self.lbl_drag_handle.setAlignment(Qt.AlignCenter)
        self.lbl_drag_handle.setCursor(Qt.SizeAllCursor)
        self.lbl_drag_handle.setToolTip(tr("drag_to_reorder"))

        self.lbl_active_badge = QLabel(f"★ {tr('active_reference')}")
        self.lbl_active_badge.setFont(QFont("Segoe UI", 8, QFont.Bold))
        self.lbl_active_badge.setAlignment(Qt.AlignCenter)
        sp = self.lbl_active_badge.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.lbl_active_badge.setSizePolicy(sp)
        self.lbl_active_badge.setVisible(is_active)

        self.btn_edit = QPushButton("✎")
        self.btn_edit.setFixedSize(20, 20)
        self.btn_edit.setCursor(Qt.PointingHandCursor)
        self.btn_edit.setToolTip(tr("edit_weapon_class"))
        self.btn_edit.clicked.connect(lambda: self.edit_requested.emit(self.weapon_class))

        top_row.addWidget(self.lbl_drag_handle)
        top_row.addWidget(self.lbl_active_badge, stretch=1)
        top_row.addWidget(self.btn_edit)
        layout.addLayout(top_row)

        self.setToolTip(tr("active_ref_tooltip"))

        self.lbl_name = QLabel(f"{wc.name}")
        self.lbl_name.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.lbl_name.setAlignment(Qt.AlignCenter)

        self.lbl_limit = QLabel(f"≤ {wc.max_joules:.2f} J")
        self.lbl_limit.setFont(QFont("Consolas, Courier New", 10))
        self.lbl_limit.setObjectName("label_secondary")
        self.lbl_limit.setAlignment(Qt.AlignCenter)

        self.lbl_status = QLabel(tr("awaiting_shot"))
        self.lbl_status.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.lbl_status.setAlignment(Qt.AlignCenter)

        self.lbl_margin = QLabel("--")
        self.lbl_margin.setFont(QFont("Segoe UI", 9))
        self.lbl_margin.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.lbl_name)
        layout.addWidget(self.lbl_limit)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.lbl_margin)

        self.update_velocity(0.0)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            self._is_dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_start_pos is not None:
            pt = event.position().toPoint() if hasattr(event, "position") else event.pos()
            if (pt - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                self._is_dragging = True
                self._start_drag()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._is_dragging:
                self.clicked.emit(self.weapon_class)
            self._is_dragging = False
            self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def _start_drag(self):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData("application/x-chronomate-weapon-class", self.weapon_class.name.encode("utf-8"))
        drag.setMimeData(mime)

        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(self._drag_start_pos if self._drag_start_pos else QPoint(pixmap.width() // 2, pixmap.height() // 2))

        drag.exec(Qt.MoveAction)
        self._is_dragging = False
        self._drag_start_pos = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-chronomate-weapon-class"):
            event.acceptProposedAction()
            self._is_drop_target = True
            self._apply_border_style()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-chronomate-weapon-class"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._is_drop_target = False
        self._apply_border_style()
        event.accept()

    def dropEvent(self, event):
        self._is_drop_target = False
        self._apply_border_style()
        if event.mimeData().hasFormat("application/x-chronomate-weapon-class"):
            source_name = bytes(event.mimeData().data("application/x-chronomate-weapon-class")).decode("utf-8")
            if source_name != self.weapon_class.name:
                self.reorder_requested.emit(source_name, self.weapon_class.name)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _apply_border_style(self):
        if self._is_drop_target:
            accent = "#00E5FF" if self._dark_mode else "#00838F"
            bg = "rgba(0, 229, 255, 0.22)" if self._dark_mode else "rgba(0, 131, 143, 0.18)"
            self.setStyleSheet(f"""
                ClassComplianceCard {{
                    background-color: {bg};
                    border: 2.5px dashed {accent};
                    border-radius: 8px;
                }}
                QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
        else:
            self.update_velocity(self._latest_velocity)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.edit_requested.emit(self.weapon_class)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        act_edit = menu.addAction(f"✏️ {tr('edit_weapon_class')}")
        act_set_ref = menu.addAction(f"★ {tr('active_reference')}")
        action = menu.exec(event.globalPos())
        if action == act_edit:
            self.edit_requested.emit(self.weapon_class)
        elif action == act_set_ref:
            self.clicked.emit(self.weapon_class)

    def set_active(self, is_active: bool):
        self._is_active = is_active
        self.lbl_active_badge.setVisible(is_active)
        self.lbl_active_badge.setText(f"★ {tr('active_reference')}")
        self.setToolTip(tr("active_ref_tooltip"))
        self.update_velocity(self._latest_velocity)

    def update_velocity(self, velocity: float):
        self._latest_velocity = velocity
        active_accent = "#00E5FF" if self._dark_mode else "#00838F"
        self.lbl_active_badge.setStyleSheet(f"color: {active_accent}; letter-spacing: 0.5px;")

        if velocity <= 0.0:
            bg = "#161B22" if self._dark_mode else "#F0F2F5"
            border = active_accent if self._is_active else ("#30363D" if self._dark_mode else "#D0D7DE")
            self.lbl_name.setStyleSheet("color: #F0F6FC;" if self._dark_mode else "color: #1F2328;")
            self.lbl_status.setText(tr("awaiting_shot"))
            self.lbl_status.setStyleSheet("color: #8B949E;")
            self.lbl_margin.setText("--")
            self.lbl_margin.setStyleSheet("color: #8B949E;")
        else:
            # Energy at minimum standard 0.20g BB
            e_20 = 0.5 * 0.00020 * (velocity ** 2)
            max_w_grams = (2.0 * self.weapon_class.max_joules / (velocity ** 2)) * 1000.0

            if e_20 <= self.weapon_class.max_joules:
                # Legal at 0.20g
                bg = "rgba(46, 125, 50, 0.28)" if self._dark_mode else "rgba(46, 125, 50, 0.15)"
                border = active_accent if self._is_active else ("#2E7D32" if self._dark_mode else "#4CAF50")
                accent = "#88FF11" if self._dark_mode else "#1B5E20"

                self.lbl_name.setStyleSheet(f"color: {accent};")
                self.lbl_status.setText(f"{tr('legal')} ✓")
                self.lbl_status.setStyleSheet(f"color: {accent}; font-weight: bold;")
                self.lbl_margin.setText(tr("max_bb_weight_label", max_w_grams))
                self.lbl_margin.setStyleSheet(f"color: {accent};")
            else:
                # Over Limit even at 0.20g
                bg = "rgba(244, 67, 54, 0.28)" if self._dark_mode else "rgba(244, 67, 54, 0.15)"
                border = active_accent if self._is_active else ("#F44336" if self._dark_mode else "#C62828")
                danger = "#F44336" if self._dark_mode else "#C62828"

                self.lbl_name.setStyleSheet(f"color: {danger};")
                self.lbl_status.setText(f"{tr('illegal')} ✕")
                self.lbl_status.setStyleSheet(f"color: {danger}; font-weight: bold;")
                self.lbl_margin.setText(tr("exceeds_limit_20"))
                self.lbl_margin.setStyleSheet(f"color: {danger};")

        edit_hover = "rgba(0, 229, 255, 0.22)" if self._dark_mode else "rgba(0, 131, 143, 0.2)"
        edit_bg = "rgba(255, 255, 255, 0.06)" if self._dark_mode else "rgba(0, 0, 0, 0.04)"
        edit_border = "rgba(255, 255, 255, 0.1)" if self._dark_mode else "rgba(0, 0, 0, 0.1)"
        edit_color = "#8B949E" if self._dark_mode else "#57606A"
        self.btn_edit.setStyleSheet(f"""
            QPushButton {{
                background-color: {edit_bg};
                border: 1px solid {edit_border};
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
                color: {edit_color};
                padding: 0px;
            }}
            QPushButton:hover {{
                color: {active_accent};
                background-color: {edit_hover};
                border-color: {active_accent};
            }}
        """)

        handle_color = "#6E7681" if self._dark_mode else "#8C959F"
        self.lbl_drag_handle.setStyleSheet(f"color: {handle_color}; font-size: 13px; font-weight: bold; background: transparent;")

        border_w = "2.5px" if self._is_active else "1.5px"
        self.setStyleSheet(f"""
            ClassComplianceCard {{
                background-color: {bg};
                border: {border_w} solid {border};
                border-radius: 8px;
            }}
            ClassComplianceCard:hover {{
                border-color: {active_accent};
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)


class OrgaView(QWidget):
    def __init__(self, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self._dark_mode = dark_mode
        self._cfg = ConfigManager.get_instance()
        self._sm = SessionManager.get_instance()
        self._compliance_cards: List[ClassComplianceCard] = []

        # Find or default active weapon class for Joule Reference Grid
        self._active_weapon_class = None
        for wc in self._cfg.weapon_classes:
            if wc.name == self._cfg.selected_weapon_class:
                self._active_weapon_class = wc
                break
        if not self._active_weapon_class and self._cfg.weapon_classes:
            self._active_weapon_class = self._cfg.weapon_classes[0]

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # Title Row
        title_row = QHBoxLayout()
        self.lbl_title = QLabel(tr("orga_limits"))
        self.lbl_title.setObjectName("page_title")
        title_row.addWidget(self.lbl_title)
        title_row.addStretch()

        self.btn_reset_classes = QPushButton(f"↺ {tr('reset_weapon_classes')}")
        self.btn_reset_classes.setFixedHeight(28)
        self.btn_reset_classes.setCursor(Qt.PointingHandCursor)
        self.btn_reset_classes.clicked.connect(self._reset_weapon_classes)
        title_row.addWidget(self.btn_reset_classes)

        self.btn_add_class = QPushButton(tr("add_weapon_class"))
        self.btn_add_class.setFixedHeight(28)
        self.btn_add_class.setCursor(Qt.PointingHandCursor)
        self.btn_add_class.clicked.connect(self._add_weapon_class)
        title_row.addWidget(self.btn_add_class)
        layout.addLayout(title_row)

        # 1. Telemetry Card: Shows Actual Measured Velocity (m/s)
        telemetry_frame = QFrame()
        telemetry_frame.setObjectName("card")
        telemetry_layout = QHBoxLayout(telemetry_frame)
        telemetry_layout.setContentsMargins(24, 16, 24, 16)
        telemetry_layout.setSpacing(20)

        # Velocity Block
        vel_box = QVBoxLayout()
        vel_box.setSpacing(4)
        self.lbl_v_hdr = QLabel(tr("measured_velocity"))
        self.lbl_v_hdr.setObjectName("label_secondary")
        self.lbl_vel = QLabel("0.00 m/s")
        self.lbl_vel.setFont(QFont("Consolas, Courier New", 36, QFont.Bold))
        self.lbl_vel.setStyleSheet("color: #88FF11;" if dark_mode else "color: #2E7D32;")
        vel_box.addWidget(self.lbl_v_hdr)
        vel_box.addWidget(self.lbl_vel)
        telemetry_layout.addLayout(vel_box, stretch=1)

        layout.addWidget(telemetry_frame)

        # 2. Weapon Class Compliance Grid (Evaluates ALL classes simultaneously)
        self.lbl_compliance_hdr = QLabel(tr("compliance_board_title"))
        self.lbl_compliance_hdr.setObjectName("section_title")
        layout.addWidget(self.lbl_compliance_hdr)

        self.compliance_container = QGridLayout()
        self.compliance_container.setSpacing(10)
        layout.addLayout(self.compliance_container)

        # 3. Joule Reference Grid (Color-coded across BB weights)
        self.lbl_grid_title = QLabel(tr("joule_grid_title"))
        self.lbl_grid_title.setObjectName("section_title")
        layout.addWidget(self.lbl_grid_title)

        self.joule_grid = JouleGrid(dark_mode=dark_mode, parent=self)
        layout.addWidget(self.joule_grid)
        self.rebuild_joule_grid_weights()
        self.rebuild_compliance_cards()

        layout.addStretch()
        scroll.setWidget(container)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroll)

    def rebuild_compliance_cards(self):
        while self.compliance_container.count():
            item = self.compliance_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._compliance_cards.clear()

        # Ensure active weapon class is valid
        if self._active_weapon_class not in self._cfg.weapon_classes:
            self._active_weapon_class = None
            for wc in self._cfg.weapon_classes:
                if wc.name == self._cfg.selected_weapon_class:
                    self._active_weapon_class = wc
                    break
            if not self._active_weapon_class and self._cfg.weapon_classes:
                self._active_weapon_class = self._cfg.weapon_classes[0]

        active_name = self._active_weapon_class.name if self._active_weapon_class else ""

        classes = self._cfg.weapon_classes
        cols = 5
        for idx, wc in enumerate(classes):
            is_active = (wc.name == active_name)
            card = ClassComplianceCard(wc, dark_mode=self._dark_mode, is_active=is_active, parent=self)
            card.clicked.connect(self._on_card_clicked)
            card.edit_requested.connect(self._edit_weapon_class)
            card.reorder_requested.connect(self._on_reorder_classes)
            row = idx // cols
            col = idx % cols
            self.compliance_container.addWidget(card, row, col)
            self._compliance_cards.append(card)

        self.refresh()

    def _on_reorder_classes(self, source_name: str, target_name: str):
        classes = self._cfg.weapon_classes
        src_idx = next((i for i, c in enumerate(classes) if c.name == source_name), None)
        tgt_idx = next((i for i, c in enumerate(classes) if c.name == target_name), None)
        if src_idx is not None and tgt_idx is not None and src_idx != tgt_idx:
            item = classes.pop(src_idx)
            classes.insert(tgt_idx, item)
            self._cfg.save()
            self.rebuild_compliance_cards()

    def _on_card_clicked(self, wc: WeaponClass):
        self._active_weapon_class = wc
        self._cfg.selected_weapon_class = wc.name
        self._cfg.save()
        for card in self._compliance_cards:
            card.set_active(card.weapon_class.name == wc.name)
        self._update_joule_grid()

    def _edit_weapon_class(self, wc: WeaponClass):
        can_delete = len(self._cfg.weapon_classes) > 1
        dlg = WeaponClassDialog(wc=wc, can_delete=can_delete, parent=self)
        if dlg.exec() == QDialog.Accepted:
            if dlg.deleted:
                if wc in self._cfg.weapon_classes:
                    self._cfg.weapon_classes.remove(wc)
                if self._active_weapon_class == wc or (self._active_weapon_class and self._active_weapon_class.name == wc.name):
                    self._active_weapon_class = self._cfg.weapon_classes[0] if self._cfg.weapon_classes else None
                    self._cfg.selected_weapon_class = self._active_weapon_class.name if self._active_weapon_class else ""
                self._cfg.save()
                self.rebuild_compliance_cards()
            else:
                updated = dlg.get_weapon_class()
                old_name = wc.name
                wc.name = updated.name
                wc.max_joules = updated.max_joules
                wc.description = updated.description
                if self._cfg.selected_weapon_class == old_name:
                    self._cfg.selected_weapon_class = updated.name
                if self._active_weapon_class and self._active_weapon_class.name == old_name:
                    self._active_weapon_class = wc
                self._cfg.save()
                self.rebuild_compliance_cards()

    def _reset_weapon_classes(self):
        reply = QMessageBox.question(
            self,
            tr("reset_weapon_classes"),
            tr("confirm_reset_classes"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._cfg.weapon_classes = [
                WeaponClass(name=wc.name, max_joules=wc.max_joules, description=wc.description)
                for wc in DEFAULT_WEAPON_CLASSES
            ]
            self._cfg.selected_weapon_class = "AR"
            self._active_weapon_class = next(
                (c for c in self._cfg.weapon_classes if c.name == "AR"),
                self._cfg.weapon_classes[0] if self._cfg.weapon_classes else None
            )
            self._cfg.save()
            self.rebuild_compliance_cards()

    def _add_weapon_class(self):
        dlg = WeaponClassDialog(wc=None, can_delete=False, parent=self)
        if dlg.exec() == QDialog.Accepted:
            new_cls = dlg.get_weapon_class()
            self._cfg.weapon_classes.append(new_cls)
            self._active_weapon_class = new_cls
            self._cfg.selected_weapon_class = new_cls.name
            self._cfg.save()
            self.rebuild_compliance_cards()

    def rebuild_joule_grid_weights(self):
        # Orga view shows all weights (all standard weights 0.20g to 0.45g) so marshals have the complete spectrum
        weights: List[Tuple[float, str]] = [(w, f"{w:.2f}g") for w in STANDARD_BB_WEIGHTS]
        self.joule_grid.set_weights(weights, columns=5)
        self.refresh()

    def _update_joule_grid(self):
        shots = self._sm.active_session.shots
        latest_vel = shots[-1].velocity if shots else 0.0
        limit = self._active_weapon_class.max_joules if self._active_weapon_class else 1.50
        name = self._active_weapon_class.name if self._active_weapon_class else "AR"
        self.lbl_grid_title.setText(f"{tr('joule_grid_title')} — {name} (≤ {limit:.2f} J)")
        if hasattr(self, "joule_grid"):
            self.joule_grid.update_velocity(latest_vel, limit)

    def refresh(self):
        shots = self._sm.active_session.shots
        latest_vel = shots[-1].velocity if shots else 0.0

        self.lbl_vel.setText(f"{latest_vel:.2f} m/s" if latest_vel > 0 else "-- m/s")

        # Update ALL weapon class cards simultaneously based on measured velocity
        for card in self._compliance_cards:
            card.update_velocity(latest_vel)

        # Update Joule reference grid based on active weapon class
        self._update_joule_grid()

    def set_theme(self, dark_mode: bool):
        self._dark_mode = dark_mode
        accent = "#88FF11" if dark_mode else "#2E7D32"
        self.lbl_vel.setStyleSheet(f"color: {accent};")
        for card in self._compliance_cards:
            card._dark_mode = dark_mode
        self.joule_grid.set_theme(dark_mode)
        self.refresh()

    def retranslate(self):
        self.lbl_title.setText(tr("orga_limits"))
        self.btn_reset_classes.setText(f"↺ {tr('reset_weapon_classes')}")
        self.btn_add_class.setText(tr("add_weapon_class"))
        self.lbl_v_hdr.setText(tr("measured_velocity"))
        self.lbl_compliance_hdr.setText(tr("compliance_board_title"))
        self.rebuild_compliance_cards()
        self.rebuild_joule_grid_weights()
        self._update_joule_grid()
