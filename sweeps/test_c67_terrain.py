"""Host tests for C67 fixture provenance and fail-closed collection, not a Squirrel VM."""
from pathlib import Path
import hashlib
import tempfile
import unittest

from diag_c67_terrain import NAME, ROOT, assess, keep, stage_fixture


class TerrainHarnessTests(unittest.TestCase):
    def records(self):
        return [{"run": [NAME, 42, 0], "date": f"1970-{month:02d}-01",
                 "passed": True, "output": ""} for month in range(1, 13)]

    def test_staged_source_is_exact_and_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "fixture"
            manifest = stage_fixture(target)
            source = (ROOT / "ai/OpexAI/terrain_map.nut").read_bytes()
            self.assertEqual((target / "terrain_map.nut").read_bytes(), source)
            self.assertEqual(manifest["terrain_map.nut"], hashlib.sha256(source).hexdigest())
            with self.assertRaises(FileExistsError):
                stage_fixture(target)

    def test_processor_tuple_and_exact_marker(self):
        row = {"experiment": {"bench_run": [NAME, 42, 0]}, "date": "1970-12-01",
               "chunks": {"SIGN": {1: {"name": "C67|PASS"}}}}
        result = keep(row)
        self.assertIsInstance(result, tuple)
        self.assertTrue(result[0]["passed"])
        row["chunks"]["SIGN"][1]["name"] = "C67|PASSING"
        self.assertFalse(keep(row)[0]["passed"])

    def test_complete_fixture(self):
        self.assertTrue(assess(self.records())["ok"])

    def test_empty_truncated_missing_and_duplicate_fail(self):
        rows = self.records()
        for bad in [[], rows[:-1], rows[:3] + rows[4:], rows + [rows[-1]]]:
            with self.subTest(bad=len(bad)):
                self.assertFalse(assess(bad)["ok"])

    def test_marker_is_required_at_final_checkpoint(self):
        rows = self.records()
        rows[-1]["passed"] = False
        self.assertFalse(assess(rows)["ok"])

    def test_wrong_seed_and_invalid_month_do_not_fill_coverage(self):
        rows = self.records()
        rows[0]["run"] = [NAME, 100, 0]
        self.assertFalse(assess(rows)["ok"])
        rows = self.records()
        rows[0]["date"] = "1970-99-01"
        self.assertFalse(assess(rows)["ok"])

    def test_engine_and_noai_failures_override_pass(self):
        for log in ["Fatal error", "The script died unexpectedly",
                    "[script:0] [0] [E] Your script made an error"]:
            rows = self.records()
            rows[0]["output"] = log
            self.assertFalse(assess(rows)["ok"])
        rows = self.records()
        rows[0]["engine_failure"] = {"kind": "timeout"}
        self.assertFalse(assess(rows)["ok"])


if __name__ == "__main__":
    unittest.main()
