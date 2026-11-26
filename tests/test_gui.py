"""Offline unit and headless PyQt5 smoke tests for the Desktop GUI.

Never connects to a live emulator or initiates a Google Play transaction.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import gui_core
import linux_runner
import query_sku

ROOT = Path(__file__).resolve().parents[1]

try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5 import QtCore, QtWidgets
    import gui as desktop_gui
    HAS_PYQT5 = True
except Exception:
    HAS_PYQT5 = False


class GuiCoreTests(unittest.TestCase):
    def test_sanitize_log_line_masks_emails_and_tokens(self):
        line = 'Account alice.smith@gmail.com token="AYrTWi7M/ONiNWv+hjaFmQ77fKZR8V5U3wE0whyjtpJG"'
        cleaned = gui_core.sanitize_log_line(line)
        self.assertNotIn("alice.smith@gmail.com", cleaned)
        self.assertIn("al***@gmail.com", cleaned)
        self.assertNotIn("AYrTWi7M", cleaned)
        self.assertIn("[REDACTED]", cleaned)
        self.assertEqual(gui_core.sanitize_log_line("current@device"), "current@device")

    def test_checkout_steps_require_explicit_confirmation_in_logic(self):
        with self.assertRaises(ValueError):
            gui_core.build_step_command("pro18", ROOT, confirmed=False)
        with self.assertRaises(ValueError):
            gui_core.build_step_command("step2", ROOT, confirmed=False)
        with self.assertRaises(ValueError):
            gui_core.build_step_command("step3", ROOT, confirmed=True, active_confirmed=False)

    def test_pro18_command_uses_runner_and_no_tap_without_force(self):
        cmd = gui_core.build_step_command("pro18", ROOT, confirmed=True, no_tap=True)
        self.assertIn(str(ROOT / "linux_runner.py"), cmd)
        self.assertIn("--pro18", cmd)
        self.assertIn("--confirmed", cmd)
        self.assertIn("--no-tap", cmd)
        self.assertNotIn("--force", cmd)

    def test_step0_and_step1_commands_are_readonly_without_confirmed(self):
        cmd0 = gui_core.build_step_command("step0", ROOT)
        cmd1 = gui_core.build_step_command("step1", ROOT)
        self.assertEqual(cmd0[-2:], ["--step", "0"])
        self.assertEqual(cmd1[-2:], ["--step", "1"])
        self.assertNotIn("--confirmed", cmd0)
        self.assertNotIn("--confirmed", cmd1)

    def test_sku_scan_command_is_readonly_json(self):
        cmd = gui_core.build_sku_scan_command(ROOT, preset="pro", only_free=True, serial="192.168.240.112:5555")
        self.assertIn(str(ROOT / "query_sku.py"), cmd)
        self.assertIn("--preset", cmd)
        self.assertIn("pro", cmd)
        self.assertIn("--json", cmd)
        self.assertIn("--only-free", cmd)
        self.assertIn("--serial", cmd)

    def test_parse_sku_json_sorts_free_longest_first_and_maps_guided_step(self):
        sample = {
            "queried_count": 3,
            "only_free": False,
            "offers": [
                {"product": "g1.2tb.ai.18months_eft", "id": "null", "micros": "309000000000", "period": "P1M", "name": "Google AI Pro (5 TB)"},
                {"product": "g1.2tb.ai.subs_variant", "id": "12months-eft", "micros": "0", "period": "P1Y", "name": "Google AI Pro (5 TB)"},
                {"product": "g1.2tb.ai.18months_eft", "id": "eft-18months", "micros": "0", "period": "P1Y6M", "name": "Google AI Pro (5 TB)"},
            ],
            "errors": [],
        }
        output = "Querying SKU batch 1/1...\nSKU_JSON_RESULT:" + json.dumps(sample) + "\n"
        rows, queried, errors = gui_core.parse_sku_json_output(output)
        self.assertEqual(queried, 3)
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].product, "g1.2tb.ai.18months_eft")
        self.assertEqual(rows[0].offer_id, "eft-18months")
        self.assertEqual(rows[0].guided_step_key, "pro18")
        self.assertEqual(rows[1].guided_step_key, "step2")
        self.assertIsNone(rows[2].guided_step_key)

        free_only = gui_core.filter_offers(rows, only_free=True)
        self.assertEqual(len(free_only), 2)
        search_18 = gui_core.filter_offers(rows, query="18 bulan", only_free=True)
        self.assertEqual(len(search_18), 1)
        self.assertEqual(search_18[0].offer_id, "eft-18months")

    def test_linux_runner_pro18_fail_closed_without_confirmed(self):
        with self.assertRaises(SystemExit) as ctx:
            linux_runner.main(["--pro18"])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_custom_catalog_offer_command_supports_1m_and_2m_and_fails_closed(self):
        with self.assertRaises(ValueError):
            gui_core.build_custom_offer_command("g1.2tb.ai.2months_eft", "eft-2months", ROOT, confirmed=False)
        with self.assertRaises(ValueError):
            gui_core.build_custom_offer_command("g1.100gb.1month_eft", "null", ROOT, confirmed=True)
        with self.assertRaises(SystemExit) as ctx:
            linux_runner.main(["--product", "g1.20tb.1month_eft.acq", "--offer", "eft-1mo"])
        self.assertNotEqual(ctx.exception.code, 0)

        cmd_2m = gui_core.build_custom_offer_command("g1.2tb.ai.2months_eft", "eft-2months", ROOT, confirmed=True)
        self.assertIn("--product", cmd_2m)
        self.assertIn("g1.2tb.ai.2months_eft", cmd_2m)
        self.assertIn("--offer", cmd_2m)
        self.assertIn("eft-2months", cmd_2m)
        self.assertIn("--confirmed", cmd_2m)
        self.assertIn("--no-tap", cmd_2m)
        self.assertNotIn("--force", cmd_2m)

        row_1m = gui_core.OfferRow("g1.20tb.1month_eft.acq", "eft-1mo", "0", "P4W3D", "Ultra", "Google AI Ultra (20 TB)")
        self.assertTrue(row_1m.can_open_checkout)
        self.assertEqual(row_1m.period_human, "1 bulan")
        row_paid = gui_core.OfferRow("g1.2tb.ai.2months_eft", "null", "309000000000", "P1M", "Pro", "Google AI Pro (5 TB)")
        self.assertFalse(row_paid.can_open_checkout)

    def test_query_sku_parser_accepts_json_flag(self):
        args = query_sku.build_parser().parse_args(["--preset", "pro", "--json"])
        self.assertTrue(args.json)
        self.assertEqual(args.preset, "pro")


@unittest.skipUnless(HAS_PYQT5, "PyQt5 not installed in this Python interpreter")
class DesktopGuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _make_window(self):
        return desktop_gui.DesktopToolkitWindow(repo=ROOT, auto_probe=False)

    def test_launch_starts_no_checkout_and_navigation_works(self):
        win = self._make_window()
        self.assertFalse(win.is_busy())
        self.assertEqual(win.pages.currentIndex(), 0)

        for idx in (1, 2, 0):
            win.nav_buttons[idx].click()
            self.assertEqual(win.pages.currentIndex(), idx)
        win.close()

    def test_step_selection_and_theme_toggle_work(self):
        win = self._make_window()
        initial_theme = win.theme
        win.theme_btn.click()
        self.assertNotEqual(win.theme, initial_theme)
        win.theme_btn.click()
        self.assertEqual(win.theme, initial_theme)

        for step in gui_core.GUIDED_STEPS:
            win.step_buttons[step.key].click()
            self.assertEqual(win.selected_step_key, step.key)
            self.assertEqual(win.detail_title.text(), step.title)
            self.assertEqual(win.run_step_btn.text().replace("&&", "&"), step.cta_label)
        win.close()

    def test_checkout_approval_dialog_gates_and_cancel_aborts(self):
        win = self._make_window()
        step3 = gui_core.STEP_BY_KEY["step3"]
        dlg = desktop_gui.CheckoutApprovalDialog(step3, win)
        self.assertFalse(dlg.proceed_btn.isEnabled())
        dlg.active_checkbox.setChecked(True)
        self.assertTrue(dlg.proceed_btn.isEnabled())
        dlg.reject()

        win._select_step("pro18")
        with patch.object(desktop_gui.CheckoutApprovalDialog, "exec_", return_value=QtWidgets.QDialog.Rejected), \
             patch.object(win, "_launch_subprocess") as launcher:
            win.run_step_btn.click()
        launcher.assert_not_called()
        win.close()

    def test_offer_table_filters_and_triggers_all_free_offers_safely(self):
        win = self._make_window()
        sample = {
            "queried_count": 4,
            "only_free": False,
            "offers": [
                {"product": "g1.2tb.ai.18months_eft", "id": "eft-18months", "micros": "0", "period": "P1Y6M", "name": "Google AI Pro (5 TB)"},
                {"product": "g1.2tb.ai.subs_variant", "id": "6months-eft", "micros": "0", "period": "P6M", "name": "Google AI Pro (5 TB)"},
                {"product": "g1.2tb.ai.2months_eft", "id": "eft-2months", "micros": "0", "period": "P2M", "name": "Google AI Pro (5 TB)"},
                {"product": "g1.20tb.1month_eft.acq", "id": "eft-1mo", "micros": "0", "period": "P1M", "name": "Google AI Ultra (20 TB)"},
                {"product": "g1.2tb.ai.18months_eft", "id": "null", "micros": "309000000000", "period": "P1M", "name": "Google AI Pro (5 TB)"},
            ],
            "errors": [],
        }
        win._handle_sku_finished(0, "SKU_JSON_RESULT:" + json.dumps(sample))
        self.assertEqual(win.offer_states.currentIndex(), 3)
        self.assertEqual(win.offer_table.rowCount(), 5)

        win.only_free_check.setChecked(True)
        self.assertEqual(win.offer_table.rowCount(), 4)

        # Row 1 (6months-eft stack) jumps to guided Step 3
        stack_holder = win.offer_table.cellWidget(1, 5)
        self.assertIsNotNone(stack_holder)
        stack_btn = stack_holder.findChild(QtWidgets.QPushButton)
        self.assertEqual(stack_btn.text(), "Ke Step 3")
        stack_btn.click()
        self.assertEqual(win.pages.currentIndex(), 0)
        self.assertEqual(win.selected_step_key, "step3")

        # Row 2 (2-month free offer) and Row 3 (1-month Ultra free offer) both have Buka Checkout gated by modal
        win._switch_page(1)
        for row_idx, expected_sku, expected_offer in (
            (2, "g1.2tb.ai.2months_eft", "eft-2months"),
            (3, "g1.20tb.1month_eft.acq", "eft-1mo"),
        ):
            holder = win.offer_table.cellWidget(row_idx, 5)
            btn = holder.findChild(QtWidgets.QPushButton)
            self.assertEqual(btn.text(), "Buka Checkout")
            with patch.object(desktop_gui.CheckoutApprovalDialog, "exec_", return_value=QtWidgets.QDialog.Accepted), \
                 patch.object(win, "_launch_subprocess") as launcher:
                btn.click()
            launcher.assert_called_once()
            cmd = launcher.call_args.args[0]
            self.assertIn(expected_sku, cmd)
            self.assertIn(expected_offer, cmd)
            self.assertIn("--confirmed", cmd)
            self.assertIn("--no-tap", cmd)
            self.assertNotIn("--force", cmd)
        win.close()

    def test_busy_lock_and_checkout_stop_protection(self):
        win = self._make_window()
        with patch.object(win, "is_busy", return_value=True):
            win.active_is_checkout = False
            win._sync_busy_ui()
            self.assertFalse(win.run_step_btn.isEnabled())
            self.assertFalse(win.scan_btn.isEnabled())
            self.assertTrue(win.guide_stop_btn.isEnabled())

            win.active_is_checkout = True
            win._sync_busy_ui()
            self.assertFalse(win.guide_stop_btn.isEnabled())
        win.close()

    def test_log_sanitization_and_clear(self):
        win = self._make_window()
        win._append_log("Account private.user@gmail.com")
        self.assertIn("pr***@gmail.com", win.log_view.toPlainText())
        self.assertNotIn("private.user@gmail.com", win.log_view.toPlainText())
        win.clear_log_btn.click()
        self.assertEqual(win.log_view.toPlainText(), "")
        win.close()


if __name__ == "__main__":
    unittest.main()
