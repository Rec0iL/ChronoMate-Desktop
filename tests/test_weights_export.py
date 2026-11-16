"""
Weights (loaded list + always-show-custom), custom table edits, export slider, active class limit.
"""

import sys
import unittest

from PySide6.QtWidgets import QApplication

from core.models import Shot, WeightType, CustomWeight, STANDARD_BB_WEIGHTS
from core.config import ConfigManager
from core.session_manager import SessionManager
from core.weights import available_weights
from core.pellets import pellets_for
from core.i18n import I18n
from ui.theme import Theme
from ui.views.settings_view import SettingsView
from ui.views.export_view import ExportView
from ui.views.dashboard_view import DashboardView


from core.models import BallisticMode
from core.weights import (
    DEFAULT_ACTIVE_BB, DEFAULT_ACTIVE_PCP, KIND_BB, KIND_PELLET, add_to_active, delete_own, is_selected,
    library, migrate, move_active, normalize_active, remove_from_active, resolve, select_option,
)


def fresh(cfg, mode=BallisticMode.AIRSOFT):
    """Reset the shared settings to a known state for one test."""
    cfg.ballistic_mode = mode
    cfg.custom_weights = [CustomWeight("Bio", 0.27, kind=KIND_BB, id="bio"),
                          CustomWeight("HeavySniper", 0.69, 4.5, kind=KIND_PELLET, id="hs")]
    cfg.active_airsoft = list(DEFAULT_ACTIVE_BB)
    cfg.active_pcp = list(DEFAULT_ACTIVE_PCP)
    cfg.selected_item, cfg.selected_weight = "bb:0.20", 0.20
    cfg.selected_by_kind = {KIND_BB: "bb:0.20"}
    normalize_active(cfg)


class TestProjectiles(unittest.TestCase):
    """Library + active list per mode; own projectiles always active; one Airsoft / PCP switch."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        I18n.set_language("en")
        self.cfg = ConfigManager.get_instance()
        fresh(self.cfg)
        SessionManager.get_instance().clear_shots()

    def test_active_lists_per_mode(self):
        ids = [o.id for o in available_weights(self.cfg)]
        self.assertEqual(ids, DEFAULT_ACTIVE_BB + ["own:bio"])             # own BB always active
        self.cfg.ballistic_mode = BallisticMode.PCP
        ids = [o.id for o in available_weights(self.cfg)]
        self.assertEqual(ids, DEFAULT_ACTIVE_PCP + ["own:hs"])            # own pellet in the PCP list
        self.assertTrue(all(resolve(self.cfg, i) for i in DEFAULT_ACTIVE_PCP))   # starter set exists

    def test_add_remove_move(self):
        add_to_active(self.cfg, "bb:0.12")
        self.assertEqual(self.cfg.active_airsoft[-1], "bb:0.12")
        move_active(self.cfg, "bb:0.12", -1)
        self.assertEqual(self.cfg.active_airsoft[-2], "bb:0.12")
        self.assertTrue(remove_from_active(self.cfg, "bb:0.12"))
        self.assertNotIn("bb:0.12", self.cfg.active_airsoft)
        self.assertFalse(remove_from_active(self.cfg, "own:bio"))         # own: delete instead
        delete_own(self.cfg, "bio")
        self.assertNotIn("own:bio", self.cfg.active_airsoft)

    def test_library_filter_and_search(self):
        bbs = library(self.cfg, KIND_BB)
        self.assertEqual(bbs[0].id, "bb:0.12")
        self.assertEqual(bbs[-1].id, "bb:0.48")
        p22 = library(self.cfg, KIND_PELLET, ".22")
        self.assertTrue(p22 and all(o.pellet.caliber == ".22" for o in p22))
        found = library(self.cfg, KIND_PELLET, "ALL", "baracuda match")
        self.assertEqual(len(found), 3)                                  # .177, .22, .25

    def test_selection_by_id_no_double_marks(self):
        self.cfg.ballistic_mode = BallisticMode.PCP
        add_to_active(self.cfg, "pellet:H&N Baracuda Match .177")
        opts = available_weights(self.cfg)
        bara = next(o for o in opts if o.id == "pellet:H&N Baracuda Match .177")
        own = next(o for o in opts if o.id == "own:hs")                   # also 0.69 g
        select_option(self.cfg, bara)
        self.assertEqual([o.id for o in opts if is_selected(self.cfg, o)], [bara.id])
        select_option(self.cfg, own)
        self.assertEqual([o.id for o in opts if is_selected(self.cfg, o)], [own.id])

    def test_pellet_selection_sets_pcp_projectile(self):
        self.cfg.ballistic_mode = BallisticMode.PCP
        select_option(self.cfg, resolve(self.cfg, "pellet:JSB Exact Jumbo Heavy .22"))
        self.assertEqual(self.cfg.pcp.projectile_name, "JSB Exact Jumbo Heavy .22")
        self.assertAlmostEqual(self.cfg.pcp.bc, 0.033)
        self.assertAlmostEqual(self.cfg.selected_weight, 1.175, places=3)

    def test_migration_of_old_settings(self):
        self.cfg.custom_weights = [CustomWeight("Bio", 0.27), CustomWeight("Mine", 1.2, bc=0.04)]
        self.cfg.active_airsoft, self.cfg.active_pcp, self.cfg.selected_item = [], [], ""
        self.cfg.ballistic_mode = BallisticMode.PCP
        migrate(self.cfg, {"selected_pellet": "H&N Hornet .177"})
        self.assertEqual([c.kind for c in self.cfg.custom_weights], [KIND_BB, KIND_PELLET])
        self.assertTrue(all(c.id for c in self.cfg.custom_weights))
        self.assertIn("pellet:H&N Hornet .177", self.cfg.active_pcp)    # old selection kept
        self.assertEqual(self.cfg.selected_item, "pellet:H&N Hornet .177")
        self.assertEqual(self.cfg.active_airsoft[:len(DEFAULT_ACTIVE_BB)], DEFAULT_ACTIVE_BB)

    def test_settings_card_mode_switch_and_library(self):
        from ui.main_window import MainWindow
        w = MainWindow()
        w.poller.stop()
        card = w.settings_view.projectiles_card
        self.assertTrue(card.btn_airsoft.isChecked())
        card.btn_pcp.click()
        self.assertEqual(self.cfg.ballistic_mode, BallisticMode.PCP)
        self.assertIs(w.trajectory_stack.currentWidget(), w.pcp_view)
        chips = [c.text().replace("&&", "&") for c in w.dashboard_view._weight_chips]
        self.assertIn("JSB Exact .177 0.547g", chips)
        card._add("pellet:JSB Exact King .25")                           # from the library
        chips = [c.text().replace("&&", "&") for c in w.dashboard_view._weight_chips]
        self.assertEqual(chips[-1], "JSB Exact King .25 1.645g")
        self.assertEqual(w.orga_view.joule_grid._cards[-1].weight, 0.27)   # Orga stays airsoft
        card.btn_airsoft.click()
        self.assertIs(w.trajectory_stack.currentWidget(), w.ballistics_view)
        self.assertEqual([c.text() for c in w.dashboard_view._weight_chips][0], "0.20g")
        w.close()

    def test_checked_buttons_have_a_style(self):
        for dark in (True, False):
            self.assertIn("QPushButton:checked", Theme.get_stylesheet(dark))
            self.assertIn("QListWidget", Theme.get_stylesheet(dark))


class TestExportAndAlert(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfg = ConfigManager.get_instance()
        fresh(self.cfg)
        self.sm = SessionManager.get_instance()
        self.sm.clear_shots()

    def test_export_slider_survives_new_shots(self):
        view = ExportView()
        for _ in range(20):
            self.sm.add_shot(Shot(100.0, 0.20))
        view.refresh()
        self.assertEqual(view.slider_shots.value(), 10)   # default

        view.slider_shots.setValue(5)
        for _ in range(3):
            self.sm.add_shot(Shot(101.0, 0.20))
            view.refresh()
        self.assertEqual(view.slider_shots.value(), 5)    # user's choice kept

        view.slider_shots.setValue(view.slider_shots.maximum())  # "all"
        self.sm.add_shot(Shot(102.0, 0.20))
        view.refresh()
        self.assertEqual(view.slider_shots.value(), 24)   # follows all shots

        self.sm.clear_shots()
        view.refresh()
        self.sm.add_shot(Shot(100.0, 0.20))
        view.refresh()
        self.assertEqual(view.slider_shots.value(), 1)    # new session: default again

    def test_alert_limit_follows_active_class(self):
        self.cfg.selected_weapon_class = "DMR"
        self.assertAlmostEqual(self.cfg.active_joule_limit(), 2.00)
        self.cfg.selected_weapon_class = "AR"
        self.assertAlmostEqual(self.cfg.active_joule_limit(), 1.50)


class TestJouleGridSelection(unittest.TestCase):
    """The Orga Joule grid shows the active list, marks the selected weight, a click selects it."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_grid_follows_and_sets_selected_weight(self):
        from ui.main_window import MainWindow
        cfg = ConfigManager.get_instance()
        fresh(cfg)
        w = MainWindow()
        w.poller.stop()
        cards = w.orga_view.joule_grid._cards
        self.assertEqual([c.weight for c in cards], STANDARD_BB_WEIGHTS + [0.27])
        self.assertEqual([c.weight for c in cards if c.is_selected], [0.20])
        cards[2].clicked.emit(2)                               # click the 0.25 g tile
        self.assertAlmostEqual(cfg.selected_weight, 0.25)
        self.assertEqual([c.text() for c in w.dashboard_view._weight_chips if c.isChecked()], ["0.25g"])
        chip_030 = next(c for c in w.dashboard_view._weight_chips if c.text() == "0.30g")
        chip_030.click()                                       # and the other way round
        self.assertEqual([c.weight for c in w.orga_view.joule_grid._cards if c.is_selected], [0.30])
        w.close()


if __name__ == "__main__":
    unittest.main()


class TestOrgaVerdict(unittest.TestCase):
    """Marshal: AR day, 0.32 g field weight; the card says hot / legal and which weight would pass."""

    def test_hot_at_field_weight_but_lighter_bb_passes(self):
        from core.orga import judge, LEGAL, ILLEGAL, AWAITING
        from core.weights import resolve, DEFAULT_ACTIVE_BB
        cfg = ConfigManager.get_instance()
        opts = [resolve(cfg, i) for i in DEFAULT_ACTIVE_BB]
        v = 99.0                                   # 1.57 J at 0.32 g
        ar = judge(1.50, v, 0.32, opts)
        self.assertEqual(ar.status, ILLEGAL)
        self.assertAlmostEqual(ar.max_weight_g, 0.306, places=3)
        self.assertAlmostEqual(ar.best.weight, 0.30)   # a 0.30 g player is fine
        sniper = judge(2.80, v, 0.32, opts)
        self.assertEqual(sniper.status, LEGAL)
        self.assertAlmostEqual(sniper.best.weight, 0.45)
        backup = judge(1.00, 150.0, 0.32, opts)        # even 0.20 g is too heavy
        self.assertEqual(backup.status, ILLEGAL)
        self.assertIsNone(backup.best)
        self.assertEqual(judge(1.5, 0.0, 0.32, opts).status, AWAITING)


class TestSelectionPerMode(unittest.TestCase):
    def test_each_mode_keeps_its_pick_and_orga_stays_airsoft(self):
        from core.weights import orga_selection, restore_mode_selection
        cfg = ConfigManager.get_instance()
        fresh(cfg)
        select_option(cfg, resolve(cfg, "bb:0.32"))
        cfg.ballistic_mode = BallisticMode.PCP
        restore_mode_selection(cfg)
        select_option(cfg, resolve(cfg, "pellet:JSB Exact Heavy .177"))
        self.assertAlmostEqual(cfg.selected_weight, 0.670, places=3)     # shots use the pellet
        self.assertEqual(orga_selection(cfg).id, "bb:0.32")              # Orga still judges at 0.32 g
        cfg.ballistic_mode = BallisticMode.AIRSOFT
        restore_mode_selection(cfg)
        self.assertEqual(cfg.selected_item, "bb:0.32")                   # back to the BB pick
        cfg.ballistic_mode = BallisticMode.PCP
        restore_mode_selection(cfg)
        self.assertEqual(cfg.selected_item, "pellet:JSB Exact Heavy .177")
