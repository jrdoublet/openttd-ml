"""Contract of the minimal, default-OFF cold realization gate."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"


class ColdExemptContracts(unittest.TestCase):
    def test_all_four_defaults_are_zero(self):
        info = (AI / "info.nut").read_text(encoding="utf-8")
        block = info.split('name = "c121_kdec_cold_exempt",')[1].split("});")[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{difficulty}_value\s*=\s*0\b")
        self.assertIn("AICONFIG_BOOLEAN", block)

    def test_requires_c121_and_has_no_persisted_behavioral_state(self):
        settings = (AI / "settings.nut").read_text(encoding="utf-8")
        self.assertIn('C121_KDEC_COLD_EXEMPT = C121_AIR_ECONOMICS\n      && AIController.GetSetting("c121_kdec_cold_exempt") != 0;', settings)
        self.assertIn("C121_KDEC_COLD_EXEMPT <- false;", (AI / "globals_pre.nut").read_text(encoding="utf-8"))
        self.assertNotIn("C121_KDEC_COLD_EXEMPT", (AI / "persist.nut").read_text(encoding="utf-8"))

    def test_off_path_retains_original_return_byte_for_byte(self):
        text = (AI / "projects_models.nut").read_text(encoding="utf-8")
        block = text.split("function OpexC121ProjectHasRealization(project, requireObservedMarginal = true)")[1].split("/* C70")[0]
        old_return = '    return ("c121MarginalProfit" in line) && ("c121MarginalRevenue" in line);'
        self.assertIn(old_return, block)
        self.assertEqual(block.count("C121_KDEC_COLD_EXEMPT"), 1)
        self.assertRegex(block, r'if \(C121_KDEC_COLD_EXEMPT && requireObservedMarginal\s+&& \(!\("c121MarginalSamples" in line\) \|\| line.c121MarginalSamples <= 0\)\) return false;')
        air_branch, fleet_branch = block.split('if (project.mode == "fleet"')
        self.assertNotIn("C121_KDEC_COLD_EXEMPT", air_branch)
        self.assertLess(fleet_branch.index("return false"), fleet_branch.index(old_return.strip()))

    def test_calibration_numerator_uses_original_estimate_presence(self):
        text = (AI / "projects_models.nut").read_text(encoding="utf-8")
        for name, end in (("function OpexC70Profit", "function OpexC82Profit"),
                          ("function OpexC82Profit", "OpexCalibratedProfit <-")):
            block = text[text.index(name):text.index(end)]
            self.assertIn("OpexC121ProjectHasRealization(project, false)", block)
        selection = (AI / "projects_selection.nut").read_text(encoding="utf-8")
        self.assertEqual(selection.count("OpexC121ProjectHasRealization(project)"), 3)

    def test_gate_is_not_used_to_change_any_other_policy(self):
        sites = []
        for path in AI.glob("*.nut"):
            if "C121_KDEC_COLD_EXEMPT" in path.read_text(encoding="utf-8"):
                sites.append(path.name)
        self.assertEqual(sorted(sites), ["globals_pre.nut", "projects_models.nut", "settings.nut"])


if __name__ == "__main__":
    unittest.main()
