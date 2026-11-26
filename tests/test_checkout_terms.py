"""Checkout parsing tests: no real Google Play transactions."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "checkout_terms", Path(__file__).resolve().parents[1] / "ultra0.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class CheckoutTests(unittest.TestCase):
    def test_future_renewal_price_does_not_mask_zero_due_today(self):
        result = app.assess_checkout_terms(
            "Google AI Pro Subscribe Today US$0.00 12-month free trial "
            "First renewal 2027-11-19 US$19.99/month", "pro12")
        self.assertEqual(result["reason"], "zero_today_and_duration_verified")
        self.assertIn("US$19.99", result["prices"])

    def test_only_future_price_is_ambiguous(self):
        result = app.assess_checkout_terms(
            "Google AI Pro Subscribe 12 months free, then $19.99/month", "pro12")
        self.assertEqual(result["reason"], "today_price_unverified")

    def test_positive_today_price_is_never_tapped(self):
        result = app.assess_checkout_terms(
            "Google AI Pro Subscribe Today $19.99 12-month offer", "pro12")
        self.assertNotEqual(result["reason"], "zero_today_and_duration_verified")

    def test_fractional_price_is_not_zero(self):
        terms = app.assess_checkout_terms(
            "Google AI Pro Subscribe Today $0.99 12-month free trial", "pro12")
        self.assertEqual(terms["reason"], "today_price_unverified")

    def test_wrong_duration_is_blocked(self):
        result = app.assess_checkout_terms(
            "Google AI Pro Subscribe Today $0 1 month free trial", "pro12")
        self.assertEqual(result["reason"], "trial_duration_unverified")

    def test_google_play_or_reh_04_is_a_security_block_not_trial_error(self):
        checkout = (
            "Google AI Pro Subscribe Today $0.00 6 months free trial "
            "Error Your transaction can't be completed. To continue this "
            "transaction, secure your account. [OR-REH-04] Got it"
        )
        result = app.assess_checkout_terms(checkout, "pro6")
        self.assertEqual(result["reason"], "payment_security_blocked")
        self.assertEqual(result["error_code"], "OR-REH-04")
        self.assertIsNone(result["today_price"])

    def test_checkout_security_block_never_taps_subscribe(self):
        with patch.object(app, "ui_xml", return_value=(
                 "Error Your transaction can't be completed. "
                 "Secure your account [OR-REH-04] Got it")), \
             patch.object(app, "nodes", side_effect=lambda xml: [
                 {"text": xml, "desc": ""}]), \
             patch.object(app, "tap_text") as tapped:
            result = app.confirm_zero(wait=2, expected_plan="pro6")
        self.assertFalse(result["confirmed"])
        self.assertEqual(result["reason"], "payment_security_blocked")
        tapped.assert_not_called()

    def test_checkout_security_block_sets_distinct_status(self):
        fr = {"launched": {"code": 0}, "offers": [{"id": "6months-eft", "micros": "0"}]}
        with patch.object(app, "current_play_account", return_value="test@example.com"), \
             patch.object(app, "launch_app", return_value=123), \
             patch.object(app, "run_trial", return_value=fr), \
             patch.object(app, "confirm_zero", return_value={
                 "confirmed": False, "reason": "payment_security_blocked",
                 "error_code": "OR-REH-04"
             }), \
             patch.object(app, "verify") as verify:
            result = app.process("test@example.com", add=False, no_switch=True, plan="pro6", stack=True)
        self.assertEqual(result["status"], "checkout_security_blocked")
        verify.assert_not_called()

    def test_already_subscribed_is_not_extension_success(self):
        result = app.assess_checkout_terms(
            "Error You're already subscribed to Google AI Pro (5 TB) (Google One). Got it", "pro6")
        self.assertEqual(result["reason"], "already_subscribed")

    def test_already_subscribed_is_never_tapped(self):
        with patch.object(app, "ui_xml", return_value=(
                 "Error You're already subscribed to Google AI Pro (5 TB). Got it")), \
             patch.object(app, "nodes", side_effect=lambda xml: [
                 {"text": xml, "desc": ""}]), \
             patch.object(app, "tap_text") as tapped:
            result = app.confirm_zero(wait=2, expected_plan="pro6")
        self.assertFalse(result["confirmed"])
        self.assertEqual(result["reason"], "already_subscribed")
        tapped.assert_not_called()

    def test_backup_payment_prompt_is_not_a_checkout(self):
        result = app.assess_checkout_terms(
            "Google Play Turn on backup payment methods? Manage Turn on", "pro12")
        self.assertEqual(result["reason"], "backup_payment_methods_prompt")

    def test_processing_is_not_a_purchase(self):
        self.assertEqual(app.assess_checkout_terms(
            "Google Play Processing", "pro12")["reason"], "processing")

    def test_chinese_free_today_and_period(self):
        result = app.assess_checkout_terms(
            "Google AI Pro \u8ba2\u9605 \u4eca\u5929 JP¥0 12\u4e2a\u6708\u514d\u8d39\u8bd5\u7528 \u5f00\u59cb\u65e5\u671f2028\u5e74 JP¥2900/\u6708", "pro12")
        self.assertEqual(result["reason"], "zero_today_and_duration_verified")

    def test_do_not_tap_ambiguous_checkout(self):
        with patch.object(app, "ui_xml", return_value=(
                 "Google AI Pro Subscribe 12 months free then $19.99/month")), \
             patch.object(app, "nodes", side_effect=lambda xml: [
                 {"text": xml, "desc": ""}]), \
             patch.object(app, "tap_text") as tap:
            out = app.confirm_zero(wait=2, expected_plan="pro12")
        self.assertFalse(out["confirmed"])
        tap.assert_not_called()

    def test_tap_must_succeed_to_claim_confirmation(self):
        with patch.object(app, "ui_xml", return_value=(
                 "Google AI Pro Subscribe Today $0 12-month free trial")), \
             patch.object(app, "nodes", side_effect=lambda xml: [
                 {"text": xml, "desc": ""}]), \
             patch.object(app, "tap_text", return_value=False):
            out = app.confirm_zero(wait=2, expected_plan="pro12")
        self.assertFalse(out["confirmed"])
        self.assertEqual(out["reason"], "subscribe_button_not_found")

    def test_process_does_not_leave_checkout_when_unverified(self):
        fr = {"launched": {"code": 0}, "offers": [{"id": "12months-eft", "micros": "0"}]}
        with patch.object(app, "current_play_account", return_value="test@example.com"), \
             patch.object(app, "launch_app", return_value=123), \
             patch.object(app, "run_trial", return_value=fr), \
             patch.object(app, "confirm_zero", return_value={"confirmed": False}), \
             patch.object(app, "verify") as verify:
            result = app.process("test@example.com", add=False, no_switch=True, plan="pro12")
        self.assertEqual(result["status"], "checkout_not_confirmed")
        verify.assert_not_called()

    def test_pro18_build_js_targets_exact_product_and_offer(self):
        script = app.build_js(plan="pro18", list_only=True)
        self.assertIn('var PRODUCTS=["g1.2tb.ai.18months_eft"];', script)
        self.assertIn('var PREFER="eft-18months";', script)
        self.assertIn('"P1Y6M":18', script)

    def test_pro18_checkout_terms_english_and_indonesian(self):
        en = app.assess_checkout_terms(
            "Google AI Pro (5 TB) Subscribe Today US$0.00 18-month free trial "
            "Then US$19.99/month", "pro18")
        self.assertEqual(en["reason"], "zero_today_and_duration_verified")
        ind = app.assess_checkout_terms(
            "Google AI Pro (5 TB) Langganan Hari ini Rp 0 Uji coba gratis 18 bulan "
            "Lalu Rp 309.000/bulan", "pro18")
        self.assertEqual(ind["reason"], "zero_today_and_duration_verified")
        wrong = app.assess_checkout_terms(
            "Google AI Pro (5 TB) Subscribe Today US$0.00 12-month free trial", "pro18")
        self.assertEqual(wrong["reason"], "trial_duration_unverified")

    def test_confirm_zero_no_tap_never_clicks_subscribe(self):
        with patch.object(app, "ui_xml", return_value=(
                 "Google AI Pro (5 TB) Subscribe Today $0 18-month free trial")), \
             patch.object(app, "nodes", side_effect=lambda xml: [
                 {"text": xml, "desc": ""}]), \
             patch.object(app, "tap_text") as tapped:
            out = app.confirm_zero(wait=2, expected_plan="pro18", no_tap=True)
        self.assertFalse(out["confirmed"])
        self.assertEqual(out["reason"], "awaiting_manual_confirmation")
        tapped.assert_not_called()

    def test_custom_catalog_offer_build_js_and_manual_review_only(self):
        js = app.build_js(custom_product="g1.2tb.ai.2months_eft", custom_offer="eft-2months")
        self.assertIn('var PRODUCTS=["g1.2tb.ai.2months_eft"];', js)
        self.assertIn('var PREFER="eft-2months";', js)
        self.assertIn('"P4W3D":1', js)
        self.assertIn('"P8W6D":2', js)

        with self.assertRaises(ValueError):
            app.build_js(custom_product="bad.sku", custom_offer="eft-1month")
        with self.assertRaises(ValueError):
            app.build_js(custom_product="g1.2tb.ai.2months_eft", custom_offer="null")

        with patch.object(app, "ui_xml", return_value=(
                 "100 GB (Google One) Langganan Hari ini Rp 0 Uji coba gratis 1 bulan")), \
             patch.object(app, "nodes", side_effect=lambda xml: [
                 {"text": xml, "desc": ""}]), \
             patch.object(app, "tap_text") as tapped:
            out = app.confirm_zero(wait=2, expected_plan="custom", no_tap=False)
        self.assertFalse(out["confirmed"])
        self.assertEqual(out["reason"], "awaiting_manual_confirmation")
        tapped.assert_not_called()


if __name__ == "__main__":
    unittest.main()
