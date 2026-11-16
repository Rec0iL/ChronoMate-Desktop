"""
ChronoMate Desktop - Weight chip bar
The row of weight chips used by Dashboard, Trajectory and Settings. It reads the list from
core.weights.available_weights(), wraps onto more lines when needed and marks the active weight.
"""

from typing import List

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QWidget

from core.config import ConfigManager
from core.weights import available_weights, same_weight
from ui.components.flow_layout import FlowLayout


class WeightChipBar(QWidget):
    weight_clicked = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg = ConfigManager.get_instance()
        self._layout = FlowLayout(self, spacing=6)
        self._chips: List[QPushButton] = []
        self.rebuild()

    def rebuild(self):
        self._layout.clear()
        self._chips.clear()
        for opt in available_weights(self._cfg):
            chip = QPushButton(opt.label)
            chip.setObjectName("chip_btn")
            chip.setCheckable(True)
            chip.setProperty("weight", opt.weight)
            chip.setProperty("custom", "true" if opt.is_custom else "false")
            chip.setToolTip(opt.label)
            chip.clicked.connect(lambda _checked, w=opt.weight: self._on_clicked(w))
            self._layout.addWidget(chip)
            self._chips.append(chip)
        self.set_active(self._cfg.selected_weight)
        self.updateGeometry()

    def _on_clicked(self, weight: float):
        self.set_active(weight)   # a click on the active chip must not un-check it
        self.weight_clicked.emit(weight)

    def set_active(self, weight: float):
        for chip in self._chips:
            chip.setChecked(same_weight(float(chip.property("weight")), weight))

    def chips(self) -> List[QPushButton]:
        return list(self._chips)
