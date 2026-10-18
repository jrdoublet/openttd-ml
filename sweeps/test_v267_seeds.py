"""V267 : contrats du script de choix des graines (sweeps/v267_seeds.py)."""

import re
import unittest
from pathlib import Path

import v267_seeds as v

ROOT = Path(__file__).resolve().parents[1]


class TestV267Seeds(unittest.TestCase):
    def test_seeds_40_read_from_bench_v2(self):
        text = (ROOT / "sweeps" / "bench_v2.py").read_text()
        self.assertIn("SEEDS_40 = SEEDS + SEEDS_EXTRA_20", text)
        self.assertEqual(len(v.SEEDS_40), 40)
        self.assertEqual(v.SEEDS_40[:3], (42, 100, 7))

    def test_generation_deterministic_and_excludes_73(self):
        a = v.lcg_seeds(200, exclude=v.EXCLUDED)
        self.assertEqual(a, v.lcg_seeds(200, exclude=v.EXCLUDED))
        self.assertNotIn(73, a)
        self.assertEqual(len(set(a)), 200)
        self.assertFalse(set(a) & set(v.SEEDS_40))

    def test_checkpoints_match_harness(self):
        # run_c66 : expected_last_checkpoint = derniere annee, 1er decembre.
        self.assertEqual(v.checkpoint(3), "1972-12-01")
        self.assertEqual(v.checkpoint(10), "1979-12-01")

    def test_greedy_picks_distinct_and_covers(self):
        z = {s: [float(s % 7), float(s % 3)] for s in range(1, 60)}
        chosen = v.greedy_mmd(z, 10)
        self.assertEqual(len(set(chosen)), 10)
        # Couverture : la selection ne se concentre pas sur une seule valeur de la 1re variable.
        self.assertGreater(len({s % 7 for s in chosen}), 3)

    def test_pc_profile(self):
        self.assertEqual(v.PC_PROFILE[:6], ["--cpus", "10", "--memory", "8g", "--max-workers", "10"])
        src = (ROOT / "sweeps" / "v267_seeds.py").read_text()
        self.assertTrue(re.search(r'"--decision-rule", "non_erosion"', src))


if __name__ == "__main__":
    unittest.main()
