"""Fixture de jointure BFAIL/financement, indépendante d'OpenTTD."""
import json
from pathlib import Path
import tempfile
import unittest

import analyse_air_orphan_opportunity as opportunity


ORIGIN = ("AIR_ORPHAN_RETAIN date=719542 anchor=38488 station=2 town=9 "
          "pair=air|20146|36956 reason=BFAIL cost_a=26009 cost_b=2387 "
          "total=28396 reuse_a=0 reuse_b=0\n")
FAIL = ("AIR_FINANCE_TRY date=1970-01-15 outcome=failed reason=BFAIL "
        "orphan_kept=1 actual=28396 cash=186377\n")
SELECT = ("AIR_FINANCE_SELECT date=1970-01-15 budget=152981 air=3 "
          "blocked_margin=1 blocked_capital=0 blk_finance=167000 "
          "top_mode=none\n")
ORPHAN = {"date": 719542, "anchor": 38488, "station": 2,
          "cost_a_gbp": 26009, "total_build_cost_gbp": 28396,
          "status": "censored", "first_reuse_line": None, "log_line": 1}


class CounterfactualExposureTests(unittest.TestCase):
    def records(self, lines, orphan=ORPHAN):
        with tempfile.TemporaryDirectory() as dirname:
            base = Path(dirname)
            logs = base / "logs"
            logs.mkdir()
            (logs / "reference_seed42_r0.log").write_text("".join(lines), encoding="utf-8")
            orphan_file = base / "orphans.json"
            orphan_file.write_text(json.dumps({"runs": [{"file": "results\\logs\\reference_seed42_r0.log",
                "seed": 42, "arm": "reference", "repeat": 0, "orphans": [orphan]}]}), encoding="utf-8")
            return opportunity.analyze(orphan_file, logs)

    def test_same_day_static_margin_sensitivity_and_cash(self):
        result = self.records([ORIGIN, FAIL, SELECT])
        r = result["records"][0]
        self.assertEqual(r["failure_match_status"], "matched")
        self.assertEqual(r["cash_after_failed_build_proxy_gbp"], 157981)
        self.assertEqual(r["best_margin_blocked_deficit_gbp"], 14019)
        self.assertTrue(r["static_same_day_margin_crossing"])
        self.assertEqual(result["summary"]["same_day_margin_crossings"], 1)

    def test_later_crossing_not_counted_as_same_day(self):
        result = self.records([ORIGIN, FAIL, SELECT.replace("1970-01-15", "1970-01-20")])
        self.assertIsNone(result["records"][0]["static_same_day_margin_crossing"])
        self.assertEqual(result["summary"]["same_day_margin_crossings"], 0)
        self.assertEqual(result["summary"]["delayed_static_margin_crossings"], 1)

    def test_other_build_before_selection_censors_snapshot(self):
        build = "AIR_FINANCE_TRY date=1970-01-15 outcome=built reason=OK cash=157981\n"
        r = self.records([ORIGIN, FAIL, build, SELECT])["records"][0]
        self.assertEqual(r["selection_match_status"], "other_build_before_selection")
        self.assertNotIn("selection_budget_gbp", r)

    def test_wrong_total_never_joins(self):
        r = self.records([ORIGIN, FAIL.replace("actual=28396", "actual=28395"), SELECT])["records"][0]
        self.assertEqual(r["failure_match_status"], "failed_try_missing_or_ambiguous")
        self.assertNotIn("cash_before_failure_gbp", r)

    def test_no_margin_does_not_claim_avoided_project(self):
        r = self.records([ORIGIN, FAIL, SELECT.replace("blocked_margin=1", "blocked_margin=0")])["records"][0]
        self.assertIsNone(r["static_avoided_a_cost_covers_deficit"])

    def test_duplicate_origin_field_is_rejected(self):
        result = self.records([ORIGIN.replace(" anchor=38488", " anchor=38488 anchor=38488"), FAIL, SELECT])
        self.assertEqual(result["records"][0]["failure_match_status"], "missing_origin_log_line")
        self.assertEqual(result["warnings"][0]["code"], "duplicate_field")

    def test_identity_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as dirname:
            path = Path(dirname) / "reference_seed42_r0.log"
            path.write_text(ORIGIN + FAIL + SELECT, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                opportunity.analyze_run(path, {"seed": 43, "arm": "reference", "repeat": 0,
                    "orphans": [ORPHAN]})


if __name__ == "__main__":
    unittest.main()
