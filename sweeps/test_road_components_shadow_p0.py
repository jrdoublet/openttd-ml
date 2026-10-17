"""Retirement contracts for the ROAD B0 passive cost decomposition."""
import unittest
from pathlib import Path
AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
def source(name):
    return (AI / name).read_text(encoding="utf-8")
class RoadComponentsContracts(unittest.TestCase):
    def test_setting_and_globals_removed(self):
        for name in ("info.nut", "settings.nut", "globals_pre.nut"):
            self.assertNotIn("road_quote_components_shadow_p0", source(name))
            self.assertNotIn("ROAD_QUOTE_COMPONENTS_SHADOW_P0", source(name))
    def test_quote_helper_and_phase_bookkeeping_removed(self):
        builder = source("builder_road.nut")
        for token in ("OpexRoadQuotePlanComponents", "p0TraceSpend", "p0StopsSpend",
                      "p0DepotSpend", "phaseCosts"):
            self.assertNotIn(token, builder)
        self.assertIn("local costs = AIAccounting();", builder)
        self.assertIn("result.actualCost = costs.GetCosts();", builder)
    def test_task_keeps_real_build_without_shadow(self):
        task = source("task_road.nut")
        self.assertIn("OpexBuildRoadRoute(this._catalog, this._budget, plan, candidate)", task)
        self.assertNotIn("roadComponents", task)
        self.assertNotIn("ROAD_COMPONENTS_P0", task)
