from pathlib import Path
import tempfile
import unittest
from sweeps.run_c121_winner_integration import ROOT, stage, probe_evidence
from sweeps.campaign_freeze import parse_ai_setting_specs


class IntegrationTests(unittest.TestCase):
    def test_setting_default_is_on_in_all_difficulties_and_gated_by_c121(self):
        info = (ROOT / "ai/OpexAI/info.nut").read_text(encoding="utf-8")
        block = info.split('name = "c121_air_winner_fusion",')[1].split("});")[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(key + " = 1", block)
        self.assertTrue(parse_ai_setting_specs(ROOT / "ai/OpexAI/info.nut")["c121_air_winner_fusion"]["boolean"])
        settings = (ROOT / "ai/OpexAI/settings.nut").read_text(encoding="utf-8")
        self.assertIn("C121_AIR_WINNER_FUSION = C121_AIR_ECONOMICS", settings)

    def test_measure_has_no_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            target = stage(Path(folder), "measure")
            main = (target / "main.nut").read_text(encoding="utf-8")
            self.assertNotIn("FxIStart", main)
            self.assertIn("C121_INTEGRATION_RECEIPT", main)

    def test_fixture_calls_integrated_pair(self):
        text = (ROOT / "tests/mechanisms/c121_winner_integration_vm.nut").read_text(encoding="utf-8")
        self.assertIn("OpexC121WinnerEconomics(catalog, plan, plane, fusion)", text)

    def test_pinned_copy_keeps_exact_ai_and_single_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            source = stage(base / "source", "measure")
            target = stage(base / "second", "measure", source)
            self.assertEqual((source / "main.nut").read_bytes(), (target / "main.nut").read_bytes())
            self.assertEqual((source / "info.nut").read_bytes(), (target / "info.nut").read_bytes())

    def test_missing_cost_is_unknown(self):
        evidence = probe_evidence("", "test")
        self.assertIsNone(evidence["totals"]["c121_winner_ops"])
        self.assertFalse(all(evidence["checks"].values()))

    def test_foreign_cost_refused(self):
        log = "dbg: [script:4] [1] OPEX 1970-1-1 CATALOG_COST total_ops=9 air_ops=8 c121_winner_ops=7"
        self.assertFalse(probe_evidence(log, "test")["checks"]["no_foreign_or_out_of_interval_cost"])

    def test_valid_receipt_preserves_actual_zero(self):
        log = ("dbg: [script:4] [0] OPEX 1970-1-2 CATALOG_COST total_ops=100 air_ops=80 "
               "c121_winner_ops=0 c121_calls=1 air_new_pairs=1 air_hub_site_pairs=0 "
               "air_hub_hub_pairs=0 c121_scan_ops=40 c121_demand_ops=20")
        evidence = probe_evidence(log, "test")
        self.assertTrue(all(evidence["checks"].values()))
        self.assertEqual(evidence["totals"]["c121_winner_ops"], 0)

    def test_out_of_year_receipt_refused(self):
        log = "dbg: [script:4] [0] OPEX 1971-1-1 CATALOG_COST total_ops=9 air_ops=8 c121_winner_ops=7"
        self.assertFalse(probe_evidence(log, "test")["checks"]["no_foreign_or_out_of_interval_cost"])


if __name__ == "__main__":
    unittest.main()
