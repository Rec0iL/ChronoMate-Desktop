"""
ChronoMate Desktop - Responsive layout helpers
Pages lay themselves out by window width instead of forcing a horizontal scrollbar:
- ResponsiveGrid: as many columns as fit (between min_cols and max_cols), equal widths;
- ResponsiveRow: side by side when wide, stacked when narrower than a threshold.
"""

from typing import List

from PySide6.QtWidgets import QBoxLayout, QGridLayout, QLayout, QSizePolicy, QWidget


class ResponsiveGrid(QWidget):
    def __init__(self, min_col_width: int = 360, max_cols: int = 2, min_cols: int = 1, spacing: int = 12, parent=None):
        super().__init__(parent)
        self._min_col_width = min_col_width
        self._max_cols = max_cols
        self._min_cols = min_cols
        self._items: List[QWidget] = []
        self._cols = -1
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(spacing)
        # The grid must not insist on its current column count, or the page could never shrink
        # back to fewer columns: its minimum is one column, everything else follows the width.
        self._grid.setSizeConstraint(QLayout.SetNoConstraint)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(min_col_width)

    def set_min_col_width(self, w: int):
        self._min_col_width = max(40, int(w))
        self.setMinimumWidth(self._min_col_width)
        self._relayout(force=True)

    def set_max_cols(self, n: int):
        self._max_cols = max(1, n)
        self._relayout(force=True)

    def add_widget(self, w: QWidget):
        self._items.append(w)
        self._relayout(force=True)

    def clear(self):
        while self._grid.count():
            self._grid.takeAt(0)
        for w in self._items:
            w.hide()
            w.setParent(None)
            w.deleteLater()
        self._items.clear()
        self._cols = -1

    def widgets(self) -> List[QWidget]:
        return list(self._items)

    def columns(self) -> int:
        return max(1, self._cols)

    def _wanted_cols(self) -> int:
        width = self.width() if self.width() > 0 else self._min_col_width * self._max_cols
        spacing = self._grid.spacing()
        fit = max(1, (width + spacing) // (self._min_col_width + spacing))
        return int(max(self._min_cols, min(self._max_cols, fit)))

    def _relayout(self, force: bool = False):
        cols = self._wanted_cols()
        if cols == self._cols and not force:
            return
        self._cols = cols
        while self._grid.count():
            self._grid.takeAt(0)
        for i, w in enumerate(self._items):
            self._grid.addWidget(w, i // cols, i % cols)
            w.show()
        if self._items:   # height: tallest item of each row (the layout no longer sets it for us)
            rows = [self._items[r:r + cols] for r in range(0, len(self._items), cols)]
            height = sum(max(x.sizeHint().height() for x in row) for row in rows)
            self.setMinimumHeight(height + (len(rows) - 1) * self._grid.spacing())
        for c in range(max(self._grid.columnCount(), cols)):
            self._grid.setColumnStretch(c, 1 if c < cols else 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def hasHeightForWidth(self):
        return False


class ResponsiveRow(QWidget):
    """Children side by side (with stretch factors) when at least `threshold` px wide, else stacked."""

    def __init__(self, threshold: int = 900, spacing: int = 12, parent=None):
        super().__init__(parent)
        self._threshold = threshold
        self._box = QBoxLayout(QBoxLayout.LeftToRight, self)
        self._box.setContentsMargins(0, 0, 0, 0)
        self._box.setSpacing(spacing)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def add_widget(self, w: QWidget, stretch: int = 1):
        self._box.addWidget(w, stretch)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        wide = self.width() >= self._threshold
        want = QBoxLayout.LeftToRight if wide else QBoxLayout.TopToBottom
        if self._box.direction() != want:
            self._box.setDirection(want)
