"""PCP calculator screen: mode switch, presets, save as custom weight, BC tool, range card."""

import sys
import unittest

from PySide6.QtWidgets import QApplication

from core.config import ConfigManager
from core.models import BallisticMode, Shot
from core.pcp_presets import PCP_PRESETS
from core.session_manager import SessionManager
from core.i18n import I18n


class TestPcpView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        I18n.set_language("en")
        self.cfg = ConfigManager.get_instance()
        self.cfg.custom_weights = []
        self.sm = SessionManager.get_instance()
        self.sm.clear_shots()

    def test_mode_switch_shows_pcp_page(self):
        from ui.main_window import MainWindow
        w = MainWindow()
        w.poller.stop()
        w.settings_view.combo_bmode.setCurrentIndex(w.settings_view.combo_bmode.findData(BallisticMode.PCP.value))
        self.assertIs(w.trajectory_stack.currentWidget(), w.pcp_view)
        self.assertEqual(self.cfg.ballistic_mode, BallisticMode.PCP)
        # a new shot feeds the calculator ("latest shot" is the default velocity source)
        w._on_shot_detected(280.0)
        w.pcp_view.recalculate()
        self.assertAlmostEqual(w.pcp_view.params().muzzle_velocity_mps, 280.0)
        w.settings_view.combo_bmode.setCurrentIndex(0)
        self.assertIs(w.trajectory_stack.currentWidget(), w.ballistics_view)
        w.close()

    def test_language_switch_reaches_pcp_and_weather(self):
        from ui.main_window import MainWindow
        from core.i18n import TRANSLATIONS
        w = MainWindow()
        w.poller.stop()
        w.settings_view.combo_bmode.setCurrentIndex(1)            # PCP
        w.settings_view.combo_lang.setCurrentIndex(w.settings_view.combo_lang.findData("de"))
        self.assertEqual(w.pcp_view.lbl_title.text(), TRANSLATIONS["de"]["pcp_title"])
        self.assertEqual(w.pcp_view.env_card.lbl_title.text(), TRANSLATIONS["de"]["pcp_card_environment"])
        self.assertEqual(w.ballistics_view.env_card.lbl_title.text(), TRANSLATIONS["de"]["pcp_card_environment"])
        self.assertIs(w.trajectory_stack.currentWidget(), w.pcp_view)
        self.assertEqual(w.settings_view.chk_always_custom.text(), TRANSLATIONS["de"]["always_show_custom"])
        w.settings_view.combo_lang.setCurrentIndex(w.settings_view.combo_lang.findData("en"))
        w.settings_view.combo_bmode.setCurrentIndex(0)
        w.close()

    def test_preset_save_and_bc_tool(self):
        from ui.views.pcp_view import PcpView
        v = PcpView()
        idx = next(i for i in range(v.combo_projectile.count())
                   if (v.combo_projectile.itemData(i) or ("", -1))[0] == "preset"
                   and PCP_PRESETS[v.combo_projectile.itemData(i)[1]].name == "JSB Exact Jumbo Heavy .22")
        v.combo_projectile.setCurrentIndex(idx)
        v._on_projectile_picked(idx)
        self.assertAlmostEqual(self.cfg.pcp.mass_grams, 1.175, places=3)
        self.assertAlmostEqual(self.cfg.pcp.bc, 0.033, places=3)

        v._save_as_custom()
        self.assertEqual(len(self.cfg.custom_weights), 1)
        self.assertAlmostEqual(self.cfg.custom_weights[0].bc, 0.033)
        self.assertAlmostEqual(self.cfg.selected_weight, 1.175, places=3)

        v.combo_vsource.setCurrentIndex(2)   # typed in
        v.spin_velocity.setValue(274.3)
        v.recalculate()
        far = v._result.point_at(30.0).velocity_mps
        v.spin_v1.setValue(274.3); v.spin_d1.setValue(0.0)
        v.spin_v2.setValue(far); v.spin_d2.setValue(30.0)
        v._calc_bc()
        self.assertAlmostEqual(v._bc_value, 0.033, delta=0.0005)
        v.spin_v2.setValue(300.0)   # faster far away: impossible
        v._calc_bc()
        self.assertIsNone(v._bc_value)

        self.assertEqual(v.table.rowCount(), int(self.cfg.pcp.max_range_m / self.cfg.pcp.step_m) + 1)


if __name__ == "__main__":
    unittest.main()
