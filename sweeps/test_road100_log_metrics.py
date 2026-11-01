"""ROAD100 : la sonde ne transforme pas les événements en projets uniques."""
from pathlib import Path
import tempfile
import unittest

from road100_log_metrics import decode_one_log


class TestRoad100LogMetrics(unittest.TestCase):
    def test_counts_builds_costs_and_reasons_without_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.log"
            prefix = "[2026-10-27 22:00:00] dbg: [script:4] [0] [I] OPEX 1970-1-2 "
            rows = [
                "ROAD_BUILD line=0 cargo=PASS profit=2300 cost=16000 vehicles=2",
                "VIVIER_GEN mode=road produced=33 kept=30",
                "ROAD100_BATCH year=1970 rank=1 built=1 action=allow",
                "ROAD100_PAX_GEN towns=4 positive=3",
                "ROAD100_TOWN_GEN towns=2 positive=1",
                "PROJECT_DISCARD reason=plan_failed detail=TRACEX",
                "C69_BOTTLENECK phase=c75_pass year=1970 stop=k_pass",
            ]
            path.write_text("\n".join(prefix + row for row in rows) + "\n", encoding="utf-8")
            out = decode_one_log(path, 1970, 2)
            self.assertEqual(out[1970]["builds"], 1)
            self.assertEqual(out[1970]["reported_build_cost_gbp"], 16000)
            self.assertEqual(out[1970]["predicted_build_profit_gbp_year"], 2300)
            self.assertEqual(out[1970]["vehicles_purchased_on_new_lines"], 2)
            self.assertEqual(out[1970]["generation_produced"], 33)
            self.assertEqual(out[1970]["pax_intertown_positive"], 3)
            self.assertEqual(out[1970]["pax_local_positive"], 1)
            self.assertEqual(out[1970]["c75_stop_reasons"]["k_pass"], 1)
            self.assertEqual(out[1970]["discard_reasons"]["plan_failed"], 1)
            self.assertEqual(out[1971]["builds"], 0)


if __name__ == "__main__":
    unittest.main()
