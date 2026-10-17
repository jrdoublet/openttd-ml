#!/usr/bin/env python3
"""Contrat statique de retrait de la sonde de terrain au demarrage d'une recherche rail.

probe_rail_terrain est retiree (defaut 0).
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class TestRailTerrainProbeContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.probes = _read("ai/OpexAI/probes.nut")
        cls.task_rail = _read("ai/OpexAI/task_rail.nut")

    def test_setting_retired_from_info_and_settings(self):
        self.assertNotIn('name = "probe_rail_terrain"', self.info)
        self.assertNotIn("probe_rail_terrain", self.settings)

    def test_global_retired(self):
        self.assertNotIn("RAIL_TERRAIN_PROBE", self.globals)
        self.assertNotIn("RAIL_TERRAIN_PROBE", self.settings)

    def test_probe_function_and_calls_retired(self):
        self.assertNotIn("function OpexRailTerrainProbe(", self.probes)
        self.assertNotIn("OpexRailTerrainProbe(", self.task_rail)


if __name__ == "__main__":
    unittest.main()

