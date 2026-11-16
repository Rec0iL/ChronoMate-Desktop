"""
ChronoMate Desktop - Projectiles card (Settings)
One switch for the mode (Airsoft = BBs + hop-up trajectory, PCP = pellets & slugs + PCP calculator),
the chips to pick the weight, and per mode two lists: the *active* list (what the chips show,
sortable) and the *library* (BB weights or the pellet catalogue) to add from. The user's own
projectiles are always in the active list of their kind.
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout,
    QWidget, QSizePolicy,
)

from core.config import ConfigManager
from core.i18n import tr
from core.models import BallisticMode, CustomWeight
from core.pellets import ALL_CALIBERS, CALIBERS
from core.weights import (
    KIND_BB, KIND_PELLET, active_ids, restore_mode_selection, add_to_active, available_weights, delete_own, keep_selection_offered,
    library, mode_kind, move_active, new_own_id, normalize_active, own_by_id, remove_from_active, resolve,
)


def _amp(text: str) -> str:
    """'&' would be read as a keyboard shortcut on buttons (H&N)."""
    return text.replace("&", "&&")


class OwnProjectileDialog(QDialog):
    """Create or edit one of the user's own projectiles (a BB or a pellet / slug)."""

    def __init__(self, kind: str, cw: Optional[CustomWeight] = None, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setWindowTitle(tr("own_projectile_title"))
        form = QFormLayout(self)
        self.edit_name = QLineEdit(cw.name if cw else "")
        self.edit_name.setPlaceholderText(tr("own_projectile_name_hint"))
        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(0.05, 20.0)
        self.spin_weight.setDecimals(3)
        self.spin_weight.setSingleStep(0.01)
        self.spin_weight.setSuffix(" g")
        self.spin_weight.setValue(cw.weight if cw else (0.25 if kind == KIND_BB else 1.0))
        self.spin_caliber = QDoubleSpinBox()
        self.spin_caliber.setRange(4.0, 12.0)
        self.spin_caliber.setDecimals(2)
        self.spin_caliber.setSuffix(" mm")
        self.spin_caliber.setValue(cw.caliber if cw else (6.0 if kind == KIND_BB else 5.5))
        form.addRow(tr("custom_col_name"), self.edit_name)
        form.addRow(tr("custom_col_weight"), self.spin_weight)
        form.addRow(tr("custom_col_caliber"), self.spin_caliber)
        self.chk_bc = QCheckBox(tr("own_projectile_has_bc"))
        self.spin_bc = QDoubleSpinBox()
        self.spin_bc.setRange(0.005, 1.0)
        self.spin_bc.setDecimals(3)
        self.spin_bc.setSingleStep(0.001)
        self.spin_bc.setValue(cw.bc if cw and cw.bc else 0.030)
        self.combo_model = QComboBox()
        self.combo_model.addItems(["G1", "G7"])
        self.combo_model.setCurrentText(cw.drag_model if cw else "G1")
        self.chk_bc.setChecked(bool(cw and cw.bc))
        if kind == KIND_PELLET:
            form.addRow(self.chk_bc)
            form.addRow(tr("pcp_bc"), self.spin_bc)
            form.addRow(tr("pcp_drag_model"), self.combo_model)
            self.chk_bc.toggled.connect(lambda on: (self.spin_bc.setEnabled(on), self.combo_model.setEnabled(on)))
            self.spin_bc.setEnabled(self.chk_bc.isChecked())
            self.combo_model.setEnabled(self.chk_bc.isChecked())
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def apply_to(self, cw: CustomWeight):
        cw.name = self.edit_name.text().strip() or ("BB" if self.kind == KIND_BB else "Pellet")
        cw.weight = round(self.spin_weight.value(), 3)
        cw.caliber = self.spin_caliber.value()
        cw.caliber_unit = "mm"
        cw.kind = self.kind
        if self.kind == KIND_PELLET and self.chk_bc.isChecked():
            cw.bc, cw.drag_model = self.spin_bc.value(), self.combo_model.currentText()
        else:
            cw.bc = None


class ProjectilesCard(QFrame):
    changed = Signal()              # lists, own projectiles or the mode changed → rebuild every list
    mode_changed = Signal(str)      # BallisticMode value
    weight_selected = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._cfg = ConfigManager.get_instance()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        self.lbl_title = QLabel(tr("projectiles_title"))
        self.lbl_title.setObjectName("section_title")
        lay.addWidget(self.lbl_title)

        # One switch for both: projectile kind + trajectory model
        mode_row = QHBoxLayout()
        self.btn_airsoft = QPushButton()
        self.btn_pcp = QPushButton()
        for b, mode in ((self.btn_airsoft, BallisticMode.AIRSOFT), (self.btn_pcp, BallisticMode.PCP)):
            b.setCheckable(True)
            b.clicked.connect(lambda _c, m=mode: self.set_mode(m))
            mode_row.addWidget(b)
        lay.addLayout(mode_row)
        self.lbl_mode_hint = QLabel()
        self.lbl_mode_hint.setObjectName("label_secondary")
        self.lbl_mode_hint.setWordWrap(True)
        lay.addWidget(self.lbl_mode_hint)

        # Active list | library
        self.lbl_active = QLabel()
        self.lbl_active.setObjectName("section_title")
        lay.addWidget(self.lbl_active)
        self.list_active = QListWidget()
        self.list_active.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_active.setMinimumHeight(220)
        lay.addWidget(self.list_active)

        # Library, collapsed behind a chevron: the active list is what you work with
        self.btn_library = QPushButton()
        self.btn_library.setCheckable(True)
        self.btn_library.setObjectName("expander_btn")
        self.btn_library.toggled.connect(self._toggle_library)
        lay.addWidget(self.btn_library)
        self.library_box = QWidget()
        lists = QGridLayout(self.library_box)
        lists.setContentsMargins(0, 0, 0, 0)

        lib_filter = QHBoxLayout()
        self.edit_search = QLineEdit()
        self.edit_search.setClearButtonEnabled(True)
        self.edit_search.textChanged.connect(self._fill_library)
        self.combo_caliber = QComboBox()
        for key, mm in CALIBERS:
            self.combo_caliber.addItem(f"{mm:g} mm ({key})", key)
        self.combo_caliber.addItem(tr("all_calibers"), ALL_CALIBERS)
        self.combo_caliber.setCurrentIndex(max(0, self.combo_caliber.findData(self._cfg.library_caliber)))
        self.combo_caliber.currentIndexChanged.connect(self._on_caliber_changed)
        lib_filter.addWidget(self.edit_search, 1)
        lib_filter.addWidget(self.combo_caliber)
        lists.addLayout(lib_filter, 0, 0)
        self.list_library = QListWidget()
        self.list_library.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_library.setMinimumHeight(260)
        lists.addWidget(self.list_library, 1, 0)
        self.library_box.setVisible(False)
        lay.addWidget(self.library_box)

        self.btn_new_own = QPushButton()
        self.btn_new_own.clicked.connect(self._new_own)
        lay.addWidget(self.btn_new_own)

        self.retranslate()
        self.refresh()

    # --- mode -------------------------------------------------------------------------------------
    def set_mode(self, mode: BallisticMode):
        if mode != self._cfg.ballistic_mode:
            self._cfg.ballistic_mode = mode
            restore_mode_selection(self._cfg)
            self._cfg.save()
            self.refresh()
            self.mode_changed.emit(mode.value)
            self.changed.emit()
        self._update_mode_buttons()

    def _update_mode_buttons(self):
        pcp = self._cfg.ballistic_mode == BallisticMode.PCP
        self.btn_airsoft.setChecked(not pcp)
        self.btn_pcp.setChecked(pcp)
        self.lbl_mode_hint.setText(tr("mode_hint_pcp" if pcp else "mode_hint_airsoft"))
        self.combo_caliber.setVisible(pcp)

    # --- lists ------------------------------------------------------------------------------------
    def refresh(self):
        normalize_active(self._cfg)
        self._update_mode_buttons()
        self._fill_active()
        self._fill_library()

    def _row_widget(self, text: str, buttons):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(6, 2, 4, 2)
        h.setSpacing(4)
        lbl = QLabel(text)
        lbl.setToolTip(text)
        lbl.setMinimumWidth(40)
        lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)   # long names give way, buttons stay
        h.addWidget(lbl, 1)
        for glyph, tip, slot, enabled, danger in buttons:
            b = QPushButton(glyph)
            b.setProperty("compact", "true")
            if danger:
                b.setObjectName("danger_btn")
            b.setFixedSize(26, 24)
            b.setToolTip(tip)
            b.setEnabled(enabled)
            b.clicked.connect(slot)
            h.addWidget(b)
        return w

    def _fill_active(self):
        self.list_active.clear()
        ids = active_ids(self._cfg)
        for i, item_id in enumerate(ids):
            opt = resolve(self._cfg, item_id)
            if opt is None:
                continue
            text = ("★ " if opt.is_custom else "") + opt.label + self._bc_suffix(opt)
            buttons = [
                ("▲", tr("move_up"), lambda _c, x=item_id: self._move(x, -1), i > 0, False),
                ("▼", tr("move_down"), lambda _c, x=item_id: self._move(x, +1), i < len(ids) - 1, False),
            ]
            if opt.is_custom:
                buttons += [("✎", tr("own_projectile_edit"), lambda _c, x=item_id: self._edit_own(x), True, False),
                            ("✕", tr("delete"), lambda _c, x=item_id: self._delete_own(x), True, True)]
            else:
                buttons.append(("✕", tr("remove_from_active"), lambda _c, x=item_id: self._remove(x), len(ids) > 1, True))
            item = QListWidgetItem(self.list_active)
            row = self._row_widget(text, buttons)
            item.setSizeHint(row.sizeHint())
            self.list_active.setItemWidget(item, row)

    def _fill_library(self, *_):
        self.list_library.clear()
        kind = mode_kind(self._cfg)
        active = set(active_ids(self._cfg))
        for opt in library(self._cfg, kind, self._cfg.library_caliber, self.edit_search.text()):
            added = opt.id in active
            text = opt.label + self._bc_suffix(opt)
            item = QListWidgetItem(self.list_library)
            row = self._row_widget(text, [("✓" if added else "+", tr("in_active") if added else tr("add_to_active"),
                                           lambda _c, x=opt.id: self._add(x), not added, False)])
            item.setSizeHint(row.sizeHint())
            self.list_library.setItemWidget(item, row)

    @staticmethod
    def _bc_suffix(opt) -> str:
        p = opt.pellet
        if p is None:
            return ""
        return f"  · BC ≈{p.bc:.3f}" if p.bc is not None else f"  · {tr('pcp_bc_unknown')}"

    def _changed(self):
        self._cfg.save()
        self.refresh()
        self.changed.emit()

    def _add(self, item_id: str):
        add_to_active(self._cfg, item_id)
        self._changed()

    def _remove(self, item_id: str):
        remove_from_active(self._cfg, item_id)
        self._changed()

    def _move(self, item_id: str, step: int):
        move_active(self._cfg, item_id, step)
        self._changed()

    def _new_own(self):
        kind = mode_kind(self._cfg)
        dlg = OwnProjectileDialog(kind, None, self)
        if dlg.exec() == QDialog.Accepted:
            cw = CustomWeight(name="", weight=0.25, id=new_own_id())
            dlg.apply_to(cw)
            self._cfg.custom_weights.append(cw)
            normalize_active(self._cfg)
            self._changed()

    def _edit_own(self, item_id: str):
        cw = own_by_id(self._cfg, item_id[4:])
        if cw is None:
            return
        dlg = OwnProjectileDialog(cw.kind, cw, self)
        if dlg.exec() == QDialog.Accepted:
            dlg.apply_to(cw)
            if self._cfg.selected_item == item_id:
                self._cfg.selected_weight = cw.weight
            self._changed()

    def _delete_own(self, item_id: str):
        cw = own_by_id(self._cfg, item_id[4:])
        if cw is None:
            return
        if QMessageBox.question(self, tr("delete"), tr("own_projectile_confirm_delete", cw.name),
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            delete_own(self._cfg, cw.id)
            self._changed()

    def _toggle_library(self, open_: bool):
        self.library_box.setVisible(open_)
        self._update_library_button()

    def _update_library_button(self):
        arrow = "▾" if self.btn_library.isChecked() else "▸"
        self.btn_library.setText(f"{arrow}  {tr('library_title')}")

    def _on_caliber_changed(self, _idx: int):
        self._cfg.library_caliber = self.combo_caliber.currentData()
        self._cfg.save()
        self._fill_library()

    def set_active_weight(self, _weight: float = None):
        pass   # the weight is picked on Dashboard / Orga / Trajectory, not here

    def retranslate(self):
        self.lbl_title.setText(tr("projectiles_title"))
        self.btn_airsoft.setText(_amp(tr("mode_airsoft")))
        self.btn_pcp.setText(_amp(tr("mode_pcp")))
        self.lbl_active.setText(tr("active_list_title"))
        self._update_library_button()
        self.edit_search.setPlaceholderText(tr("library_search"))
        self.combo_caliber.setItemText(self.combo_caliber.count() - 1, tr("all_calibers"))
        self.btn_new_own.setText(f"+ {tr('own_projectile_new')}")
        self._update_mode_buttons()
        self._fill_active()
        self._fill_library()
