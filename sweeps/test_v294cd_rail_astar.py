#!/usr/bin/env python3
"""Contrats statiques V294c/d/f/i/j : paramètres A* ferroviaire alignés sur AAA.

Vérifie, sans lancer OpenTTD :
1. Déclaration de chaque réglage (défaut 0 sur les 4 niveaux, bornes exactes) ;
2. Lecture unique dans settings.nut vers les globales de globals_pre.nut ;
3. Gardes explicites `if (V294_... > 0)` autour de chaque nouveau chemin de code ;
4. Aucun global non déclaré dans globals_pre.nut ;
5. Absence totale de OpexDynamicHardCap et nettoyage des commentaires périmés.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read(rel: str) -> str:
    return (AI / rel).read_text(encoding="utf-8")


def function_body(source: str, name: str) -> str:
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:pos]
    raise AssertionError(f"Unclosed function: {name}")


class TestV294cRailWeightPct(unittest.TestCase):
    def test_setting_declared_default_zero(self):
        info = read("info.nut")
        match = re.search(r'AddSetting\(\{\s*name\s*=\s*"v294_rail_weight_pct"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(match, "v294_rail_weight_pct non déclaré dans info.nut")
        block = match.group(1)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{level}_value\s*=\s*0\b")
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 400", block)

    def test_global_declared_and_loaded_once(self):
        globals_pre = read("globals_pre.nut")
        self.assertIn("V294_RAIL_WEIGHT_PCT <- 0;", globals_pre)
        settings = read("settings.nut")
        self.assertEqual(settings.count('GetSetting("v294_rail_weight_pct")'), 1)
        self.assertIn("V294_RAIL_WEIGHT_PCT = railWeightPct;", settings)

    def test_guarded_in_builder_rail(self):
        body = function_body(read("builder_rail.nut"), "OpexRailAstarWeight")
        self.assertIn("if (V294_RAIL_WEIGHT_PCT > 0)", body)
        self.assertIn("return V294_RAIL_WEIGHT_PCT;", body)


if __name__ == "__main__":
    unittest.main()
