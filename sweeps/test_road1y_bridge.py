"""ROAD1Y-BRIDGE : contrat de road1y_bridge (ponts routiers A*, defaut 0).

Longueur maximale de pont en tuiles d'eau ou de rail franchies (0..6).
Hors route seule le chargement force 0 aux deux chargeurs.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from test_v261_forum_behaviours import body, source

AI = ROOT / "ai" / "OpexAI"


class TestRoad1yBridge(unittest.TestCase):
    def test_setting_declaration_and_bounds(self):
        info = source("info.nut")
        self.assertEqual(info.count('name = "road1y_bridge"'), 1)
        block = info.split('name = "road1y_bridge",')[1].split("});")[0]
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 6", block)
        self.assertIn("flags = 0", block)
        self.assertNotIn("AICONFIG_BOOLEAN", block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{difficulty}_value = 0", block)
        self.assertIn("ROAD1Y_BRIDGE <- 0;", source("globals_pre.nut"))

    def test_loaded_clamped_and_gated_in_both_loaders(self):
        settings = source("settings.nut")
        self.assertEqual(settings.count('GetSetting("road1y_bridge")'), 2)
        for loader_name in ("OpexLoadSettings", "OpexLoadBusDistrictSettings"):
            load = body("settings.nut", loader_name)
            self.assertIn('ROAD1Y_BRIDGE = AIController.GetSetting("road1y_bridge");', load)
            self.assertIn("if (ROAD1Y_BRIDGE < 0 || ROAD1Y_BRIDGE > 6) ROAD1Y_BRIDGE = 0;", load)
            self.assertIn("if (!road1yRoadOnly) ROAD1Y_BRIDGE = 0;", load)
            read_at = load.index('GetSetting("road1y_bridge")')
            clamp_at = load.index("if (ROAD1Y_BRIDGE < 0 || ROAD1Y_BRIDGE > 6) ROAD1Y_BRIDGE = 0;")
            gate_at = load.index("if (!road1yRoadOnly) ROAD1Y_BRIDGE = 0;")
            self.assertLess(read_at, clamp_at)
            self.assertLess(clamp_at, gate_at)
        self.assertNotIn("road1y_bridge", source("persist.nut"))
        self.assertNotIn("ROAD1Y_BRIDGE", source("persist.nut"))

    def test_module_squirrel_safety(self):
        code = source("road1y_astar.nut")
        for word in ("clone", "base", "parent", "static", "delegate",
                     "vargc", "vargv", "resume", "yield", "constructor", "instanceof"):
            self.assertNotRegex(code, r"\blocal\s+" + word + r"\b", word)
        self.assertNotIn("function(", code)
        self.assertNotIn(".find(", code)
        for block in re.findall(r"try\s*\{[^}]*\}", code, re.DOTALL):
            self.assertNotIn("yield", block)

    def test_bridge_ramp_slope_function(self):
        code = source("road1y_astar.nut")
        self.assertIn("function OpexRoad1yBridgeRampOk(tile, d, stepX)", code)
        ramp_fn = body("road1y_astar.nut", "OpexRoad1yBridgeRampOk")
        self.assertIn("AITile.SLOPE_FLAT", ramp_fn)
        self.assertIn("AITile.SLOPE_SW", ramp_fn)
        self.assertIn("AITile.SLOPE_NE", ramp_fn)
        self.assertIn("AITile.SLOPE_SE", ramp_fn)
        self.assertIn("AITile.SLOPE_NW", ramp_fn)

    def test_bridge_price_sort_function(self):
        code = source("road1y_astar.nut")
        self.assertIn("function OpexRoad1yBridgeSortPrice(a, b)", code)
        sort_fn = body("road1y_astar.nut", "OpexRoad1yBridgeSortPrice")
        self.assertIn("a.price < b.price", sort_fn)
        self.assertIn("a.price > b.price", sort_fn)

    def test_search_jump_neighbor_structure(self):
        code = body("road1y_astar.nut", "OpexRoad1yAStarSearch")
        self.assertIn("if (ROAD1Y_BRIDGE > 0", code)
        self.assertIn("AITile.IsWaterTile(nxt1) || AIRail.IsRailTile(nxt1)", code)
        self.assertIn("for (local k = 2; k <= ROAD1Y_BRIDGE + 1; k++)", code)
        self.assertIn("4 * k + 6", code)
        self.assertIn("bridge = true", code)

    def test_trace_validation_and_decision_log(self):
        code = body("road1y_astar.nut", "OpexRoad1yAStarTrace")
        self.assertIn("AIBridgeList_Length(edge.len + 1)", code)
        self.assertIn("AIBridge.GetPrice(bridgeId, edge.len + 1)", code)
        self.assertIn("AIBridge.BuildBridge(AIVehicle.VT_ROAD, c.id, edge.from, edge.to)", code)
        self.assertIn('bridges=" + nBridges', code)
        self.assertIn('bridgeTiles=" + sumBridgeTiles', code)

    def test_build_trace_and_rollback(self):
        code = source("road1y_astar.nut")
        self.assertIn("function OpexRoadBuildTrace(trace, added)", code)
        self.assertIn("AIBridge.BuildBridge(AIVehicle.VT_ROAD, edge.id, edge.from, edge.to)", code)
        self.assertIn('OpexDecide("ROAD1Y_BRIDGE"', code)
        self.assertIn("from=", code)
        self.assertIn("to=", code)
        self.assertIn("len=", code)
        self.assertIn("id=", code)
        self.assertIn("price=", code)
        self.assertIn("ok=", code)
        self.assertIn("AIBridge.RemoveBridge(edge.from)", code)


if __name__ == "__main__":
    unittest.main()
