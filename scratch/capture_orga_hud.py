import sys
import os
from pathlib import Path

desktop_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(desktop_dir))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from core.models import Shot, WeaponClass, DEFAULT_WEAPON_CLASSES
from core.config import ConfigManager
from core.session_manager import SessionManager
from core.i18n import I18n
from ui.views.orga_view import OrgaView
from ui.views.hud_dialog import HudDialog

app = QApplication.instance() or QApplication(sys.argv)

cfg = ConfigManager.get_instance()
sm = SessionManager.get_instance()
sm.clear_shots()

# Add a representative shot: 105 m/s at 0.20g
sm.add_shot(Shot(raw_velocity=105.0, weight_grams=0.20))

# 1. Capture Orga View with drag handles & reordered classes
I18n.set_language("en")
cfg.weapon_classes = [
    WeaponClass(name=wc.name, max_joules=wc.max_joules, description=wc.description)
    for wc in DEFAULT_WEAPON_CLASSES
]
# Reorder SNIPER to the front to showcase reordering
sniper = cfg.weapon_classes.pop(4)
cfg.weapon_classes.insert(0, sniper)
cfg.selected_weapon_class = "AR"
cfg.save()

orga = OrgaView(dark_mode=True)
orga.resize(1100, 750)
orga.show()
app.processEvents()
pix_orga = orga.grab()
artifacts_dir = Path("/home/rec0il/.gemini/antigravity-ide/brain/075ea3ee-242e-44f7-b1bf-c9a301fbf429")
pix_orga.save(str(artifacts_dir / "orga_chrono_reordered.png"))
orga.close()

# 2. Capture HUD Orga Mode at 1080p Full HD (1920x1080)
hud_1080 = HudDialog(dark_mode=True)
hud_1080._toggle_mode()  # Switch to Orga Mode
hud_1080.resize(1920, 1080)
hud_1080.show()
app.processEvents()
pix_hud_1080 = hud_1080.grab()
pix_hud_1080.save(str(artifacts_dir / "hud_orga_joule_grid_1080p.png"))
hud_1080.close()

# 3. Capture HUD Orga Mode at 720p Laptop HD (1280x720)
hud_720 = HudDialog(dark_mode=True)
hud_720._toggle_mode()
hud_720.resize(1280, 720)
hud_720.show()
app.processEvents()
pix_hud_720 = hud_720.grab()
pix_hud_720.save(str(artifacts_dir / "hud_orga_joule_grid_720p.png"))
hud_720.close()

# 4. Capture German HUD Orga Mode
I18n.set_language("de")
hud_de = HudDialog(dark_mode=True)
hud_de._toggle_mode()
hud_de.resize(1920, 1080)
hud_de.show()
app.processEvents()
pix_hud_de = hud_de.grab()
pix_hud_de.save(str(artifacts_dir / "hud_orga_joule_grid_de.png"))
hud_de.close()

# Restore English
I18n.set_language("en")
print("All screenshots generated successfully.")
