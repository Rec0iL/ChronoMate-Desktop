"""
ChronoMate Desktop - Stable text sizing
Labels whose text changes with every shot (LEGAL / ILLEGAL, "-- J" / "1.23 J") would make their
layout re-flow each time. reserve_text_space() sizes a label once for the widest text it can ever
show, so the cards and grids around it keep their place.
"""

from typing import Iterable
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QLabel, QSizePolicy

SAMPLE_DIGITS = "88.88"   # widest digits in most fonts, used for numeric placeholders


def text_width(font: QFont, texts: Iterable[str]) -> int:
    fm = QFontMetrics(font)
    return max((fm.horizontalAdvance(t) for t in texts), default=0)


def reserve_text_space(label: QLabel, texts: Iterable[str], font: QFont = None, padding: int = 6):
    """Give `label` a fixed minimum size that fits every text in `texts`."""
    f = font or label.font()
    if font is not None:
        label.setFont(font)
    fm = QFontMetrics(f)
    label.setMinimumWidth(text_width(f, texts) + padding)
    label.setFixedHeight(fm.height() + 2)
    label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)


def equalize_widths(widgets):
    """All widgets get the minimum width of the widest one and ignore their own size hint,
    so grid / row cells share space evenly and never change when the content does."""
    widgets = list(widgets)
    if not widgets:
        return
    w = max(x.minimumSizeHint().width() for x in widgets)
    for x in widgets:
        x.setMinimumWidth(w)
        sp = x.sizePolicy()
        sp.setHorizontalPolicy(QSizePolicy.Ignored)
        x.setSizePolicy(sp)
