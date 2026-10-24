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
    def test_declared_default_fifteen(self):
        info = read_file("info.nut")
        block = info[info.index('name = "v275_rail_pax_mm"'):]
        block = block[:block.index("});")]
        self.assertIn("min_value = 0, max_value = 15", block)
        self.assertIn("easy_value = 15, medium_value = 15, hard_value = 15", block)
        self.assertIn("custom_value = 15", block)
        self.assertIn("V275_RAIL_PAX_MM <- 15;", read_file("globals_pre.nut"))

    def test_read_and_bounded(self):
        settings = read_file("settings.nut")
        self.assertIn('AIController.GetSetting("v275_rail_pax_mm")', settings)
        self.assertIn("V275_RAIL_PAX_MM = (v275 != null && v275 >= 0 && v275 <= 15) ? v275 : 0;", settings)

    def test_bit8_by_mode(self):
        settings = read_file("settings.nut")
        body = settings[settings.index("if (V275_RAIL_PAX_MM & 8) {"):]
        body = body[:body.index("local v190Delay")]
        # Avec l'aerien : masque entier ramene a 0 (comportement d'avant V275).
        self.assertIn("if (MODE_AIR) {\n      V275_RAIL_PAX_MM = 0;", body)
        # Sans aerien : paquet V207 seulement si les reglages V207 sont au defaut.
        self.assertIn("V207_RAIL_PAX_SHARE_PCT == 0 && !V207_RAIL_MAIL && V207_RAIL_PAX_JOINED_STOPS == 0", body)
        self.assertIn("V207_RAIL_PAX_SHARE_PCT = 40;", body)
        self.assertIn("V207_RAIL_MAIL = true;", body)
        self.assertIn("V207_RAIL_PAX_JOINED_STOPS = 2;", body)
        # Lu apres MODE_AIR et apres les reglages V207.
        self.assertLess(settings.index('MODE_AIR = AIController.GetSetting("mode_air")'), settings.index("if (V275_RAIL_PAX_MM & 8) {"))
        self.assertLess(settings.index('V207_RAIL_PAX_JOINED_STOPS = (v207Stops'), settings.index("if (V275_RAIL_PAX_MM & 8) {"))


class TestV275Candidates(unittest.TestCase):
    def setUp(self):
        self.body = function_body(read_file("candidates.nut"), "OpexPaxCandidates")

    def test_air_first_gate_retired(self):
        self.assertNotIn("V275_RAIL_PAX_MM & 4", self.body)  # bit 4 retire le 24/10
        self.assertNotIn("< OPEX_START_YEAR + 2) return;", self.body)

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
        self.assertIn('if (kind == "pax" && (V275_RAIL_PAX_MM & 2)) {', body)
        self.assertIn("result.revenueAnnual = (result.revenueAnnual * 150) / 100;", body)
        self.assertIn("result.capital = (result.capital * 85) / 100;", body)


if __name__ == "__main__":
    unittest.main()
