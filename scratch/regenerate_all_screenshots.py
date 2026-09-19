import sys
import os
import shutil
from pathlib import Path

desktop_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(desktop_dir))

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from PySide6.QtWidgets import QApplication
from core.models import (
    Shot,
    WeaponClass,
    DEFAULT_WEAPON_CLASSES,
    CalibrationEntry,
    CompensationMode,
    WeightType,
)
from core.config import ConfigManager
from core.session_manager import SessionManager
from core.i18n import I18n
from ui.main_window import MainWindow
from ui.views.hud_dialog import HudDialog
from ui.views.orga_view import WeaponClassDialog

app = QApplication.instance() or QApplication(sys.argv)

docs_dir = desktop_dir / "docs" / "screenshots"
docs_dir.mkdir(parents=True, exist_ok=True)
artifacts_dir = Path("/home/rec0il/.gemini/antigravity-ide/brain/075ea3ee-242e-44f7-b1bf-c9a301fbf429")

cfg = ConfigManager.get_instance()
sm = SessionManager.get_instance()

def populate_realistic_data():
    sm.clear_shots()
    velocities = [104.2, 105.1, 104.8, 105.5, 104.0, 105.2, 105.0, 104.7, 105.3, 104.9]
    for v in velocities:
        sm.add_shot(Shot(raw_velocity=v, weight_grams=0.20))
    
    cfg.weapon_classes = [
        WeaponClass(name=wc.name, max_joules=wc.max_joules, description=wc.description)
        for wc in DEFAULT_WEAPON_CLASSES
    ]
    cfg.selected_weapon_class = "AR"
    cfg.selected_weight = 0.20
    cfg.weight_type = WeightType.BB
    
    # Add calibration data
    cfg.clear_calibration()
    cfg.add_calibration_entry(104.5, 105.0)
    cfg.add_calibration_entry(104.8, 105.2)
    cfg.add_calibration_entry(105.1, 105.5)
    cfg.compensation_mode = CompensationMode.MEDIAN
    cfg.save()

populate_realistic_data()

def save_image(pixmap, name):
    doc_path = docs_dir / f"{name}.png"
    pixmap.save(str(doc_path))
    if artifacts_dir.exists():
        art_path = artifacts_dir / f"{name}.png"
        pixmap.save(str(art_path))
    print(f"Captured: {name}.png")

# --- 1. Dashboard Dark & Light ---
I18n.set_language("en")
win = MainWindow()
win.resize(1280, 820)
win._apply_theme(True)
win._navigate_to(0)
win.show()
app.processEvents()
save_image(win.grab(), "dashboard_dark")

win._apply_theme(False)
app.processEvents()
save_image(win.grab(), "dashboard_light")

# --- 2. Orga Chrono (Dark & German) ---
win._apply_theme(True)
win._navigate_to(1)
app.processEvents()
save_image(win.grab(), "orga_chrono_dark")

# Reorder demo: move SNIPER to the front
sniper_idx = next(i for i, c in enumerate(cfg.weapon_classes) if c.name == "SNIPER")
sniper_wc = cfg.weapon_classes.pop(sniper_idx)
cfg.weapon_classes.insert(0, sniper_wc)
cfg.save()
win.orga_view.rebuild_compliance_cards()
app.processEvents()
save_image(win.grab(), "orga_chrono_reordered")

win._on_language_changed("de")
app.processEvents()
save_image(win.grab(), "orga_chrono_de")

# Restore English & default classes order
populate_realistic_data()
win._on_language_changed("en")

# --- 3. Trajectory View ---
win._navigate_to(2)
app.processEvents()
save_image(win.grab(), "trajectory_dark")

# --- 4. History View ---
win._navigate_to(3)
app.processEvents()
save_image(win.grab(), "history_dark")

# --- 5. Export View ---
win._navigate_to(4)
app.processEvents()
save_image(win.grab(), "export_dark")

# --- 6. Settings & Calibration View ---
win._navigate_to(5)
app.processEvents()
save_image(win.grab(), "settings_calibration_dark")

win.close()

# --- 7. Edit Weapon Class Dialog ---
wc_ar = next(c for c in cfg.weapon_classes if c.name == "AR")
dlg = WeaponClassDialog(wc=wc_ar, can_delete=True)
dlg.show()
app.processEvents()
save_image(dlg.grab(), "edit_weapon_class_dialog")
dlg.close()

# --- 8. HUD Modes ---
# Dashboard HUD
hud_dash = HudDialog(dark_mode=True)
hud_dash.resize(1920, 1080)
hud_dash.show()
app.processEvents()
save_image(hud_dash.grab(), "hud_dashboard_1080p")
save_image(hud_dash.grab(), "hud_mode")  # alias for backward compat
hud_dash.close()

# Orga HUD 1080p
hud_orga_1080 = HudDialog(dark_mode=True)
hud_orga_1080._toggle_mode()
hud_orga_1080.resize(1920, 1080)
hud_orga_1080.show()
app.processEvents()
save_image(hud_orga_1080.grab(), "hud_orga_joule_grid_1080p")
hud_orga_1080.close()

# Orga HUD 720p Laptop
hud_orga_720 = HudDialog(dark_mode=True)
hud_orga_720._toggle_mode()
hud_orga_720.resize(1280, 720)
hud_orga_720.show()
app.processEvents()
save_image(hud_orga_720.grab(), "hud_orga_joule_grid_720p")
hud_orga_720.close()

# Orga HUD German 1080p
I18n.set_language("de")
hud_orga_de = HudDialog(dark_mode=True)
hud_orga_de._toggle_mode()
hud_orga_de.resize(1920, 1080)
hud_orga_de.show()
app.processEvents()
save_image(hud_orga_de.grab(), "hud_orga_joule_grid_de")
hud_orga_de.close()

# Reset clean configuration
I18n.set_language("en")
populate_realistic_data()

print("All screenshots generated and saved to docs/screenshots/ and artifacts!")
