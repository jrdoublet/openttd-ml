"""Offline contracts of staging/receipts; these tests are NOT engine fixtures."""
from datetime import date
from pathlib import Path
import tempfile
import unittest

from sweeps.run_mechanism_fixtures import (
    ROOT, checkpoint_dates, phase_integrity, replace_once, select_checkpoint, stage, stage_bypass, tree_hashes, verify_markers,
)


class FixtureContracts(unittest.TestCase):
    def test_replace_refuses_missing(self):
        with self.assertRaises(ValueError):
            replace_once("abc", "missing", "replacement")

    def test_no_unavailable_array_find(self):
        source = (ROOT / "tests/mechanisms/world_fleet.nut").read_text(encoding="utf-8")
        self.assertNotIn("after.find(", source)
        self.assertIn('FxAssert(present, "no_replacement")', source)

    def test_replace_refuses_duplicate(self):
        with self.assertRaises(ValueError):
            replace_once("xx", "x", "y")

    def test_staging_preserves_production(self):
        before = tree_hashes(ROOT / "ai/OpexAI")
        with tempfile.TemporaryDirectory() as tmp:
            staged = stage(Path(tmp))
            self.assertIn("FxEntry(this, fleetEntry);", (staged / "task_air.nut").read_text(encoding="utf-8"))
            self.assertIn("saveObj.fixture <- FX", (staged / "persist.nut").read_text(encoding="utf-8"))
            self.assertEqual((staged / "info.nut").read_bytes(), (ROOT / "ai/OpexAI/info.nut").read_bytes())
        self.assertEqual(before, tree_hashes(ROOT / "ai/OpexAI"))

    def test_checkpoint_is_boundary_not_mid_fraction(self):
        day = (date(1971, 2, 1) - date(1, 1, 1)).days + 365
        log = f"FXWORLD phase=save state=selected date={day} tick=90"
        self.assertEqual(checkpoint_dates(log, "selected"), {"1971-02-01"})
        rows = [{"date": "1971-01-01"}, {"date": "1971-02-01"}]
        self.assertEqual(select_checkpoint(rows, log, "selected"), rows[1])

    def test_bypass_staging_uses_real_commands(self):
        for scenario in ("r3_dead", "r3_cash", "r3_failure"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                target = stage_bypass(Path(tmp), scenario)
                construction = (target / "air_construction.nut").read_text(encoding="utf-8")
                self.assertIn("FxR3Obstacle(plan, levelA);", construction)
                self.assertIn("levelA.ok && AIAirport.BuildAirport", construction)
                self.assertNotIn("FxEntry(this, fleetEntry);", (target / "task_air.nut").read_text(encoding="utf-8"))
                self.assertIn("if (R1_R3_TEST_ONLY || C49_SCARCITY_LEDGER", (target / "task_air.nut").read_text(encoding="utf-8"))
                self.assertIn("detail = result.reason, error = result.error", (target / "task_air.nut").read_text(encoding="utf-8"))

    def test_checkpoint_missing_rejected(self):
        with self.assertRaises(RuntimeError):
            select_checkpoint([{"date": "1971-01-01"}], "", "selected")

    def test_checkpoint_duplicates_rejected(self):
        day = (date(1971, 2, 1) - date(1, 1, 1)).days + 365
        with self.assertRaises(RuntimeError):
            select_checkpoint([{"date": "1971-02-01"}] * 2,
                              f"FXWORLD phase=save state=selected date={day}", "selected")

    def test_absent_proof_fails(self):
        self.assertFalse(any(verify_markers(["", "", ""]).values()))

    def test_matrix_requires_all_distinct_cases(self):
        log = "\n".join(f"FXVM case={i} pass=1" for i in range(1, 49))
        end = "FXVM complete=1 cases=48 boundary_checks=9 settings_restored=1"
        self.assertTrue(verify_markers([log + "\n" + end, "", ""])["vm_matrix"])
        self.assertFalse(verify_markers([log.replace("case=48", "case=47") + end, "", ""])["vm_matrix"])

    def test_real_guard_not_inferred_from_fit(self):
        logs = ["", "FXWORLD phase=guard price=30000 need=36000 cash=35999", ""]
        self.assertFalse(verify_markers(logs)["exact_real_purchase_guard"])

    def test_error_metadata_is_not_a_failure(self):
        phase = {"script_errors": {"schema_version": "1", "attributed": [],
                                  "unattributed": [], "engine_marker": None}, "records": []}
        self.assertTrue(phase_integrity(phase, "1970-06-01", 1)["no_script_errors"])
        phase["script_errors"]["unattributed"] = ["fatal"]
        self.assertFalse(phase_integrity(phase, "1970-06-01", 1)["no_script_errors"])
        phase["script_errors"] = {}
        self.assertFalse(phase_integrity(phase, "1970-06-01", 1)["no_script_errors"])

    def test_reload_interval_requires_all_real_months(self):
        from unittest.mock import patch
        phase = {"script_errors": {}, "records": []}
        dates = [f"{1970 + (5 + n) // 12}-{(5 + n) % 12 + 1:02d}-01" for n in range(13)]
        phase["records"] = [{"date": d, "company": {}} for d in dates]
        with patch("sweeps.game_health.inspect_checkpoints", return_value={
                "duplicates": [], "missing_companies": [], "missing_checkpoints": {}}) as inspect:
            self.assertTrue(phase_integrity(phase, "1970-06-01", 1)["exact_monthly_interval"])
            self.assertEqual(inspect.call_args.kwargs["expected_dates"], dates)
            phase["records"].pop(4)
            self.assertFalse(phase_integrity(phase, "1970-06-01", 1)["exact_monthly_interval"])


if __name__ == "__main__":
    unittest.main()