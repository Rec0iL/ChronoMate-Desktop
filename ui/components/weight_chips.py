"""
ChronoMate Desktop - Weight chip bar
The row of weight chips used by Dashboard, Trajectory and Settings. It reads the list from
core.weights.available_weights(), wraps onto more lines when needed and marks the active weight.
"""

from typing import List

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QWidget

from core.config import ConfigManager
from core.weights import available_weights, is_selected, select_option
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
        self._options = available_weights(self._cfg)
        for opt in self._options:
            chip = QPushButton(opt.label.replace("&", "&&"))   # '&' would be read as a shortcut (H&N)
            chip.setObjectName("chip_btn")
            chip.setCheckable(True)
            chip.setProperty("weight", opt.weight)
            chip.setProperty("custom", "true" if opt.is_custom else "false")
            chip.setToolTip(opt.label)
            chip.clicked.connect(lambda _checked, o=opt: self._on_clicked(o))
            self._layout.addWidget(chip)
            self._chips.append(chip)
        self.set_active(self._cfg.selected_weight)
        self.updateGeometry()

    def _on_clicked(self, opt):
        select_option(self._cfg, opt)   # remembers which pellet, keeps PCP in step
        self._cfg.save()
        self.set_active(opt.weight)     # a click on the active chip must not un-check it
        self.weight_clicked.emit(opt.weight)

    def set_active(self, weight: float = None):
        """Mark the selected chip (the weight argument is kept for callers; the settings decide)."""
        for chip, opt in zip(self._chips, self._options):
            chip.setChecked(is_selected(self._cfg, opt))

    def chips(self) -> List[QPushButton]:
        return list(self._chips)
