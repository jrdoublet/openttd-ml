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

    def test_fractional_calendar_year_never_becomes_an_observed_line_year(self):
        rows = [
            row("1970-1-1", "AIR_BUILD", "arm=newpair line=0 planes=1 cost=10"),
            row("1970-1-2", "AIR_BUILD", "arm=hubsite line=1 planes=1 cost=10"),
            row("1972-1-2", "LINE_REVENUE", "mode=air line=0 age=2 year=1972.75 vehs=1 pred_prof=10 real_prof=12"),
            row("1972-1-2", "LINE_REVENUE", "mode=air line=1 age=2 year=1972 vehs=1 pred_prof=10 real_prof=12"),
        ]
        totals, arms = analyse_log(rows, with_arms=True)
        self.assertEqual(totals["mature_invalid_year"], 1)
        self.assertEqual(totals["mature_line_years_joined"], 1)
        self.assertEqual(arms["newpair"]["builds_without_mature_report"], 1)
        self.assertEqual(arms["hubsite"]["mature_line_years"], 1)

    def test_invalid_age_does_not_raise_or_count_as_mature(self):
        rows = [
            row("1970-1-1", "AIR_BUILD", "arm=newpair line=0 planes=1 cost=10"),
            row("1972-1-2", "LINE_REVENUE", "mode=air line=0 age=NaN year=1972 vehs=1 pred_prof=10 real_prof=12"),
            row("1972-1-2", "LINE_REVENUE", "mode=air line=0 age=1 year=1972 vehs=1 pred_prof=10 real_prof=12"),
        ]
        totals = analyse_log(rows)
        self.assertEqual(totals["air_revenue_events"], 2)
        self.assertEqual(totals["invalid_age_revenue_events"], 1)
        self.assertEqual(totals["censored_immature_events"], 1)
        self.assertEqual(totals["mature_line_years_joined"], 0)

    def test_invalid_line_ids_never_forge_an_observed_air_line(self):
        rows = [
            row("1970-1-1", "AIR_BUILD", "line=oops arm=newpair planes=1 cost=10"),
            row("1970-1-1", "AIR_BUILD", "line=-1 arm=newpair planes=1 cost=10"),
            row("1970-1-1", "AIR_BUILD", "line=0 arm=hubsite planes=1 cost=10"),
            row("1972-1-1", "LINE_REVENUE", "mode=air line=oops age=2 year=1972 vehs=1 pred_prof=10 real_prof=12"),
            row("1972-1-1", "LINE_REVENUE", "mode=air line=-1 age=2 year=1972 vehs=1 pred_prof=10 real_prof=12"),
            row("1972-1-1", "LINE_REVENUE", "mode=air line=0 age=2 year=1972 vehs=1 pred_prof=10 real_prof=12"),
        ]
        totals, arms = analyse_log(rows, with_arms=True)
        self.assertEqual(totals["invalid_or_reused_line_id"], 2)
        self.assertEqual(totals["mature_invalid_line_id"], 2)
        self.assertEqual(totals["air_builds_distinct"], 1)
        self.assertEqual(totals["mature_line_years_joined"], 1)
        self.assertEqual(arms["hubsite"]["mature_line_years"], 1)

    def test_noncanonical_numeric_line_alias_cannot_duplicate_identity(self):
        rows = [
            row("1970-1-1", "AIR_BUILD", "line=01 arm=newpair planes=1 cost=10"),
            row("1970-1-1", "AIR_BUILD", "line=1 arm=hubsite planes=1 cost=10"),
            row("1972-1-1", "LINE_REVENUE", "mode=air line=01 age=2 year=1972 vehs=1 pred_prof=10 real_prof=12"),
            row("1972-1-1", "LINE_REVENUE", "mode=air line=1 age=2 year=1972.0 vehs=1 pred_prof=10 real_prof=12"),
        ]
        totals, arms = analyse_log(rows, with_arms=True)
        self.assertEqual(totals["invalid_or_reused_line_id"], 1)
        self.assertEqual(totals["mature_invalid_line_id"], 1)
        self.assertEqual(totals["air_builds_distinct"], 1)
        self.assertEqual(totals["mature_line_years_joined"], 1)
        self.assertNotIn("newpair", arms)
        self.assertEqual(arms["hubsite"]["mature_line_years"], 1)

    def test_build_arms_keep_maturity_and_unknown_fleet_count_separate(self):
        rows = [
            row("1970-1-1", "AIR_BUILD", "arm=newpair line=0 src=1 dst=2 planes=1 cost=900"),
            row("1970-2-1", "AIR_BUILD", "arm=hubsite line=1 src=2 dst=3 planes=2 cost=100"),
            row("1970-3-1", "AIR_BUILD", "arm=hubhub line=2 src=2 dst=4 planes=3 cost=90"),
            row("1972-1-1", "LINE_REVENUE", "mode=air line=0 age=2 year=1972 vehs=1 pred_prof=50 real_prof=10"),
            row("1972-1-1", "LINE_REVENUE", "mode=air line=1 age=2 year=1972 vehs=3 pred_prof=50 real_prof=10"),
            row("1972-1-1", "LINE_REVENUE", "mode=air line=2 age=2 year=1972 pred_prof=50 real_prof=10"),
        ]
        summary, by_arm = analyse_log(rows, with_arms=True)
        self.assertEqual(summary["mature_line_years_joined"], 3)
        self.assertEqual(summary["mature_line_years_fleet_drift"], 1)
        self.assertEqual(summary["mature_line_years_fleet_unknown"], 1)
        self.assertEqual(set(by_arm), {"newpair", "hubsite", "hubhub"})
        self.assertEqual(by_arm["newpair"]["mature_line_years_same_fleet_count"], 1)
        self.assertEqual(by_arm["hubsite"]["mature_line_years_fleet_count_drift"], 1)
        self.assertEqual(by_arm["hubhub"]["mature_line_years_fleet_count_unknown"], 1)
        for arm in by_arm.values():
            self.assertEqual(arm["builds"], 1)
            self.assertEqual(arm["cost_quotes_present"], 1)

    def test_directory_build_arm_totals_do_not_double_count_gzip_copies(self):
        import gzip
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            text = (row("1970-1-1", "AIR_BUILD", "arm=hubsite line=1 planes=2 cost=100") +
                    row("1972-1-1", "LINE_REVENUE", "mode=air line=1 age=2 year=1972 vehs=2 pred_prof=20 real_prof=10"))
            (directory / "reference_seed42_r0.log").write_text(text, encoding="utf-8")
            with gzip.open(directory / "reference_seed42_r0.log.gz", "wt", encoding="utf-8") as output:
                output.write(text)
            (directory / "reference_seed7_r0.log").write_text(
                row("1970-1-2", "AIR_BUILD", "arm=newpair line=0 planes=1 cost=30"), encoding="utf-8")
            report = analyse_directory(directory)
        self.assertEqual(report["n_games"], 2)
        self.assertEqual(report["counts"]["air_builds_distinct"], 2)
        self.assertEqual(report["by_build_arm"]["hubsite"]["mature_line_years"], 1)
        self.assertEqual(report["by_build_arm"]["newpair"]["builds_without_mature_report"], 1)

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
