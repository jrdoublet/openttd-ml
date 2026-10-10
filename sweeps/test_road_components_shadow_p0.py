"""Static regression contracts for the ROAD B0 *passive* cost decomposition."""

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class RoadComponentsContracts(unittest.TestCase):
    def test_default_off(self):
        info = source("info.nut")
        group = re.search(r'name = "road_quote_components_shadow_p0",(.*?)\}\);', info, re.S)
        self.assertIsNotNone(group)
        for k in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(group.group(1), rf"\b{k}\s*=\s*0\b")
        self.assertIn('ROAD_QUOTE_COMPONENTS_SHADOW_P0 = AIController.GetSetting(',
                      source("settings.nut"))
        self.assertIn('ROAD_QUOTE_COMPONENTS_SHADOW_P0 <- false;',
                      source("globals_pre.nut"))
        # En Squirrel, affecter un global inconnu avec = dans
        # OpexLoadSettings leve "the index ... does not exist" au demarrage.
        # Un reglage valide dans info.nut ne suffit pas.
        self.assertRegex(source("globals_pre.nut"),
                         r"(?m)^ROAD_QUOTE_COMPONENTS_SHADOW_P0\s*<-\s*false\s*;")

    def test_only_uses_existing_tariffs_and_geometry(self):
        builder = source("builder_road.nut")
        helper = builder.split('function OpexRoadQuotePlanComponents(', 1)[1].split('\n}', 1)[0]
        self.assertIn('AreRoadTilesConnected', helper)
        self.assertIn('plan.trace', helper)
        self.assertIn('candidate.trains * candidate.engine.price', helper)
        self.assertIn('catalog.costRoadPerTile', helper)
        self.assertNotIn('AITestMode()', helper)
        self.assertNotIn('AIAccounting()', helper)
        self.assertNotIn('candidate.capital =', helper)
        self.assertNotIn('capitalIsActual', helper)

    def test_real_success_phase_bookkeeping(self):
        builder = source("builder_road.nut")
        self.assertIn('p0TraceSpend = costs.GetCosts();', builder)
        self.assertIn('p0StopsSpend = costs.GetCosts();', builder)
        self.assertIn('p0DepotSpend = costs.GetCosts();', builder)
        self.assertIn('vehicles = result.actualCost - p0DepotSpend', builder)
        task = source("task_road.nut")
        self.assertIn('ROAD_COMPONENTS_P0 date=', task)
        self.assertIn('OpexOpsMeasureBegin()', task)
        self.assertIn('OpexOpsMeasureEnd(roadComponentsOpsMark)', task)
        self.assertIn('quote_ops=', task)
        self.assertIn('result.ok && nBuilt == candidate.trains', task)
        self.assertNotIn('if (ROAD_QUOTE_COMPONENTS_SHADOW_P0) candidate.capital', task)
        self.assertNotIn('if (ROAD_QUOTE_COMPONENTS_SHADOW_P0) return',
                         source("projects_finance.nut"))


if __name__ == "__main__":
    unittest.main()
