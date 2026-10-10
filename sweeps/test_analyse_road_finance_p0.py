"""P0 ROAD log analysis: unique ODs are not the same as repeated visits."""

import tempfile
import unittest
from pathlib import Path

from sweeps.analyse_road_finance_p0 import parse_logs


class RoadP0AnalysisTests(unittest.TestCase):
    def test_repeated_visits_not_counted_as_distinct_od(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "reference_seed42_r0.log"
            path.write_text("\n".join([
                "dbg: ROAD_FINANCE_P0 date=1 variant=0 observed=4 eligible121=1 eligible100=2 unlocked=1 selected=0",
                "dbg: ROAD_FINANCE_UNLOCK_P0 date=1 variant=0 src=3 dst=4 kind=pax cargo=0 budget=100 need121=120 need100=100 in_top=0",
                "dbg: ROAD_FINANCE_P0 date=1 variant=0 observed=4 eligible121=1 eligible100=2 unlocked=1 selected=0",
                "dbg: ROAD_FINANCE_UNLOCK_P0 date=1 variant=0 src=3 dst=4 kind=pax cargo=0 budget=100 need121=120 need100=100 in_top=0",
                "dbg: ROAD_FINANCE_POSTPLAN_P0 date=2 variant=0 src=3 dst=4 before=80 after=110 cash=100 need=120 shortage=1",
                "dbg: ROAD_FINANCE_BUILD_P0 date=2 variant=0 src=3 dst=4 planned=110 actual=125 ok=0",
            ]), encoding="utf-8")
            result = parse_logs([path])["runs"][0]
            self.assertTrue(result["exposure_known"])
            self.assertEqual(result["candidate_visits_unlocked"], 2)
            self.assertEqual(result["unique_unlocked_od"], 1)
            self.assertEqual(result["unique_unlocked_dated_od"], 1)
            self.assertEqual(result["postplan_cash_shortages"], 1)
            self.assertEqual(result["build_successes"], 0)

    def test_missing_probe_is_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "variant_seed7_r0.log"
            path.write_text("an unrelated engine warning\n", encoding="utf-8")
            result = parse_logs([path])["runs"][0]
            self.assertFalse(result["exposure_known"])
            self.assertEqual(result["unlocked_events"], 0)


if __name__ == "__main__":
    unittest.main()
