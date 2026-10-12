"""Durable CD economic and VM opcode archive verification (no Docker)."""
import json
import unittest
from pathlib import Path

from sweeps.compare_cd_cross_tree_c66 import compare
from sweeps.verify_cd_opcode_archive import verify


EVIDENCE = Path(__file__).resolve().parents[1] / "evidence/review/air_catalogue_cd_20261012"


class TestCDCrossTreeEvidence(unittest.TestCase):
    def test_independent_b20x10_recomputes_exact_report(self):
        actual = compare(
            EVIDENCE / "cd_baseline_B20x10_20261012_r1.json",
            EVIDENCE / "cd_combined_B20x10_20261012_r1.json",
            opcode=False,
        )
        expected = json.loads((EVIDENCE / "cd_combined_B20x10_20261012_r1_comparison.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)
        self.assertEqual(actual["n"], 20)

    def test_opcode_c40x4_checks_every_seed_and_total(self):
        actual = verify()
        self.assertAlmostEqual(actual["1970-1972"]["mean_delta"], 362454.8)
        self.assertAlmostEqual(actual["1970-1972"]["relative_delta"],
                               0.0018843828503480042)
        self.assertEqual(actual["1970-1972"]["increases"], 21)
        self.assertEqual(actual["1970-1972"]["decreases"], 19)


if __name__ == "__main__":
    unittest.main()
