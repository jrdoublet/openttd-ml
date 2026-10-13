"""Fixtures de controle du contrat P4_FLIP logs/report final."""
import tempfile
import unittest
from pathlib import Path

from analyse_scores_p4_flip_logs_20261013 import analyze_file, fields, identity


class P4FlipLogAnalysisTests(unittest.TestCase):
    def test_fields_and_od_identity(self):
        k, data = fields("[I] P4_FLIP_HEAD id=5 year=1972 tier=0 "
                         "legacy=rail/pax/0/1/2/123 stable=air/pax/0/3/4/E7")
        self.assertEqual(k, "HEAD")
        self.assertEqual(data["id"], "5")
        self.assertNotEqual(identity(data["legacy"]), identity(data["stable"]))

    def _fixture(self, extra="", reported=""):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.log"
            path.write_text(
                "P4_FLIP_SUMMARY report_year=1974 selects=4 verified=3 "
                "skipped=1 mismatch=0 head_changes=1 attempts=0\n"
                "P4_FLIP_HEAD id=1 year=1973 month=5 tier=0 budget=100 "
                "legacy=rail/pax/0/1/2/100 stable=air/pax/0/3/4/E7 "
                "legacy_finance=99 stable_finance=98\n"
                + reported + extra, encoding="utf8")
            return analyze_file(path)

    def test_final_year_tail_not_misclassified_as_lost_event(self):
        report = self._fixture(
            "P4_FLIP_HEAD id=2 year=1974 month=5 tier=0 budget=120 "
            "legacy=road/pax/0/5/6 stable=air/pax/0/3/4/E7 "
            "legacy_finance=118 stable_finance=110\n"
            "P4_FLIP_ATTEMPT id=2 year=1974 rank=0\n")
        self.assertFalse(report["errors"])
        self.assertEqual(report["totals"]["head_events_in_log"], 2)
        self.assertEqual(report["totals"]["tail_head_events_unreported"], 1)
        self.assertEqual(report["totals"]["tail_attempt_events_unreported"], 1)

    def test_mismatch_and_unaffordable_project_are_errors(self):
        report = self._fixture(
            "P4_FLIP_HEAD id=2 year=1974 tier=0 budget=100 "
            "legacy=rail/pax/0/1/2 stable=air/pax/0/3/4 "
            "legacy_finance=101 stable_finance=90\n")
        self.assertTrue(any("unaffordable" in e for e in report["errors"]))

    def test_annual_coverage_mismatch_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.log"
            p.write_text("P4_FLIP_SUMMARY report_year=1974 selects=7 "
                         "verified=1 skipped=1 mismatch=1 head_changes=0 attempts=0\n",
                         encoding="utf8")
            report = analyze_file(p)
            self.assertTrue(any("coverage" in e for e in report["errors"]))
            self.assertTrue(any("mismatch year" in e for e in report["errors"]))


if __name__ == "__main__":
    unittest.main()
