from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from analyse_c121_hub_delay import ratio, stat, weighted


class TestC121HubDelayAnalysis(unittest.TestCase):
    def test_stats(self):
        self.assertEqual(stat([1, 2, 3])["median"], 2.0)

    def test_weighted_live_timing_and_ratio(self):
        events = [
            {"period_days": 10, "c121_adapted_oneway_days": 20.0},
            {"period_days": 30, "c121_adapted_oneway_days": 28.0},
        ]
        self.assertAlmostEqual(weighted(events, "c121_adapted_oneway_days"), 26.0)
        self.assertAlmostEqual(ratio(28.0, 28.0), 1.0)
        self.assertIsNone(ratio(1.0, 0.0))


if __name__ == "__main__":
    unittest.main()
