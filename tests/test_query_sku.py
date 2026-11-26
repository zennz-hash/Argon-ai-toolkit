"""Offline regression tests for the read-only query_sku.py inspector."""
import unittest

import query_sku


class QuerySkuTests(unittest.TestCase):
    def test_default_sku_preserves_backwards_compatibility(self):
        self.assertEqual(["g1.2tb.ai.subs_variant"], query_sku.resolve_skus([]))

    def test_presets_resolve_and_deduplicate(self):
        pro = query_sku.resolve_skus(["g1.2tb.ai.18months_eft"], preset="pro")
        self.assertIn("g1.2tb.ai.subs_variant", pro)
        self.assertIn("g1.2tb.ai.18months_eft", pro)
        self.assertEqual(len(pro), len(set(pro)))

        ultra = query_sku.resolve_skus([], preset="ultra")
        self.assertIn("g1.20tb.1month_eft.acq", ultra)
        self.assertIn("g1.ai.ultra.1month_eft.acq", ultra)

        discounts = query_sku.resolve_skus([], preset="discounts")
        self.assertIn("g1.2tb.ai.12months_ip_90p", discounts)
        self.assertIn("g1.helium.12months_ip_90p", discounts)

        all_skus = query_sku.resolve_skus([], preset="all")
        self.assertIn("g1.2tb.ai.12months_ip_90p", all_skus)
        self.assertGreater(len(all_skus), query_sku.MAX_BATCH_SIZE * 2)
        self.assertEqual(len(all_skus), len(set(all_skus)))

    def test_invalid_sku_rejected(self):
        with self.assertRaises(ValueError):
            query_sku.resolve_skus(["not_a_g1_sku"])
        with self.assertRaises(ValueError):
            query_sku.resolve_skus(['g1.bad";alert(1);//'])

    def test_chunk_skus_respects_billing_client_batch_limit(self):
        all_skus = query_sku.resolve_skus([], preset="all")
        batches = query_sku.chunk_skus(all_skus)
        self.assertGreaterEqual(len(batches), 2)
        for batch in batches:
            self.assertLessEqual(len(batch), query_sku.MAX_BATCH_SIZE)
        flattened = [sku for batch in batches for sku in batch]
        self.assertEqual(all_skus, flattened)

    def test_build_readonly_query_js_always_sets_list_only(self):
        js = query_sku.build_readonly_query_js(["g1.2tb.ai.18months_eft", "g1.20tb.1month_eft.acq"])
        self.assertIn("var LIST_ONLY=true;", js)
        self.assertIn('var PRODUCTS=["g1.2tb.ai.18months_eft", "g1.20tb.1month_eft.acq"];', js)
        self.assertNotIn("var STACK=true;", js)

    def test_sanitize_offer_and_report_never_expose_raw_tokens(self):
        secret_token = "SECRET_BILLING_OFFER_TOKEN_XYZ_999"
        raw = {
            "ev": "offer",
            "product": "g1.2tb.ai.18months_eft",
            "id": "eft-18months",
            "micros": "0",
            "period": "P1Y6M",
            "token": secret_token,
            "title": "Google AI Pro (5 TB) (Google One)",
            "name": "Google AI Pro (5 TB)",
        }
        clean = query_sku.sanitize_offer(raw)
        self.assertNotIn("token", clean)
        self.assertTrue(clean["has_token"])

        report = query_sku.format_report(["g1.2tb.ai.18months_eft"], [clean], only_free=True)
        self.assertIn("g1.2tb.ai.18months_eft", report)
        self.assertIn("0 (free intro phase)", report)
        self.assertNotIn(secret_token, report)
        self.assertIn("does NOT guarantee", report)

    def test_only_free_filter_excludes_paid_offers(self):
        offers = [
            query_sku.sanitize_offer({
                "product": "g1.20tb.1month_eft.acq",
                "id": "eft-1mo",
                "micros": "0",
                "period": "P1M",
                "name": "Google AI Ultra (20 TB)",
            }),
            query_sku.sanitize_offer({
                "product": "g1.play.20tb",
                "id": "null",
                "micros": "1579000000000",
                "period": "P1M",
                "name": "Google AI Ultra (20 TB)",
            }),
        ]
        report = query_sku.format_report(["g1.20tb.1month_eft.acq", "g1.play.20tb"], offers, only_free=True)
        self.assertIn("g1.20tb.1month_eft.acq", report)
        self.assertNotIn("g1.play.20tb", report)


class AllOffersTuiTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_offers_button_runs_readonly_inspector_and_shows_summary(self):
        import io
        import tempfile
        from pathlib import Path
        from unittest.mock import MagicMock, patch
        from textual.widgets import Button, RichLog, Static
        from tui import GoogleAITUI

        class FakeProc:
            def __init__(self, command, **_kwargs):
                self.command = command
                self.pid = 4242
                self.stdout = io.StringIO(
                    "Querying SKU batch 1/3 (15 SKUs)...\n"
                    "Summary: 12 offer(s) across 8 SKU(s) (6 free intro phase, 6 paid/discount)\n"
                )
                self.stdin = io.StringIO()

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def poll(self):
                return 0

            def wait(self):
                return 0

        launched = []

        def fake_popen(command, **kwargs):
            launched.append(command)
            return FakeProc(command, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "query_sku.py").write_text("# stub\n", encoding="utf-8")
            app = GoogleAITUI(repo=repo)
            with patch("tui.subprocess.Popen", side_effect=fake_popen):
                async with app.run_test(size=(110, 35)) as pilot:
                    await pilot.click("#all_offers")
                    for _ in range(40):
                        if not app.busy and launched:
                            break
                        await pilot.pause(0.05)
                    self.assertFalse(app.busy)
                    self.assertEqual(len(launched), 1)
                    self.assertIn("query_sku.py", launched[0][1])
                    self.assertEqual(launched[0][2:], ["--preset", "all"])
                    self.assertTrue(app.query_one("#debug_log", RichLog).display)
                    self.assertIn("12 offer(s)", str(app.query_one("#step_result", Static).render()))
                    self.assertFalse(app.query_one("#all_offers", Button).disabled)
                    self.assertFalse(app.query_one("#quickstart", Button).disabled)


if __name__ == "__main__":
    unittest.main()
