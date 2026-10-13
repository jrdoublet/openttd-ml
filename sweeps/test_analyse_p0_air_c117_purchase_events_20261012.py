"""Tests hôte des dates et fenêtres d'achat, sans reconstitution contrefactuelle."""

import tempfile
import unittest
from pathlib import Path

from analyse_p0_air_c117_purchase_events_20261012 import event_date_bounds, extract


SAMPLE = ("OPEX 1973-6-01 C117_AIR_THROUGHPUT line=2 build_date=719800 age_bucket=1 "
          "period_days=30 samples=8 live_avg=1.0 live_last=1 pax=300 seat_legs=440 "
          "trips=2 profit=1200 load_factor=0.682 rating_a=110 rating_b=112 "
          "wait_a=10 wait_b=10 invalid_order_samples=0 unobserved_transitions=0")


class PurchaseTests(unittest.TestCase):
    def test_date_bracket(self):
        lines = ["1973-1-1 observed", "[FLEET_PROJECT] line=1 added=1 replaced=0", "1973-1-3 later"]
        lo, hi = event_date_bounds(lines)
        self.assertEqual(str(lo[1]), "1973-01-01")
        self.assertEqual(str(hi[1]), "1973-01-03")

    def test_reversed_timeline_rejected(self):
        with self.assertRaises(ValueError):
            event_date_bounds(["1973-4-1", "1973-2-1"])

    def test_duplicate_buy_within_interval_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.log"
            path.write_text("\n".join([
                SAMPLE,
                "1973-6-20 event", "[FLEET_PROJECT] line=2 added=1 replaced=0", "1973-6-22 event",
                "1973-7-1 event", "[FLEET_PROJECT] line=2 added=1 replaced=0", "1973-7-2 event",
                SAMPLE.replace("1973-6-01", "1973-9-01").replace("age_bucket=1", "age_bucket=4").replace("live_avg=1.0 live_last=1", "live_avg=3.0 live_last=3"),
            ]), encoding="utf-8")
            result = extract(path, seed=42)
            self.assertEqual(result["purchases_total"], 2)
            self.assertEqual(len(result["single_purchases_with_complete_pre_post_windows"]), 0)


if __name__ == "__main__":
    unittest.main()
