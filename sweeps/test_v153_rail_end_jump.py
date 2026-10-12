#!/usr/bin/env python3
"""Contrats du raccordement terminal rail sur saut (pont/tunnel) - V153."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1:pos]
    raise AssertionError(f"corps non ferme: {signature}")


class TestV153RailEndJump(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = source("info.nut")
        cls.globals = source("globals_pre.nut")
        cls.settings = source("settings.nut")
        cls.builder = source("builder_rail.nut")

    def test_setting_declared_and_default_off(self):
        self.assertIn('name = "rail_end_jump_connect"', self.info)
        start = self.info.index('name = "rail_end_jump_connect"')
        block = self.info[start:self.info.index("});", start)]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"\b{level}_value\s*=\s*0\b")
        self.assertIn("flags = AICONFIG_BOOLEAN", block)

    def test_global_and_setting_load(self):
        self.assertIn("RAIL_END_JUMP_CONNECT <- false;", self.globals)
        self.assertIn(
            'RAIL_END_JUMP_CONNECT = AIController.GetSetting("rail_end_jump_connect") != 0;',
            self.settings,
        )

    def test_opex_rail_end_connected_contract(self):
        body = function_body(self.builder, "function OpexRailEndConnected(")
        # Default guard returns legacy AreTilesConnected
        self.assertIn("!RAIL_END_JUMP_CONNECT || AIMap.DistanceManhattan(lead, inner) <= 1", body)
        self.assertIn("return AIRail.AreTilesConnected(outer, lead, inner);", body)

        # Bridge and tunnel endpoints
        self.assertIn("AIBridge.IsBridgeTile(lead) && AIBridge.GetOtherBridgeEnd(lead) == inner", body)
        self.assertIn("AITunnel.IsTunnelTile(lead) && AITunnel.GetOtherTunnelEnd(lead) == inner", body)

        # Collinearity and unit step
        self.assertIn("local d = AIMap.DistanceManhattan(lead, inner);", body)
        self.assertIn("local unit = (lead - inner) / d;", body)
        self.assertIn("outer == lead + unit", body)

        # Track continuity
        self.assertIn("AIMap.IsValidTile(nextTile)", body)
        self.assertIn("AIRail.AreTilesConnected(lead, outer, nextTile)", body)
        self.assertIn("AIRail.IsRailTile(outer)", body)

        # Exposure logging under DECISION_LOG
        self.assertIn("if (DECISION_LOG)", body)
        self.assertIn('OpexDecide("RAIL_END_JUMP"', body)
        self.assertIn("side=", body)
        self.assertIn("kind=", body)
        self.assertIn("lead=", body)
        self.assertIn("inner=", body)
        self.assertIn("outer=", body)

    def test_callsites_in_execute_rail_plan(self):
        body = function_body(self.builder, "function OpexExecuteRailPlan(")
        self.assertIn('OpexRailEndConnected(planA.station_exit, tiles[1], tiles[2], "A")', body)
        self.assertIn('OpexRailEndConnected(planB.station_exit, tiles[last - 1], tiles[last - 2], "B")', body)

    def test_no_squirrel_pitfalls(self):
        body = function_body(self.builder, "function OpexRailEndConnected(")
        for word in ("clone", "base", "parent"):
            self.assertIsNone(re.search(rf"\b{word}\b", body), f"mot reserve: {word}")
        self.assertNotIn("local function", body)
        self.assertIsNone(re.search(r"=\s*function\s*\(", body), "closure non autorisee")

    def test_synthetic_collinearity_math(self):
        # Simulation for X axis (step = 1)
        map_size_x = 256
        inner_x = 100
        lead_x = 103  # bridge of length 3 tiles
        d_x = abs(lead_x - inner_x)
        unit_x = (lead_x - inner_x) // d_x
        outer_x = lead_x + unit_x
        self.assertEqual(unit_x, 1)
        self.assertEqual(outer_x, 104)

        # Simulation for Y axis (step = map_size_x)
        inner_y = 100
        lead_y = inner_y + 4 * map_size_x
        d_y = 4
        unit_y = (lead_y - inner_y) // d_y
        outer_y = lead_y + unit_y
        self.assertEqual(unit_y, map_size_x)
        self.assertEqual(outer_y, lead_y + map_size_x)


if __name__ == "__main__":
    unittest.main()
