"""
Orga cards, HUD cards and the Joule grid must not move when a shot flips a class
between waiting, LEGAL and ILLEGAL (user report: "UI elements jump around").
"""

import sys
import unittest

from PySide6.QtWidgets import QApplication

from core.models import Shot
from core.config import ConfigManager
from core.session_manager import SessionManager
from core.i18n import I18n
from ui.views.orga_view import OrgaView
from ui.views.hud_dialog import HudDialog


def geometries(widgets):
    return [(w.x(), w.y(), w.width(), w.height()) for w in widgets]


class TestLayoutStability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        I18n.set_language("en")
        self.sm = SessionManager.get_instance()
        self.sm.clear_shots()

    def _settle(self):
        for _ in range(3):
            self.app.processEvents()

    def _shoot(self, view, velocity):
        self.sm.add_shot(Shot(raw_velocity=velocity, weight_grams=0.20))
        view.refresh()
        self._settle()

    def test_orga_cards_do_not_move(self):
        for lang in ("en", "de"):
            I18n.set_language(lang)
            view = OrgaView(dark_mode=True)
            view.resize(1100, 800)
            view.show()
            self._settle()

            cards = view._compliance_cards
            grid = view.joule_grid._cards
            before_cards, before_grid = geometries(cards), geometries(grid)

            # 90 m/s: every class legal; 125 m/s: BACKUP/AR/LMG illegal, DMR/SNIPER legal; 200: all illegal
            for v in (90.0, 125.0, 200.0, 90.0):
                self._shoot(view, v)
                self.assertEqual(geometries(cards), before_cards, f"{lang}: cards moved at {v} m/s")
                self.assertEqual(geometries(grid), before_grid, f"{lang}: joule grid moved at {v} m/s")

            # All compliance cards share one width.
            self.assertEqual(len({w for (_, _, w, _) in before_cards}), 1)
            view.close()
            self.sm.clear_shots()

    def test_hud_cards_do_not_move(self):
        hud = HudDialog(dark_mode=True)
        hud.resize(1600, 900)
        hud.show()
        hud._toggle_mode()  # Orga mode shows the class cards
        self._settle()
        before = geometries(hud._cards)
        for v in (90.0, 125.0, 200.0):
            self.sm.add_shot(Shot(raw_velocity=v, weight_grams=0.20))
            hud.refresh()
            self._settle()
            self.assertEqual(geometries(hud._cards), before, f"HUD cards moved at {v} m/s")
        hud.close()


if __name__ == "__main__":
    unittest.main()
