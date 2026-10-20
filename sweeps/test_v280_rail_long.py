"""Contrats V280 : portée fret tardive, chemin historique et réglage OFF."""
from pathlib import Path
import hashlib
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"


def body(text, signature):
    start = text.index(signature)
    return text[start:text.index("\n}\n", start) + 3]


class RailLong(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.candidate = body(cls.sources["candidates.nut"], "function OpexMakeCandidate(")
        cls.helper = body(cls.sources["candidates.nut"], "function OpexV280RailLongAllowed(")

    def test_setting_integer_off_on_all_difficulties(self):
        block = re.search(r'name = "v280_rail_long",(.*?)\}\);', self.sources["info.nut"], re.S)[1]
        for name in ("easy", "medium", "hard", "custom", "default"):
            self.assertRegex(block, name + r"_value = 0\b")
        for declaration in ("min_value = 0", "max_value = 10", "step_size = 1", "flags = 0"):
            self.assertIn(declaration, block)

    def test_read_once_bounded_and_global(self):
        self.assertEqual(sum(s.count('GetSetting("v280_rail_long")') for s in self.sources.values()), 1)
        self.assertIn("V280_RAIL_LONG <- 0;", self.sources["globals_pre.nut"])
        self.assertIn("(railLong != null && railLong >= 0 && railLong <= 10) ? railLong : 0;",
                      self.sources["settings.nut"])

    def test_master_candidate_path_except_guard_is_identical(self):
        # Empreinte de la fonction intégrale de master e302de5, sans appel à Git requis.
        historical = self.candidate.replace(
            "distance > bounds.railMax && !(V280_RAIL_LONG > 0 && OpexV280RailLongAllowed(distance, srcTile, dstTile))",
            "distance > bounds.railMax")
        self.assertEqual(hashlib.sha256(historical.encode()).hexdigest(),
                         "e8f5e8d412771787b248b2470e661bc16b8d5c696a9e3300c3a6dd3fd37bb6a0")

    def test_short_circuit_only_out_of_band_freight(self):
        guard = "} else if (distance > bounds.railMax && !(V280_RAIL_LONG > 0 && OpexV280RailLongAllowed(distance, srcTile, dstTile))) {"
        self.assertIn(guard, self.candidate)
        # Le pax retourne avant la branche else : V177 et borne pax restent intacts.
        self.assertLess(self.candidate.index('if (kind == "pax")'), self.candidate.index(guard))
        self.assertEqual(sum(s.count("OpexV280RailLongAllowed(") for s in self.sources.values()), 2)
        self.assertIn("stats.distanceLong++;\n    return null;", self.candidate)

    def test_age_capital_and_distance_are_rechecked_without_cache(self):
        for guard in ("if (distance > 350) return false;",
                      "< OPEX_START_YEAR + V280_RAIL_LONG) return false;",
                      "if (OpexAvailableCapital() < 1000000) return false;"):
            self.assertIn(guard, self.helper)
        self.assertNotIn("1970", self.helper)
        self.assertNotIn("<-", self.helper)
        self.assertNotIn("catalog.bounds", self.helper)
        self.assertIn("if (DECISION_LOG) OpexDecide(\"V280_RAIL_LONG\"", self.helper)

    def test_no_extra_loop_hook_or_saved_behavioral_state(self):
        for module in ("main.nut", "probes.nut", "persist.nut", "scheduler.nut"):
            self.assertNotIn("V280", self.sources[module])
        self.assertFalse(any("V280_DIAG_MAP_LOGGED" in s or "V280_INDUSTRY" in s
                             for s in self.sources.values()))

    def test_branch_setting_ceiling(self):
        self.assertEqual(self.sources["info.nut"].count("AddSetting("), 83)
        for test in ("test_v246_fixed_policies.py", "test_v251_inventory.py", "test_v259_bridge_renew.py"):
            self.assertIn('count("AddSetting("), 102)', (ROOT / "sweeps" / test).read_text())


if __name__ == "__main__":
    unittest.main()
