"""
ChronoMate Desktop - Theme & Style System
Provides Tactical Dark (default) and High-Contrast Light QSS stylesheets and color palettes.
"""

import math
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QPen, QPainterPath
from PySide6.QtCore import Qt, QPointF, QRectF


class Theme:
    # --- Dark Theme Palette (Tactical HUD / Cyberpunk) ---
    DARK_BG = "#0D1117"
    DARK_SURFACE = "#161B22"
    DARK_SURFACE_HOVER = "#21262D"
    DARK_SURFACE_ACTIVE = "#30363D"
    DARK_BORDER = "#30363D"
    DARK_TEXT_PRIMARY = "#F0F6FC"
    DARK_TEXT_SECONDARY = "#8B949E"
    DARK_TEXT_MUTED = "#484F58"

    # Accents
    DARK_ACCENT_PRIMARY = "#88FF11"     # Tactical Chrono Electric Green
    DARK_ACCENT_SECONDARY = "#4CAF50"
    DARK_WARNING = "#FF9800"            # Limit orange
    DARK_DANGER = "#F44336"             # Over limit red
    DARK_CYAN = "#00E5FF"
    DARK_BLUE = "#2196F3"

    # --- Light Theme Palette ---
    LIGHT_BG = "#F4F6F8"
    LIGHT_SURFACE = "#FFFFFF"
    LIGHT_SURFACE_HOVER = "#F0F2F5"
    LIGHT_SURFACE_ACTIVE = "#E4E7EB"
    LIGHT_BORDER = "#D0D7DE"
    LIGHT_TEXT_PRIMARY = "#1F2328"
    LIGHT_TEXT_SECONDARY = "#656D76"
    LIGHT_TEXT_MUTED = "#8C959F"

    LIGHT_ACCENT_PRIMARY = "#2E7D32"    # Forest green
    LIGHT_ACCENT_SECONDARY = "#388E3C"
    LIGHT_WARNING = "#E65100"
    LIGHT_DANGER = "#C62828"
    LIGHT_CYAN = "#00838F"
    LIGHT_BLUE = "#1976D2"

    @classmethod
    def get_color(cls, name: str, dark: bool = True) -> QColor:
        mapping = {
            "bg": cls.DARK_BG if dark else cls.LIGHT_BG,
            "surface": cls.DARK_SURFACE if dark else cls.LIGHT_SURFACE,
            "surface_hover": cls.DARK_SURFACE_HOVER if dark else cls.LIGHT_SURFACE_HOVER,
            "border": cls.DARK_BORDER if dark else cls.LIGHT_BORDER,
            "text": cls.DARK_TEXT_PRIMARY if dark else cls.LIGHT_TEXT_PRIMARY,
            "text_sec": cls.DARK_TEXT_SECONDARY if dark else cls.LIGHT_TEXT_SECONDARY,
            "accent": cls.DARK_ACCENT_PRIMARY if dark else cls.LIGHT_ACCENT_PRIMARY,
            "accent_sec": cls.DARK_ACCENT_SECONDARY if dark else cls.LIGHT_ACCENT_SECONDARY,
            "warning": cls.DARK_WARNING if dark else cls.LIGHT_WARNING,
            "danger": cls.DARK_DANGER if dark else cls.LIGHT_DANGER,
            "cyan": cls.DARK_CYAN if dark else cls.LIGHT_CYAN,
        }
        return QColor(mapping.get(name, cls.DARK_ACCENT_PRIMARY if dark else cls.LIGHT_ACCENT_PRIMARY))

    @classmethod
    def get_theme_icon(cls, is_dark_mode: bool, size: int = 24) -> QIcon:
        """
        Generates a vector-rendered high-DPI QIcon for Sun (dark mode -> switch to light)
        or Moon (light mode -> switch to dark) so that it renders crisp and reliably
        on all operating systems without relying on system emoji fonts.
        """
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        center = size / 2.0

        if is_dark_mode:
            # Sun icon for switching to light mode: vibrant golden sun with radiant rays
            color = QColor("#FFD600")
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawEllipse(QPointF(center, center), size * 0.24, size * 0.24)
            pen = QPen(color, 1.8, Qt.SolidLine, Qt.RoundCap)
            p.setPen(pen)
            for i in range(8):
                angle = i * (math.pi / 4.0)
                x1 = center + (size * 0.36) * math.cos(angle)
                y1 = center + (size * 0.36) * math.sin(angle)
                x2 = center + (size * 0.47) * math.cos(angle)
                y2 = center + (size * 0.47) * math.sin(angle)
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        else:
            # Moon icon for switching to dark mode: sleek crescent moon in deep blue / slate
            color = QColor("#0288D1")
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            path1 = QPainterPath()
            path1.addEllipse(QRectF(size * 0.12, size * 0.12, size * 0.76, size * 0.76))
            path2 = QPainterPath()
            path2.addEllipse(QRectF(size * 0.30, size * 0.05, size * 0.70, size * 0.70))
            crescent = path1.subtracted(path2)
            p.drawPath(crescent)

        p.end()
        return QIcon(pix)

    @classmethod
    def get_stylesheet(cls, dark: bool = True) -> str:
        if dark:
            return f"""
                QMainWindow, QDialog, QWidget#central_widget {{
                    background-color: {cls.DARK_BG};
                    color: {cls.DARK_TEXT_PRIMARY};
                    font-size: 13px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                }}
                
                QWidget {{
                    color: {cls.DARK_TEXT_PRIMARY};
                }}

                QFrame#card, QWidget#card {{
                    background-color: {cls.DARK_SURFACE};
                    border: 1px solid {cls.DARK_BORDER};
                    border-radius: 10px;
                }}

                QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
                    background-color: {cls.DARK_BG};
                    border: none;
                }}

                QFrame#hero_card {{
                    background-color: #0b0e14;
                    border: 1px solid #1f2937;
                    border-radius: 12px;
                }}

                /* Scrollbars */
                QScrollBar:vertical {{
                    border: none;
                    background: {cls.DARK_BG};
                    width: 8px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: {cls.DARK_BORDER};
                    min-height: 20px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: {cls.DARK_SURFACE_ACTIVE};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}

                /* Buttons */
                QPushButton {{
                    background-color: {cls.DARK_SURFACE_HOVER};
                    color: {cls.DARK_TEXT_PRIMARY};
                    border: 1px solid {cls.DARK_BORDER};
                    border-radius: 6px;
                    padding: 7px 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {cls.DARK_SURFACE_ACTIVE};
                    border-color: {cls.DARK_ACCENT_PRIMARY};
                    color: {cls.DARK_ACCENT_PRIMARY};
                }}
                QPushButton:pressed {{
                    background-color: #1a222d;
                }}
                QPushButton:disabled {{
                    background-color: {cls.DARK_SURFACE};
                    color: {cls.DARK_TEXT_MUTED};
                    border-color: {cls.DARK_BORDER};
                }}

                QPushButton#primary_btn {{
                    background-color: {cls.DARK_ACCENT_PRIMARY};
                    color: #000000;
                    border: none;
                    font-weight: 700;
                }}
                QPushButton#primary_btn:hover {{
                    background-color: #9dff38;
                    color: #000000;
                }}

                QPushButton#danger_btn {{
                    background-color: rgba(244, 67, 54, 0.15);
                    color: {cls.DARK_DANGER};
                    border: 1px solid rgba(244, 67, 54, 0.3);
                }}
                QPushButton#danger_btn:hover {{
                    background-color: rgba(244, 67, 54, 0.25);
                }}

                /* Chip Buttons */
                QPushButton#chip_btn {{
                    background-color: {cls.DARK_SURFACE};
                    border: 1px solid {cls.DARK_BORDER};
                    border-radius: 12px;
                    padding: 3px 8px;
                    font-size: 11px;
                }}
                QPushButton#chip_btn:hover {{
                    border-color: {cls.DARK_ACCENT_PRIMARY};
                }}
                QPushButton#chip_btn:checked {{
                    background-color: rgba(136, 255, 17, 0.15);
                    border: 1px solid {cls.DARK_ACCENT_PRIMARY};
                    color: {cls.DARK_ACCENT_PRIMARY};
                    font-weight: 700;
                }}

                QPushButton#theme_toggle_btn {{
                    padding: 0px;
                    min-width: 0px;
                }}

                /* LineEdit & Input */
                QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                    background-color: #0a0d12;
                    border: 1px solid {cls.DARK_BORDER};
                    border-radius: 6px;
                    color: {cls.DARK_TEXT_PRIMARY};
                    padding: 6px 10px;
                }}
                QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
                    border: 1px solid {cls.DARK_ACCENT_PRIMARY};
                }}

                /* Labels */
                QLabel#section_title {{
                    font-size: 15px;
                    font-weight: 700;
                    color: {cls.DARK_ACCENT_PRIMARY};
                    letter-spacing: 0.5px;
                }}
                QLabel#page_title {{
                    font-size: 20px;
                    font-weight: 800;
                    color: {cls.DARK_TEXT_PRIMARY};
                }}
                QLabel#label_secondary {{
                    color: {cls.DARK_TEXT_SECONDARY};
                    font-size: 11px;
                    text-transform: uppercase;
                    letter-spacing: 0.8px;
                }}

                /* Sliders */
                QSlider::groove:horizontal {{
                    border: none;
                    height: 5px;
                    background: {cls.DARK_SURFACE_ACTIVE};
                    border-radius: 2px;
                }}
                QSlider::sub-page:horizontal {{
                    background: {cls.DARK_ACCENT_PRIMARY};
                    border-radius: 2px;
                }}
                QSlider::handle:horizontal {{
                    background: #FFFFFF;
                    border: 2px solid {cls.DARK_ACCENT_PRIMARY};
                    width: 14px;
                    margin-top: -5px;
                    margin-bottom: -5px;
                    border-radius: 7px;
                }}
                QSlider::handle:horizontal:hover {{
                    background: {cls.DARK_ACCENT_PRIMARY};
                }}

                /* Tables */
                QTableWidget {{
                    background-color: {cls.DARK_SURFACE};
                    border: 1px solid {cls.DARK_BORDER};
                    border-radius: 8px;
                    gridline-color: rgba(48, 54, 61, 0.4);
                    selection-background-color: rgba(136, 255, 17, 0.15);
                    selection-color: {cls.DARK_TEXT_PRIMARY};
                }}
                QHeaderView::section {{
                    background-color: #0b0e14;
                    color: {cls.DARK_TEXT_SECONDARY};
                    font-weight: 700;
                    border: none;
                    border-bottom: 1px solid {cls.DARK_BORDER};
                    padding: 8px;
                    font-size: 11px;
                    text-transform: uppercase;
                }}

                /* Sidebar Navigation */
                QFrame#sidebar {{
                    background-color: #0a0d13;
                    border-right: 1px solid {cls.DARK_BORDER};
                }}
                QPushButton#nav_btn {{
                    background-color: transparent;
                    color: {cls.DARK_TEXT_SECONDARY};
                    border: none;
                    border-radius: 8px;
                    padding: 10px 14px;
                    text-align: left;
                    font-weight: 600;
                    font-size: 13px;
                }}
                QPushButton#nav_btn:hover {{
                    background-color: rgba(255, 255, 255, 0.05);
                    color: {cls.DARK_TEXT_PRIMARY};
                }}
                QPushButton#nav_btn:checked {{
                    background-color: rgba(136, 255, 17, 0.12);
                    color: {cls.DARK_ACCENT_PRIMARY};
                    border-left: 3px solid {cls.DARK_ACCENT_PRIMARY};
                    border-radius: 0px 8px 8px 0px;
                }}
            """
        else:
            return f"""
                QMainWindow, QDialog, QWidget#central_widget {{
                    background-color: {cls.LIGHT_BG};
                    color: {cls.LIGHT_TEXT_PRIMARY};
                    font-size: 13px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                }}

                QWidget {{
                    color: {cls.LIGHT_TEXT_PRIMARY};
                }}

                QFrame#card, QWidget#card {{
                    background-color: {cls.LIGHT_SURFACE};
                    border: 1px solid {cls.LIGHT_BORDER};
                    border-radius: 10px;
                }}

                QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
                    background-color: {cls.LIGHT_BG};
                    border: none;
                }}

                QFrame#hero_card {{
                    background-color: #E8F5E9;
                    border: 1px solid #C8E6C9;
                    border-radius: 12px;
                }}

                /* Scrollbars */
                QScrollBar:vertical {{
                    border: none;
                    background: {cls.LIGHT_BG};
                    width: 8px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: {cls.LIGHT_BORDER};
                    min-height: 20px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: {cls.LIGHT_SURFACE_ACTIVE};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}

                /* Buttons */
                QPushButton {{
                    background-color: {cls.LIGHT_SURFACE};
                    color: {cls.LIGHT_TEXT_PRIMARY};
                    border: 1px solid {cls.LIGHT_BORDER};
                    border-radius: 6px;
                    padding: 7px 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {cls.LIGHT_SURFACE_HOVER};
                    border-color: {cls.LIGHT_ACCENT_PRIMARY};
                    color: {cls.LIGHT_ACCENT_PRIMARY};
                }}
                QPushButton:pressed {{
                    background-color: {cls.LIGHT_SURFACE_ACTIVE};
                }}

                QPushButton#primary_btn {{
                    background-color: {cls.LIGHT_ACCENT_PRIMARY};
                    color: #FFFFFF;
                    border: none;
                    font-weight: 700;
                }}
                QPushButton#primary_btn:hover {{
                    background-color: #1B5E20;
                }}

                QPushButton#chip_btn {{
                    background-color: {cls.LIGHT_SURFACE};
                    border: 1px solid {cls.LIGHT_BORDER};
                    border-radius: 12px;
                    padding: 3px 8px;
                    font-size: 11px;
                }}
                QPushButton#chip_btn:hover {{
                    border-color: {cls.LIGHT_ACCENT_PRIMARY};
                }}
                QPushButton#chip_btn:checked {{
                    background-color: #E8F5E9;
                    border: 1px solid {cls.LIGHT_ACCENT_PRIMARY};
                    color: {cls.LIGHT_ACCENT_PRIMARY};
                    font-weight: 700;
                }}

                QPushButton#theme_toggle_btn {{
                    padding: 0px;
                    min-width: 0px;
                }}

                /* LineEdit & Input */
                QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                    background-color: {cls.LIGHT_SURFACE};
                    border: 1px solid {cls.LIGHT_BORDER};
                    border-radius: 6px;
                    color: {cls.LIGHT_TEXT_PRIMARY};
                    padding: 6px 10px;
                }}
                QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
                    border: 1px solid {cls.LIGHT_ACCENT_PRIMARY};
                }}

                QLabel#section_title {{
                    font-size: 15px;
                    font-weight: 700;
                    color: {cls.LIGHT_ACCENT_PRIMARY};
                    letter-spacing: 0.5px;
                }}
                QLabel#page_title {{
                    font-size: 20px;
                    font-weight: 800;
                    color: {cls.LIGHT_TEXT_PRIMARY};
                }}
                QLabel#label_secondary {{
                    color: {cls.LIGHT_TEXT_SECONDARY};
                    font-size: 11px;
                    text-transform: uppercase;
                    letter-spacing: 0.8px;
                }}

                /* Sliders */
                QSlider::groove:horizontal {{
                    border: none;
                    height: 5px;
                    background: {cls.LIGHT_SURFACE_ACTIVE};
                    border-radius: 2px;
                }}
                QSlider::sub-page:horizontal {{
                    background: {cls.LIGHT_ACCENT_PRIMARY};
                    border-radius: 2px;
                }}
                QSlider::handle:horizontal {{
                    background: #FFFFFF;
                    border: 2px solid {cls.LIGHT_ACCENT_PRIMARY};
                    width: 14px;
                    margin-top: -5px;
                    margin-bottom: -5px;
                    border-radius: 7px;
                }}

                /* Sidebar Navigation */
                QFrame#sidebar {{
                    background-color: #FFFFFF;
                    border-right: 1px solid {cls.LIGHT_BORDER};
                }}
                QPushButton#nav_btn {{
                    background-color: transparent;
                    color: {cls.LIGHT_TEXT_SECONDARY};
                    border: none;
                    border-radius: 8px;
                    padding: 10px 14px;
                    text-align: left;
                    font-weight: 600;
                    font-size: 13px;
                }}
                QPushButton#nav_btn:hover {{
                    background-color: {cls.LIGHT_SURFACE_HOVER};
                    color: {cls.LIGHT_TEXT_PRIMARY};
                }}
                QPushButton#nav_btn:checked {{
                    background-color: #E8F5E9;
                    color: {cls.LIGHT_ACCENT_PRIMARY};
                    border-left: 3px solid {cls.LIGHT_ACCENT_PRIMARY};
                    border-radius: 0px 8px 8px 0px;
                }}
            """
