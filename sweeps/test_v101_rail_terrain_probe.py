#!/usr/bin/env python3
"""Contrat statique de la sonde de terrain au demarrage d'une recherche rail.

probe_rail_terrain vaut 0 aux quatre difficultes. OpexRailTerrainProbe sort
avant tout appel d'API si RAIL_TERRAIN_PROBE est faux. Aucune partie OpenTTD
n'est lancee.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EMITTED_KEYS = (
    "src=",
    "dst=",
    "n=",
    "flat=",
    "water=",
    "bld=",
    "hmin=",
    "hmax=",
    "hspread=",
    "steps=",
    "rough=",
)


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _setting_block(info, name):
    start = info.index(f'name = "{name}"')
    return info[start:info.index("});", start)]


def _function_body(source, signature):
    start = source.index(signature)
    nxt = source.find("\nfunction ", start + 1)
    if nxt < 0:
        nxt = len(source)
    return source[start:nxt]


class TestRailTerrainProbeContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.probes = _read("ai/OpexAI/probes.nut")
        cls.task_rail = _read("ai/OpexAI/task_rail.nut")
        cls.probe_body = _function_body(
            cls.probes, "function OpexRailTerrainProbe(src, dst)"
        )
        cls.start_body = _function_body(
            cls.task_rail, "function OpexAI::_startRailSearch("
        )

    def test_setting_declared_inert_in_info_nut(self):
        block = _setting_block(self.info, "probe_rail_terrain")
        self.assertIn(
            "log a cheap terrain-roughness summary of the straight line between "
            "both stations when a rail A* search starts, to test whether terrain "
            "predicts iteration-cap abandons; 0 = off (default)",
            block,
        )
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)
        self.assertIn("step_size = 1", block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 0", block)
        self.assertEqual(self.info.count('name = "probe_rail_terrain"'), 1)

    def test_global_declared_and_loaded_once(self):
        self.assertIn("RAIL_TERRAIN_PROBE <- false;", self.globals)
        self.assertEqual(self.globals.count("RAIL_TERRAIN_PROBE <-"), 1)
        needle = 'AIController.GetSetting("probe_rail_terrain")'
        self.assertEqual(self.settings.count(needle), 1)
        self.assertIn(
            'RAIL_TERRAIN_PROBE = AIController.GetSetting("probe_rail_terrain") != 0;',
            self.settings,
        )
        self.assertNotIn("RAIL_TERRAIN_PROBE <-", self.settings)

    def test_probe_returns_before_any_api_when_disabled(self):
        body = self.probe_body
        self.assertEqual(self.probes.count("function OpexRailTerrainProbe("), 1)
        guard = body.index("if (!RAIL_TERRAIN_PROBE) return;")
        self.assertLess(guard, body.index("AIMap."))
        self.assertLess(guard, body.index("AITile."))
        self.assertLess(guard, body.index("OpexDecide("))
        self.assertIn("for (local i = 0; i < 16; i++)", body)
        self.assertIn("AIMap.IsValidTile(t)", body)
        self.assertIn("AITile.SLOPE_FLAT", body)
        self.assertIn("AITile.IsWaterTile(t)", body)
        self.assertIn("AITile.IsBuildable(t)", body)
        self.assertIn("AITile.GetMinHeight(t)", body)

    def test_emitted_line_contains_terrain_keys(self):
        decide = self.probe_body.index('OpexDecide("RAIL_TERRAIN"')
        emitted = self.probe_body[decide:]
        cursor = 0
        for key in EMITTED_KEYS:
            found = emitted.find(key, cursor)
            self.assertGreaterEqual(found, 0, key)
            cursor = found + len(key)
        self.assertIn('hspread=" + (hmax - hmin)', emitted)

    def test_called_once_at_start_of_primary_search(self):
        self.assertEqual(self.task_rail.count("OpexRailTerrainProbe("), 1)
        self.assertEqual(self.start_body.count("OpexRailTerrainProbe("), 1)
        call = self.start_body.index(
            "OpexRailTerrainProbe(candidate.src, candidate.dst);"
        )
        prepare = self.start_body.index("OpexPrepareRailRoute(")
        self.assertLess(call, prepare)


if __name__ == "__main__":
    unittest.main()
