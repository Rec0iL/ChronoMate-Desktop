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


class TestWeightsAndExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        I18n.set_language("en")
        self.cfg = ConfigManager.get_instance()
        self.cfg.weight_type = WeightType.BB
        self.cfg.selected_weight = 0.20
        self.cfg.selected_pellet = ""
        self.cfg.always_show_custom_weights = False
        self.cfg.custom_weights = [CustomWeight("Bio", 0.27), CustomWeight("Tracer", 0.30)]
        self.sm = SessionManager.get_instance()
        self.sm.clear_shots()

    def test_available_weights(self):
        opts = available_weights(self.cfg)
        self.assertEqual([o.weight for o in opts], STANDARD_BB_WEIGHTS)

        self.cfg.always_show_custom_weights = True
        opts = available_weights(self.cfg)
        self.assertEqual([o.weight for o in opts], STANDARD_BB_WEIGHTS + [0.27, 0.30])
        self.assertTrue(all(o.is_custom for o in opts[-2:]))
        self.assertEqual(opts[-2].label, "Bio 0.27g")

        self.cfg.weight_type = WeightType.CUSTOM
        self.assertEqual([o.weight for o in available_weights(self.cfg)], [0.27, 0.30])

    def test_dashboard_chips_follow_setting(self):
        dash = DashboardView()
        self.assertEqual(len(dash._weight_chips), len(STANDARD_BB_WEIGHTS))
        self.cfg.always_show_custom_weights = True
        dash.rebuild_weight_chips()
        texts = [c.text() for c in dash._weight_chips]
        self.assertEqual(texts[-1], "Tracer 0.30g")
        checked = [c.text() for c in dash._weight_chips if c.isChecked()]
        self.assertEqual(checked, ["0.20g"])

    def test_switching_type_moves_selection(self):
        view = SettingsView()
        self.cfg.diabolo_caliber = ".22"
        view._set_weight_type(WeightType.DIABLO)
        first = pellets_for(".22")[0]
        self.assertAlmostEqual(self.cfg.selected_weight, first.mass_grams)
        self.assertTrue(view.btn_diablo.isChecked())
        self.assertFalse(view.btn_bb.isChecked())
        self.assertTrue(view.combo_caliber.isVisibleTo(view))
        self.assertEqual(view.loaded_chips.chips()[0].text(), f"{first.short} {first.mass_grams:.3f}g")
        view._set_weight_type(WeightType.CUSTOM)
        self.assertAlmostEqual(self.cfg.selected_weight, 0.27)

    def test_checked_buttons_have_a_style(self):
        for dark in (True, False):
            self.assertIn("QPushButton:checked", Theme.get_stylesheet(dark))

    def test_custom_table_edits_are_saved(self):
        view = SettingsView()
        view.custom_table.item(0, 0).setText("Bio Heavy")
        view.custom_table.item(0, 1).setText("0,28")      # comma decimal is accepted
        view.custom_table.item(1, 1).setText("abc")        # invalid input is ignored
        self.app.processEvents()
        self.assertEqual(self.cfg.custom_weights[0].name, "Bio Heavy")
        self.assertAlmostEqual(self.cfg.custom_weights[0].weight, 0.28)
        self.assertAlmostEqual(self.cfg.custom_weights[1].weight, 0.30)
        reloaded = ConfigManager()  # a fresh instance reads the saved file
        self.assertEqual(reloaded.custom_weights[0].name, "Bio Heavy")

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


if __name__ == "__main__":
    unittest.main()


class TestJouleGridSelection(unittest.TestCase):
    """The Orga Joule grid shows the chips' weight list, marks the selected weight, click selects."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_grid_follows_and_sets_selected_weight(self):
        from ui.main_window import MainWindow
        cfg = ConfigManager.get_instance()
        cfg.weight_type = WeightType.BB
        cfg.selected_weight = 0.20
        cfg.always_show_custom_weights = True
        cfg.custom_weights = [CustomWeight("Bio", 0.27)]
        w = MainWindow()
        w.poller.stop()
        cards = w.orga_view.joule_grid._cards
        self.assertEqual([c.weight for c in cards], STANDARD_BB_WEIGHTS + [0.27])
        self.assertEqual([c.weight for c in cards if c.is_selected], [0.20])
        cards[2].clicked.emit(2)                               # click the 0.25 g tile
        self.assertAlmostEqual(cfg.selected_weight, 0.25)
        self.assertEqual([c.text() for c in w.dashboard_view._weight_chips if c.isChecked()], ["0.25g"])
        w.dashboard_view.weight_bar.weight_clicked.emit(0.30)  # and the other way round
        self.assertEqual([c.weight for c in w.orga_view.joule_grid._cards if c.is_selected], [0.30])
        w.close()


class TestPelletCatalogue(unittest.TestCase):
    """Diablos = the pellet catalogue; it and the PCP calculator stay in step."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_same_weight_pellets_are_told_apart(self):
        from core.weights import WeightOption, is_selected, select_option
        cfg = ConfigManager.get_instance()
        cfg.weight_type = WeightType.DIABLO
        cfg.diabolo_caliber = ".177"
        twins = [p for p in pellets_for(".177") if abs(p.mass_grams - 0.547) < 1e-4]
        self.assertGreaterEqual(len(twins), 2)                 # JSB Exact and Air Arms Field: 8.44 gr
        opts = [o for o in available_weights(cfg) if o.pellet in twins]
        select_option(cfg, opts[1])
        self.assertEqual([is_selected(cfg, o) for o in opts], [False, True] + [False] * (len(opts) - 2))

    def test_pellet_chip_sets_pcp_projectile_and_pcp_mode_switches_type(self):
        from ui.main_window import MainWindow
        cfg = ConfigManager.get_instance()
        cfg.weight_type = WeightType.BB
        cfg.diabolo_caliber = ".22"
        w = MainWindow()
        w.poller.stop()
        w.settings_view.combo_bmode.setCurrentIndex(1)          # PCP
        self.assertEqual(cfg.weight_type, WeightType.DIABLO)
        chips = w.dashboard_view._weight_chips
        jh = next(c for c in chips if c.text().startswith("JSB Exact Jumbo Heavy"))
        jh.click()
        self.assertEqual(cfg.pcp.projectile_name, "JSB Exact Jumbo Heavy .22")
        self.assertAlmostEqual(cfg.pcp.bc, 0.033)
        self.assertAlmostEqual(w.pcp_view.spin_mass.value(), 1.175, places=3)
        w.settings_view.combo_bmode.setCurrentIndex(0)          # back to airsoft: BBs again
        self.assertEqual(cfg.weight_type, WeightType.BB)
        w.close()


class TestNoDoubleSelection(unittest.TestCase):
    def test_custom_and_pellet_with_same_weight(self):
        from core.weights import is_selected, select_option
        cfg = ConfigManager.get_instance()
        cfg.weight_type = WeightType.DIABLO
        cfg.diabolo_caliber = ".177"
        cfg.always_show_custom_weights = True
        cfg.custom_weights = [CustomWeight("HeavySniper", 0.69)]
        opts = available_weights(cfg)
        bara = next(o for o in opts if o.pellet and o.pellet.name == "H&N Baracuda Match .177")
        own = next(o for o in opts if o.is_custom)
        select_option(cfg, bara)
        self.assertEqual([o for o in opts if is_selected(cfg, o)], [bara])
        select_option(cfg, own)
        self.assertEqual([o for o in opts if is_selected(cfg, o)], [own])
