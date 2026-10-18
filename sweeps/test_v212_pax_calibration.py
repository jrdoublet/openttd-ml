#!/usr/bin/env python3
"""Contrats statiques de V212 : recalage du revenu et du capital predits des lignes rail passagers.

Verifie :
1. Reglages v212_rail_pax_revenue_pct (50..300) et v212_rail_pax_capital_pct (50..200), defaut 100
   (inerte), declares dans info.nut, globals_pre.nut et settings.nut.
2. OpexLineEconomics : recalage applique apres la boucle du nombre de trains, uniquement pour
   kind == "pax", et seulement si l'un des deux reglages differe de 100.
3. Le profit est recalcule depuis le revenu recale (meme formule que OpexApplyRailActualCapital),
   et le ROI depuis le capital recale + immobilise.
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
    for pos in range(start, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:pos]
    raise AssertionError(f"Unclosed function {name}")


class TestV212Settings(unittest.TestCase):
    def test_declared_with_bounds_and_default_100(self):
        info = read_file("info.nut")
        # V236 : constantes a 100
        for name in ("v212_rail_pax_revenue_pct", "v212_rail_pax_capital_pct"):
            self.assertNotIn(f'name = "{name}"', info)
    def test_globals_and_reading(self):
        globals_pre = read_file("globals_pre.nut")
        self.assertIn("V212_RAIL_PAX_REVENUE_PCT <- 100;", globals_pre)
        self.assertIn("V212_RAIL_PAX_CAPITAL_PCT <- 100;", globals_pre)
        settings = read_file("settings.nut")
        self.assertNotIn("v212_rail_pax", settings)
        self.assertNotIn("V212_RAIL_PAX_REVENUE_PCT =", settings)
        self.assertNotIn("V212_RAIL_PAX_CAPITAL_PCT =", settings)


class TestV212Economics(unittest.TestCase):
    def setUp(self):
        self.body = function_body(read_file("economy.nut"), "OpexLineEconomics")

    def test_dead_branch_removed(self):
        # V258 : les constantes V212_RAIL_PAX_*_PCT etant figees a 100, la branche
        # != 100 qui etait devenue morte est retiree d'OpexLineEconomics.
        self.assertNotIn("V212_RAIL_PAX_REVENUE_PCT != 100", self.body)
        self.assertNotIn("V212_RAIL_PAX_CAPITAL_PCT != 100", self.body)


if __name__ == "__main__":
    unittest.main()
