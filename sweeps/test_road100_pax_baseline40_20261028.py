"""Small pure tests for the descriptive 40-seed PAX audit."""

import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diag_road100_pax_baseline40_20261028 import discover, summarise


class PaxBaseline40Tests(unittest.TestCase):
    def test_discover_requires_forty_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "road100_baseline_seed42_r0.log").write_text("", encoding="utf8")
            with self.assertRaisesRegex(ValueError, "exactly 40"):
                discover(directory)

    def test_ratio_of_sums_is_not_mean_of_ratios(self):
        rows = [
            dict(seed=1, line=0, pred_rev=10, real_rev=20, pred_prof=5, real_prof=10),
            dict(seed=2, line=0, pred_rev=90, real_rev=45, pred_prof=95, real_prof=95),
        ]
        output = summarise(rows)
        self.assertEqual(output["observations"], 2)
        self.assertEqual(output["seeds_with_mature_pax"], 2)
        self.assertEqual(output["rev"]["ratio_of_sums"], 0.65)
        self.assertEqual(output["prof"]["ratio_of_sums"], 1.05)
        self.assertEqual(output["rev"]["median_positive_line_age_ratio"], 1.25)

    def test_nonpositive_excluded_from_positive_median(self):
        rows = [
            dict(seed=1, line=0, pred_rev=10, real_rev=-2, pred_prof=5, real_prof=0),
            dict(seed=1, line=1, pred_rev=10, real_rev=20, pred_prof=10, real_prof=5),
        ]
        output = summarise(rows)
        self.assertEqual(output["rev"]["ratio_of_sums"], 0.9)
        self.assertEqual(output["rev"]["median_positive_line_age_ratio"], 2.0)
        self.assertEqual(output["rev"]["n_positive"], 1)
        self.assertEqual(output["prof"]["n_nonpositive_excluded_from_median"], 1)


if __name__ == "__main__":
    unittest.main()
