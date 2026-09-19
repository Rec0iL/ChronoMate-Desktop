#!/usr/bin/env python3
"""
ChronoMate Desktop - Entry Point
High-precision companion application for HT-X3000 / HT-50 Airsoft Chronographs.
"""

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow


def main():
    # Enable High-DPI scaling
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("ChronoMate")
    app.setApplicationDisplayName("ChronoMate Desktop")
    app.setOrganizationName("GhostWarriorCommando")

    # Set Window Icon
    logo_path = root_dir / "assets" / "logo.png"
    if logo_path.exists():
        app.setWindowIcon(QIcon(str(logo_path)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
