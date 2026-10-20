"""Tests de contrat V269 : relachement tardif du vivier rail (v269_rail_late_relax)."""
from pathlib import Path
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class TestV269RailLateRelax(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read("info.nut")
        cls.settings = read("settings.nut")
        cls.globals = read("globals_pre.nut")
        cls.candidates = read("candidates.nut")
        cls.orchestrator = read("orchestrator.nut")

    def test_setting_declared_in_info(self):
        self.assertIn('name = "v269_rail_late_relax"', self.info)
        start = self.info.index('name = "v269_rail_late_relax"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 9", block)
        self.assertIn("easy_value = 5", block)
        self.assertIn("medium_value = 5", block)
        self.assertIn("hard_value = 5", block)
        self.assertIn("custom_value = 5", block)
        self.assertIn("flags = 0", block)

    def test_setting_loaded_in_settings(self):
        self.assertEqual(self.settings.count('GetSetting("v269_rail_late_relax")'), 1)
        self.assertIn("V269_RAIL_LATE_RELAX = (lateRelax != null && lateRelax > 0 && lateRelax <= 9) ? lateRelax : 0;", self.settings)

    def test_globals_declared(self):
        self.assertIn("V269_RAIL_LATE_RELAX <- 5;", self.globals)
        self.assertIn("V269_RAIL_MAX_DIST <- 250;", self.globals)
        self.assertIn("V269_IDLE_CASH_MIN <- 1000000;", self.globals)
        self.assertIn("V269_RELAXED <- false;", self.globals)
        self.assertIn("V269_ON <- false;", self.globals)

    def test_v269_independent_of_v270(self):
        # V269 ne doit pas dependre de symboles V270 dans orchestrator
        start = self.orchestrator.index("V269_RAIL_LATE_RELAX > 0")
        end = self.orchestrator.index("OpexRegenerateModeProjects", start)
        block = self.orchestrator[start:end]
        self.assertNotIn("V270", block)
        self.assertIn("V269_IDLE_CASH_MIN", block)

    def test_candidates_freight_bound_relaxed_only_when_active(self):
        self.assertIn("distance > ((V269_RAIL_LATE_RELAX > 0 && V269_RELAXED && V269_RAIL_MAX_DIST > bounds.railMax) ? V269_RAIL_MAX_DIST : bounds.railMax)", self.candidates)

    def test_no_v178_v179_toggle_after_v263b(self):
        # V263b a fige V178/V179 a 1 et retire leurs globales.
        self.assertNotIn("V178_RAIL_SHARED_DEST", self.orchestrator)
        self.assertNotIn("V179_RAIL_GEN_DEST_SERVED", self.orchestrator)


if __name__ == "__main__":
    unittest.main()
