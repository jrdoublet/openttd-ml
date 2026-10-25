"""Contracts for retrospective, noncausal AIR-ROI-LIGNE coverage."""

import tempfile
import unittest
from pathlib import Path

from sweeps.diag_air_roi_ligne_coverage import analyse_directory, analyse_log


def row(date, tag, fields):
    return f"[script:4] [0] [I] OPEX {date} {tag} {fields}\n"


class AirLineCoverageTests(unittest.TestCase):
    def test_choice_same_day_and_maturity_fleet_drift(self):
        rows = [
            row("1970-1-14", "PROJECT_CHOSEN", "mode=air src=1 dst=2 cost=900 profit=200"),
            row("1970-1-14", "AIR_BUILD", "arm=newpair line=0 src=1 dst=2 planes=2 cost=900"),
            row("1971-1-5", "LINE_REVENUE", "mode=air line=0 year=1971 age=1 vehs=2 pred_prof=200 real_prof=100"),
            row("1972-1-5", "LINE_REVENUE", "mode=air line=0 year=1972 age=2 vehs=2 pred_prof=200 real_prof=110"),
            row("1973-1-5", "LINE_REVENUE", "mode=air line=0 year=1973 age=3 vehs=3 pred_prof=200 real_prof=170"),
        ]
        got = analyse_log(rows)
        self.assertEqual(got["air_builds_distinct"], 1)
        self.assertEqual(got["matched_choice_same_day"], 1)
        self.assertEqual(got["censored_immature_events"], 1)
        self.assertEqual(got["mature_line_years_joined"], 2)
        self.assertEqual(got["builds_with_fleet_drift"], 1)
        self.assertEqual(got["observed_capex_actual"], 0)
        self.assertEqual(got["observed_marginal_counterfactual"], 0)

    def test_no_match_for_old_choice_and_missing_build(self):
        rows = [
            row("1970-1-1", "PROJECT_CHOSEN", "mode=air src=1 dst=2 cost=900 profit=200"),
            row("1970-1-14", "AIR_BUILD", "arm=newpair line=0 src=1 dst=2 planes=1 cost=900"),
            row("1972-1-5", "LINE_REVENUE", "mode=air line=999 year=1972 age=2 vehs=1 real_prof=100"),
            row("1972-1-5", "LINE_REVENUE", "mode=air line=0 year=1972 age=2 vehs=1 real_prof=100"),
        ]
        got = analyse_log(rows)
        self.assertEqual(got["no_exact_day_choice"], 1)
        self.assertEqual(got["mature_without_build"], 1)
        self.assertEqual(got["mature_missing_profit"], 1)

    def test_reused_line_and_same_year_do_not_double_count(self):
        rows = [row("1970-1-2", "AIR_BUILD", "line=3 cost=10 planes=1") for _ in range(2)]
        rows += [row("1972-1-2", "LINE_REVENUE", "mode=air line=3 age=2 year=1972 vehs=1 pred_prof=50 real_prof=10") for _ in range(2)]
        got = analyse_log(rows)
        self.assertEqual(got["invalid_or_reused_line_id"], 1)
        self.assertEqual(got["duplicate_line_year"], 1)
        self.assertEqual(got["mature_line_years_joined"], 1)

    def test_directory_rejects_contradictory_gz_copy(self):
        import gzip
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "reference_seed42_r0.log").write_text(
                row("1970-1-1", "AIR_BUILD", "line=1 cost=10 planes=1"), encoding="utf-8")
            with gzip.open(folder / "reference_seed42_r0.log.gz", "wt", encoding="utf-8") as output:
                output.write(row("1970-1-1", "AIR_BUILD", "line=1 cost=20 planes=1"))
            # Identical coverage counts can hide distinct source facts.
            with self.assertRaisesRegex(ValueError, "copies de partie contradictoires"):
                analyse_directory(folder)


if __name__ == "__main__":
    unittest.main()
