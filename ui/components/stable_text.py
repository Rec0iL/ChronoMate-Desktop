"""
ChronoMate Desktop - Stable text sizing
Labels whose text changes with every shot (LEGAL / ILLEGAL, "-- J" / "1.23 J") would make their
layout re-flow each time. reserve_text_space() sizes a label once for the widest text it can ever
show, so the cards and grids around it keep their place.
"""

from typing import Iterable
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QLabel, QSizePolicy



def text_width(font: QFont, texts: Iterable[str]) -> int:
    fm = QFontMetrics(font)
    return max((fm.horizontalAdvance(t) for t in texts), default=0)


def reserve_text_space(label: QLabel, texts: Iterable[str], font: QFont = None, padding: int = 6,
                       lines: int = 1):
    """Give `label` a fixed size that fits every text in `texts`.

    lines=1: the label is as wide as the widest text.
    lines>1: the text may wrap; the label reserves `lines` lines of height and only needs to be as
    wide as the longest single word, so long messages don't force wide cards.
    """
    texts = list(texts)
    f = font or label.font()
    if font is not None:
        label.setFont(font)
    fm = QFontMetrics(f)
    if lines > 1:
        label.setWordWrap(True)
        words = [w for t in texts for w in t.split()]
        label.setMinimumWidth(text_width(f, words) + padding)
    else:
        label.setMinimumWidth(text_width(f, texts) + padding)
    label.setFixedHeight(fm.lineSpacing() * lines + 2)
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
