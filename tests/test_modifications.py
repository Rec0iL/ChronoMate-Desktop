"""
Tests for all user-requested modifications:
1. Orga mode does not require selecting class; evaluates all classes simultaneously; shows actual m/s.
2. History view has 5 columns, no legal/status column.
3. Audio engine plays sounds without error.
4. Switching BBs to Diablos or Custom weights switches displayed weights in Dashboard and Ballistics.
5. Calibration workflow: adding reference shots, computing factor, applying factor to active session.
"""

import sys
import os
import unittest
from pathlib import Path

desktop_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(desktop_dir))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from core.models import (
    Shot,
    WeightType,
    CompensationMode,
    CustomWeight,
    CalibrationEntry,
    WeaponClass,
    STANDARD_BB_WEIGHTS,
    STANDARD_DIABLO_WEIGHTS,
    DEFAULT_WEAPON_CLASSES,
)
from core.config import ConfigManager
from core.session_manager import SessionManager
from core.audio import AudioManager
from core.ballistics import BallisticsEngine
from ui.views.orga_view import OrgaView, ClassComplianceCard, WeaponClassDialog
from ui.views.history_view import HistoryView
from ui.views.dashboard_view import DashboardView
from ui.views.ballistics_view import BallisticsView
from ui.views.settings_view import SettingsView
from ui.main_window import MainWindow


class TestChronoMateModifications(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        from core.i18n import I18n
        I18n.set_language("en")
        self.cfg = ConfigManager.get_instance()
        self.cfg.language = "en"
        self.sm = SessionManager.get_instance()
        self.sm.clear_shots()
        self.cfg.clear_calibration()
        self.cfg.compensation_mode = CompensationMode.NONE
        self.cfg.weapon_classes = [
            WeaponClass(name=wc.name, max_joules=wc.max_joules, description=wc.description)
            for wc in DEFAULT_WEAPON_CLASSES
        ]
        self.cfg.selected_weapon_class = "AR"
        self.cfg.save()

    def test_audio_engine(self):
        audio = AudioManager.get_instance()
        self.assertTrue(audio._pygame_available)
        audio.play_shot()
        audio.play_alert()

    def test_orga_mode_all_classes_and_ms(self):
        orga = OrgaView(dark_mode=True)
        self.assertIn("m/s", orga.lbl_vel.text())

        num_classes = len(self.cfg.weapon_classes)
        self.assertEqual(len(orga._compliance_cards), num_classes)

        # 105 m/s: at 0.20g, E = 0.5 * 0.00020 * 105^2 = 1.1025 J
        # BACKUP limit is 1.00 J -> 1.1025 > 1.00 -> ILLEGAL
        # AR limit is 1.50 J -> 1.1025 <= 1.50 -> LEGAL
        shot = Shot(raw_velocity=105.0, weight_grams=0.20)
        self.sm.add_shot(shot)
        orga.refresh()

        self.assertEqual(orga.lbl_vel.text(), "105.00 m/s")
        # Ensure calculated energy was removed from telemetry header
        self.assertFalse(hasattr(orga, "lbl_energy"))

        card_backup = next(c for c in orga._compliance_cards if c.weapon_class.name == "BACKUP")
        card_ar = next(c for c in orga._compliance_cards if c.weapon_class.name == "AR")

        self.assertIn("ILLEGAL", card_backup.lbl_status.text())
        self.assertIn("LEGAL", card_ar.lbl_status.text())

    def test_orga_translations_german(self):
        from core.i18n import I18n
        I18n.set_language("de")
        orga = OrgaView(dark_mode=True)
        orga.retranslate()
        self.assertEqual(orga.lbl_compliance_hdr.text(), "WAFFENKLASSEN-ZULÄSSIGKEIT")
        self.assertEqual(orga.btn_add_class.text(), "+ Waffenklasse hinzufügen")
        self.assertEqual(orga.lbl_v_hdr.text(), "GEMESSENE GESCHWINDIGKEIT")
        I18n.set_language("en")

    def test_history_columns_no_status(self):
        hist = HistoryView(dark_mode=True)
        self.assertEqual(hist.table.columnCount(), 5)
        headers = [hist.table.horizontalHeaderItem(i).text() for i in range(5)]
        self.assertEqual(headers, ["#", "Timestamp", "Weight", "Velocity", "Energy"])
        self.assertNotIn("Status", headers)

    def test_weight_switching_dashboard_and_ballistics(self):
        main_win = MainWindow()

        # 1. Switch to DIABLO
        main_win.settings_view._set_weight_type(WeightType.DIABLO)
        self.assertEqual(self.cfg.weight_type, WeightType.DIABLO)
        self.assertEqual(self.cfg.selected_weight, 0.50)

        dash_chips_text = [chip.text() for chip in main_win.dashboard_view._weight_chips]
        self.assertIn("0.50g", dash_chips_text)
        self.assertIn("0.54g", dash_chips_text)
        self.assertNotIn("0.20g", dash_chips_text)

        ball_chips_text = [chip.text() for chip in main_win.ballistics_view._weight_chips]
        self.assertIn("0.50g", ball_chips_text)
        self.assertNotIn("0.20g", ball_chips_text)

        # 2. Switch to CUSTOM
        self.cfg.custom_weights = [
            CustomWeight(name="HeavySniper", weight=0.69, caliber=6.0)
        ]
        main_win.settings_view._set_weight_type(WeightType.CUSTOM)
        self.assertEqual(self.cfg.weight_type, WeightType.CUSTOM)
        self.assertAlmostEqual(self.cfg.selected_weight, 0.69)

        dash_chips_text2 = [chip.text() for chip in main_win.dashboard_view._weight_chips]
        self.assertTrue(any("HeavySniper" in t for t in dash_chips_text2))

        # 3. Switch back to BB
        main_win.settings_view._set_weight_type(WeightType.BB)
        dash_chips_text3 = [chip.text() for chip in main_win.dashboard_view._weight_chips]
        self.assertIn("0.20g", dash_chips_text3)
        self.assertIn("0.25g", dash_chips_text3)

        main_win.close()

    def test_calibration_system(self):
        main_win = MainWindow()

        # Add reference shot pair: Chrono 100 m/s, Control 95 m/s (Ratio 0.95)
        self.cfg.add_calibration_entry(100.0, 95.0)
        self.assertEqual(len(self.cfg.calibration_entries), 1)
        self.assertEqual(self.cfg.calibration_entries[0].control_value, 95.0)

        # Switch mode to TRUST_EXTERNAL
        main_win.settings_view.combo_comp.setCurrentIndex(2)
        factor = self.cfg.get_compensation_factor()
        self.assertAlmostEqual(factor, 0.95, places=3)

        # Add a shot through chrono with calibration factor applied
        main_win._on_shot_detected(100.0)
        latest_shot = self.sm.active_session.shots[-1]
        self.assertAlmostEqual(latest_shot.velocity, 95.0, places=2)

        # Verify calibration recording mode
        self.cfg.is_calibration_active = True
        main_win._on_shot_detected(102.0)
        self.assertEqual(len(self.cfg.calibration_entries), 2)
        self.assertEqual(self.cfg.calibration_entries[1].chrono_value, 102.0)
        self.assertIsNone(self.cfg.calibration_entries[1].control_value)

        # Set control value for shot 2
        self.cfg.update_calibration_control(1, 96.9)
        self.assertEqual(self.cfg.calibration_entries[1].control_value, 96.9)

        main_win.close()

    def test_hero_card_font_autoscaling(self):
        from ui.components.hero_card import HeroCard
        from PySide6.QtGui import QFont, QFontMetrics

        hero = HeroCard(dark_mode=True)
        hero.resize(240, 150)

        # 2-digit velocity
        hero.update_telemetry(95.50, 0.91)
        font_style_2digit = hero.lbl_velocity.styleSheet()
        px_2digit = int(font_style_2digit.split("font-size: ")[1].split("px")[0])

        # 3-digit velocity
        hero.update_telemetry(100.30, 1.01)
        font_style_3digit = hero.lbl_velocity.styleSheet()
        px_3digit = int(font_style_3digit.split("font-size: ")[1].split("px")[0])

        # Ensure that 3-digit velocity scales font appropriately and fits within card
        self.assertGreater(px_3digit, 20)
        self.assertLessEqual(px_3digit, px_2digit)

        # Check that total width of velocity text + unit never overflows available card width
        f_vel = QFont("Consolas")
        f_vel.setPixelSize(px_3digit)
        f_unit = QFont("Segoe UI")
        f_unit.setPixelSize(max(11, int(px_3digit * 0.32)))
        fm_v = QFontMetrics(f_vel)
        fm_u = QFontMetrics(f_unit)
        total_w = fm_v.horizontalAdvance("100.30") + fm_u.horizontalAdvance(" m/s")
        self.assertLess(total_w, hero.width())

        hero.close()

    def test_orga_card_click_activates_joule_grid_color_coding(self):
        self.cfg.selected_weapon_class = "AR"
        orga = OrgaView(dark_mode=True)
        orga.resize(900, 700)
        orga.show()

        # Initial default class should be AR (1.50 J)
        self.assertEqual(orga._active_weapon_class.name, "AR")
        card_ar = next(c for c in orga._compliance_cards if c.weapon_class.name == "AR")
        card_sniper = next(c for c in orga._compliance_cards if c.weapon_class.name == "SNIPER")
        card_backup = next(c for c in orga._compliance_cards if c.weapon_class.name == "BACKUP")

        self.assertTrue(card_ar._is_active)
        self.assertFalse(card_ar.lbl_active_badge.isHidden())
        self.assertFalse(card_sniper._is_active)
        self.assertTrue(card_sniper.lbl_active_badge.isHidden())
        self.assertIn("AR", orga.lbl_grid_title.text())
        self.assertIn("1.50 J", orga.lbl_grid_title.text())

        # Add a test shot at 105.0 m/s
        shot = Shot(raw_velocity=105.0, weight_grams=0.20)
        self.sm.add_shot(shot)
        orga.refresh()

        card_020 = next(c for c in orga.joule_grid._cards if abs(c.weight - 0.20) < 0.001)
        card_040 = next(c for c in orga.joule_grid._cards if abs(c.weight - 0.40) < 0.001)
        card_045 = next(c for c in orga.joule_grid._cards if abs(c.weight - 0.45) < 0.001)

        # Under AR (1.50 J): 0.20g (1.10 J) is safe (green #2E7D32); 0.45g (2.48 J) is illegal (red border #F44336)
        self.assertIn("#2E7D32", card_020.styleSheet())
        self.assertIn("#F44336", card_045.styleSheet())

        # Click on SNIPER card (2.80 J limit)
        card_sniper.clicked.emit(card_sniper.weapon_class)

        self.assertEqual(orga._active_weapon_class.name, "SNIPER")
        self.assertEqual(self.cfg.selected_weapon_class, "SNIPER")
        self.assertTrue(card_sniper._is_active)
        self.assertFalse(card_sniper.lbl_active_badge.isHidden())
        self.assertFalse(card_ar._is_active)
        self.assertTrue(card_ar.lbl_active_badge.isHidden())
        self.assertIn("SNIPER", orga.lbl_grid_title.text())
        self.assertIn("2.80 J", orga.lbl_grid_title.text())

        # Under SNIPER (2.80 J):
        # 0.40g is now SAFE (green #2E7D32)
        # 0.45g is now the highest legal practical weight (orange #FF9800) instead of illegal (red #F44336)!
        self.assertIn("#2E7D32", card_040.styleSheet())
        self.assertIn("#FF9800", card_045.styleSheet())

        # Click on BACKUP card (1.00 J limit)
        card_backup.clicked.emit(card_backup.weapon_class)

        self.assertEqual(orga._active_weapon_class.name, "BACKUP")
        self.assertEqual(self.cfg.selected_weapon_class, "BACKUP")
        self.assertTrue(card_backup._is_active)
        self.assertTrue(card_backup.lbl_active_badge.isVisible())
        self.assertFalse(card_sniper._is_active)
        self.assertIn("BACKUP", orga.lbl_grid_title.text())
        self.assertIn("1.00 J", orga.lbl_grid_title.text())

        # Under BACKUP (1.00 J): 0.20g (1.10 J) is now ILLEGAL (red #F44336)!
        self.assertIn("#F44336", card_020.styleSheet())

        orga.close()

    def test_edit_weapon_class_dialog_and_live_update(self):
        from ui.views.orga_view import WeaponClassDialog
        from PySide6.QtCore import QPoint, QEvent
        from PySide6.QtGui import QMouseEvent

        # 1. Test WeaponClassDialog prefill and extraction
        wc_ar = next(wc for wc in self.cfg.weapon_classes if wc.name == "AR")
        dlg = WeaponClassDialog(wc=wc_ar, can_delete=True)
        self.assertEqual(dlg.edit_name.text(), "AR")
        self.assertAlmostEqual(dlg.spin_joules.value(), 1.50)
        self.assertTrue(hasattr(dlg, "btn_delete"))

        # Modify values
        dlg.edit_name.setText("AR-MOD")
        dlg.spin_joules.setValue(1.75)
        dlg.edit_desc.setText("Upgraded Spring")
        updated = dlg.get_weapon_class()
        self.assertEqual(updated.name, "AR-MOD")
        self.assertAlmostEqual(updated.max_joules, 1.75)
        self.assertEqual(updated.description, "Upgraded Spring")
        dlg.close()

        # 2. Test Card Edit Signal and Double-Click
        from unittest.mock import patch, MagicMock

        standalone_card = ClassComplianceCard(wc_ar)
        signals_received = []
        standalone_card.edit_requested.connect(lambda target_wc: signals_received.append(target_wc.name))

        # Click the edit button
        standalone_card.btn_edit.click()
        self.assertIn("AR", signals_received)

        # Emulate double-click event
        dbl_event = QMouseEvent(
            QEvent.MouseButtonDblClick,
            QPoint(10, 10),
            QPoint(10, 10),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )
        standalone_card.mouseDoubleClickEvent(dbl_event)
        self.assertEqual(len(signals_received), 2)
        standalone_card.close()

        # Test OrgaView wiring with mock
        orga = OrgaView(dark_mode=True)
        orga.show()
        card_ar = next(c for c in orga._compliance_cards if c.weapon_class.name == "AR")
        card_ar.clicked.emit(card_ar.weapon_class)

        with patch.object(orga, "_edit_weapon_class") as mock_edit:
            card_ar.btn_edit.click()
            mock_edit.assert_called_once_with(card_ar.weapon_class)

        # 3. Test Live Update of Limits and Compliance
        # At 127.5 m/s: 0.20g energy = 0.5 * 0.00020 * 127.5^2 = 1.6256 J
        # Under 1.50 J -> ILLEGAL
        # Under 1.75 J -> LEGAL
        shot = Shot(raw_velocity=127.5, weight_grams=0.20)
        self.sm.add_shot(shot)
        orga.refresh()

        card_ar_now = next(c for c in orga._compliance_cards if c.weapon_class.name == "AR")
        self.assertIn("ILLEGAL", card_ar_now.lbl_status.text())

        # Update AR to 1.75 J
        wc_ar.max_joules = 1.75
        self.cfg.save()
        orga.rebuild_compliance_cards()

        card_ar_updated = next(c for c in orga._compliance_cards if c.weapon_class.name == "AR")
        self.assertIn("≤ 1.75 J", card_ar_updated.lbl_limit.text())
        self.assertIn("LEGAL", card_ar_updated.lbl_status.text())
        self.assertIn("1.75 J", orga.lbl_grid_title.text())

        # 4. Test Reset Classes
        self.cfg.weapon_classes = [
            WeaponClass(name=wc.name, max_joules=wc.max_joules, description=wc.description)
            for wc in DEFAULT_WEAPON_CLASSES
        ]
        self.cfg.save()
        orga.rebuild_compliance_cards()
        card_ar_restored = next(c for c in orga._compliance_cards if c.weapon_class.name == "AR")
        self.assertIn("≤ 1.50 J", card_ar_restored.lbl_limit.text())

        orga.close()

    def test_drag_and_drop_reorder_weapon_classes(self):
        orga = OrgaView(dark_mode=True)
        orga.show()

        # Original order: BACKUP, AR, LMG, DMR, SNIPER
        self.assertEqual([c.name for c in self.cfg.weapon_classes], ["BACKUP", "AR", "LMG", "DMR", "SNIPER"])
        self.assertEqual([c.weapon_class.name for c in orga._compliance_cards], ["BACKUP", "AR", "LMG", "DMR", "SNIPER"])

        # Reorder: move SNIPER to BACKUP (position 0)
        orga._on_reorder_classes("SNIPER", "BACKUP")
        self.assertEqual([c.name for c in self.cfg.weapon_classes], ["SNIPER", "BACKUP", "AR", "LMG", "DMR"])
        self.assertEqual([c.weapon_class.name for c in orga._compliance_cards], ["SNIPER", "BACKUP", "AR", "LMG", "DMR"])

        # Reorder: move LMG to AR
        orga._on_reorder_classes("LMG", "AR")
        self.assertEqual([c.name for c in self.cfg.weapon_classes], ["SNIPER", "BACKUP", "LMG", "AR", "DMR"])

        # Verify cards have drag handle with tooltip
        card0 = orga._compliance_cards[0]
        self.assertEqual(card0.lbl_drag_handle.text(), "⋮⋮")
        self.assertIn("Drag", card0.lbl_drag_handle.toolTip())
        self.assertTrue(card0.acceptDrops())

        # Test simulated QDropEvent
        from PySide6.QtGui import QDropEvent
        from PySide6.QtCore import QMimeData, QPointF
        mime = QMimeData()
        mime.setData("application/x-chronomate-weapon-class", b"DMR")
        drop_event = QDropEvent(QPointF(10, 10), Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)

        reorder_signals = []
        card0.reorder_requested.connect(lambda s, t: reorder_signals.append((s, t)))
        card0.dropEvent(drop_event)
        self.assertEqual(reorder_signals, [("DMR", "SNIPER")])

        orga.close()


if __name__ == "__main__":
    unittest.main()
