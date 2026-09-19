"""
Tests for Full-Screen Field Station HUD Auto-Scaling & Orga Compliance Strip
"""

import sys
import os
import unittest
from pathlib import Path

desktop_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(desktop_dir))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from core.models import Shot
from core.config import ConfigManager
from core.session_manager import SessionManager
from core.i18n import I18n
from ui.views.hud_dialog import HudDialog


class TestHudAutoScaling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        I18n.set_language("en")
        self.cfg = ConfigManager.get_instance()
        self.sm = SessionManager.get_instance()
        self.sm.clear_shots()

    def test_hud_auto_scaling_and_modes(self):
        hud = HudDialog(dark_mode=True)
        hud.show()
        self.sm.add_shot(Shot(raw_velocity=105.0, weight_grams=0.20))
        hud.refresh()

        # 1. Default is Dashboard mode: Energy visible, compliance cards and joule grid hidden
        self.assertTrue(hud.lbl_energy.isVisible())
        self.assertFalse(hud.cards_container.isVisible())
        self.assertFalse(hud.joule_container.isVisible())
        self.assertEqual(hud.lbl_vel.text(), "105.0")
        self.assertEqual(hud.lbl_energy.text(), "1.10 J")
        self.assertIn("Shot #1", hud.lbl_sub.text())

        # 2. Resize to 1920x1080 (1080p Full HD)
        hud.resize(1920, 1080)
        self.app.processEvents()
        self.assertIn("px", hud.lbl_vel.styleSheet())
        font_size_1080 = int(hud.lbl_vel.styleSheet().split("font-size: ")[1].split("px")[0])
        self.assertGreater(font_size_1080, 200)

        # 3. Toggle to Orga mode: Energy hidden, cards and Joule Reference Grid visible
        hud._toggle_mode()
        self.assertTrue(hud._is_orga_mode)
        self.assertFalse(hud.lbl_energy.isVisible())
        self.assertTrue(hud.cards_container.isVisible())
        self.assertTrue(hud.joule_container.isVisible())
        self.assertEqual(len(hud._cards), len(self.cfg.weapon_classes))

        # Check Joule Reference Grid
        self.assertEqual(len(hud.hud_joule_grid._cards), 10)
        self.assertIn("Joule Reference Grid", hud.lbl_hud_grid_title.text())
        self.assertIn("AR", hud.lbl_hud_grid_title.text())
        self.assertIn("1.50 J", hud.lbl_hud_grid_title.text())

        # Check BACKUP card (Limit 1.00J): 105 m/s at 0.20g = 1.1025 J -> ILLEGAL
        card_backup = next(c for c in hud._cards if c.weapon_class.name == "BACKUP")
        self.assertIn("ILLEGAL", card_backup.lbl_status.text())

        # Check AR card (Limit 1.50J): 1.1025 <= 1.50 -> LEGAL
        card_ar = next(c for c in hud._cards if c.weapon_class.name == "AR")
        self.assertIn("LEGAL", card_ar.lbl_status.text())
        self.assertTrue(card_ar._is_active)

        # 4. Click SNIPER card in HUD -> Switches active class for HUD Joule Grid
        card_sniper = next(c for c in hud._cards if c.weapon_class.name == "SNIPER")
        card_sniper.clicked.emit(card_sniper.weapon_class)
        self.assertTrue(card_sniper._is_active)
        self.assertFalse(card_ar._is_active)
        self.assertIn("SNIPER", hud.lbl_hud_grid_title.text())
        self.assertIn("2.80 J", hud.lbl_hud_grid_title.text())
        self.assertEqual(self.cfg.selected_weapon_class, "SNIPER")

        # 5. Resize to 1280x720 (Laptop HD) in Orga Mode
        hud.resize(1280, 720)
        self.app.processEvents()
        font_size_720 = int(hud.lbl_vel.styleSheet().split("font-size: ")[1].split("px")[0])
        self.assertGreater(font_size_720, 80)

        # 6. German translation in HUD
        I18n.set_language("de")
        hud._apply_scaling()
        hud.refresh()
        self.assertEqual(hud.lbl_title.text(), "CHRONOMATE FELDSTATION-HUD")
        self.assertIn("DASHBOARD", hud.btn_toggle_mode.text())
        self.assertIn("Waffenklassen-Zulässigkeit", hud.lbl_sub.text())
        self.assertIn("UNZULÄSSIG", card_backup.lbl_status.text())
        self.assertIn("ZULÄSSIG", card_ar.lbl_status.text())
        self.assertIn("Joule Referenz-Tabelle", hud.lbl_hud_grid_title.text())

        hud.close()


if __name__ == "__main__":
    unittest.main()
