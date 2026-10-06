import unittest
from pathlib import Path
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air
from opex_projects_source import read_projects_source

ROOT = Path(__file__).resolve().parents[1]
AIR = read_builder_air()
PROJECTS = read_projects_source()
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")

class C113AirC100FullDecisionShadowTests(unittest.TestCase):
    def test_setting_is_off_by_default_and_extends_c111(self):
        self.assertIn("C113_AIR_C100_FULL_DECISION_SHADOW <- false;", GLOBALS)
        start = INFO.index('name = "c113_air_c100_full_decision_shadow"')
        snippet = INFO[start:start + 760]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)
        self.assertIn('AIController.GetSetting("c113_air_c100_full_decision_shadow")', SETTINGS)
        self.assertIn("if (C113_AIR_C100_FULL_DECISION_SHADOW) C111_AIR_C100_DECISION_SHADOW = true;", SETTINGS)

    def test_all_three_air_arms_use_c68_shadow_for_pre_admission(self):
        marker = "local admissionEconomics = (C113_AIR_C100_FULL_DECISION_SHADOW && decisionEconomics != null)"
        self.assertEqual(AIR.count(marker), 3)
        self.assertGreaterEqual(AIR.count("admissionEconomics.profitAnnual <= 0"), 4)

    def test_hubhub_does_not_reject_on_equipment_profit_after_shadow(self):
        start = AIR.index("function OpexAirPlansHubToHub(")
        end = AIR.index("/* V95", start)
        body = AIR[start:end]
        self.assertIn("if (admissionEconomics.profitAnnual <= 0) continue;", body)
        self.assertNotIn("if (plan.economics.profitAnnual <= 0) continue;", body)

    def test_equipment_profit_is_not_an_admission_guard_under_c113(self):
        self.assertIn("(!C113_AIR_C100_FULL_DECISION_SHADOW && equipment.economics.profitAnnual <= 0)", AIR)
        self.assertIn("(!C113_AIR_C100_FULL_DECISION_SHADOW && economics.profitAnnual <= 0)", PROJECTS)
        self.assertIn("local projectEconomics = useInitialProjectEconomics ? economics : decisionEconomics;", PROJECTS)
        self.assertIn("profitAnnual = projectEconomics.profitAnnual", PROJECTS)
        self.assertIn("capital = economics.capital", PROJECTS)

if __name__ == "__main__":
    unittest.main()
