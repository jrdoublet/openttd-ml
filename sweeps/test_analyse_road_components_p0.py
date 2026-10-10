"""ROAD B0 accounting: no phase residual learned from failures or partial fleets."""

import tempfile
import unittest
from pathlib import Path

from sweeps.analyse_road_components_p0 import analyze_logs


def line(actual=125, post=110, physical=120, ok=1, comparable=1):
    return ("dbg: ROAD_COMPONENTS_P0 date=1 src=11 dst=22 kind=pax cargo=0 "
            "drive=0 edges=10 stopstubs=2 depotstub=1 pre=150 "
            f"post={post} components={physical} "
            "quote_trace=30 quote_stops=35 quote_depot=15 quote_vehicles=40 "
            "real_trace=40 real_stops=37 real_depot=10 real_vehicles=38 "
            f"actual={actual} planned_vehicles=2 built_vehicles=2 comparable={comparable} ok={ok}")


class RoadComponentsAnalysis(unittest.TestCase):
    def test_comparable_successes_only_and_phase_sum(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "reference_seed42_r0.log"
            path.write_text("\n".join([line(), line(ok=0), line(comparable=0)]), encoding="utf-8")
            parsed = analyze_logs([path])["runs"][0]
            stats = parsed["all"]
            self.assertEqual(stats["attempts"], 3)
            self.assertEqual(stats["successes_comparable"], 1)
            self.assertEqual(stats["successes_incomparable"], 1)
            self.assertEqual(stats["actual_success_total"], 125)
            self.assertEqual(stats["post_mean_absolute_error"], 15)
            self.assertEqual(stats["component_mean_absolute_error"], 5)
            self.assertEqual(sum(v["observed"] for v in stats["per_phase"].values()), 125)

    def test_missing_is_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "reference_seed7_r0.log"
            path.write_text("Nothing to see here\n", encoding="utf-8")
            report = analyze_logs([path])
            self.assertEqual(report["runs_with_probe_events"], 0)
            self.assertFalse(report["runs"][0]["probe_present"])
            self.assertFalse(report["runs"][0]["all"]["comparison_known"])

    def test_inconsistent_phase_total_not_used_as_comparable(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "reference_seed7_r0.log"
            path.write_text(line(actual=124), encoding="utf-8")
            stats = analyze_logs([path])["runs"][0]["all"]
            self.assertEqual(stats["successes"], 1)
            self.assertEqual(stats["successes_comparable"], 0)
            self.assertFalse(stats["comparison_known"])


if __name__ == "__main__":
    unittest.main()
