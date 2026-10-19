#!/usr/bin/env python3
"""Contrats statiques de V275 : rail voyageurs compatible avec l'aerien (masque de bits).

1 = aucune paire rail voyageurs touchant une ville ou nous avons un aeroport ;
2 = recalage V212 150/85 ; 4 = aerien actif : pas de candidat rail voyageurs avant la 3e annee.
Defaut 0 : chemin inchange.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_DIR = ROOT / "ai" / "OpexAI"


def read_file(rel_path: str) -> str:
    return (AI_DIR / rel_path).read_text(encoding="utf-8")


def function_body(source: str, name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\(", source)
    if not match:
        raise AssertionError(f"Function {name} not found")
    start = source.index("{", match.end())
    depth = 0
    for i in range(start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError(f"Unterminated {name}")


class TestV275Setting(unittest.TestCase):
    def test_declared_default_zero(self):
        info = read_file("info.nut")
        block = info[info.index('name = "v275_rail_pax_mm"'):]
        block = block[:block.index("});")]
        self.assertIn("min_value = 0, max_value = 15", block)
        self.assertIn("easy_value = 0, medium_value = 0, hard_value = 0", block)
        self.assertIn("custom_value = 0", block)
        self.assertIn("V275_RAIL_PAX_MM <- 0;", read_file("globals_pre.nut"))

    def test_read_and_bounded(self):
        settings = read_file("settings.nut")
        self.assertIn('AIController.GetSetting("v275_rail_pax_mm")', settings)
        self.assertIn("V275_RAIL_PAX_MM = (v275 != null && v275 >= 0 && v275 <= 15) ? v275 : 0;", settings)

    def test_bit8_disables_package_with_air(self):
        settings = read_file("settings.nut")
        start = settings.index("if ((V275_RAIL_PAX_MM & 8) && MODE_AIR) {")
        block = settings[start:settings.index("}", start)]
        for name in ("V207_RAIL_PAX_SHARE_PCT = 0;", "V207_RAIL_MAIL = false;",
                     "V207_RAIL_PAX_JOINED_STOPS = 0;", "V207_RAIL_PAX_SITE_RANK_PCT = 0;",
                     "V275_RAIL_PAX_MM = 0;"):
            self.assertIn(name, block)
        # MODE_AIR est lu (et borne par la partie) avant le paquet.
        self.assertLess(settings.index('MODE_AIR = AIController.GetSetting("mode_air") != 0;'), start)
        self.assertLess(settings.index('AIController.GetSetting("v207_rail_pax_site_rank_pct")'), start)


class TestV275Candidates(unittest.TestCase):
    def setUp(self):
        self.body = function_body(read_file("candidates.nut"), "OpexPaxCandidates")

    def test_air_first_gate_needs_air_and_persisted_start(self):
        self.assertIn("(V275_RAIL_PAX_MM & 4) && MODE_AIR", self.body)
        self.assertIn("AIDate.GetYear(AIDate.GetCurrentDate()) < OPEX_START_YEAR + 2) return;", self.body)
        self.assertLess(self.body.index("V275_RAIL_PAX_MM & 4"), self.body.index("local towns = catalog.towns;"))

    def test_air_towns_from_live_air_lines(self):
        self.assertIn("if (V275_RAIL_PAX_MM & 1) {", self.body)
        self.assertIn('line.mode != "air"', self.body)
        self.assertIn("airTowns.rawset(line.originA, true);", self.body)
        self.assertIn("airTowns.rawset(line.originB, true);", self.body)

    def test_pair_skip_after_rail_served_check(self):
        served = self.body.index("stats.pairsOriginServed++;")
        skip = self.body.index("(towns[a].tile in airTowns) || (towns[b].tile in airTowns)")
        make = self.body.index("OpexMakeCandidate(")
        self.assertLess(served, skip)
        self.assertLess(skip, make)
        self.assertIn("if (airTowns != null && ", self.body)


class TestV275Economics(unittest.TestCase):
    def test_bit2_selects_v212_values(self):
        body = function_body(read_file("economy.nut"), "OpexLineEconomics")
        self.assertIn("local v212Revenue = (V275_RAIL_PAX_MM & 2) ? 150 : V212_RAIL_PAX_REVENUE_PCT;", body)
        self.assertIn("local v212Capital = (V275_RAIL_PAX_MM & 2) ? 85 : V212_RAIL_PAX_CAPITAL_PCT;", body)


if __name__ == "__main__":
    unittest.main()
