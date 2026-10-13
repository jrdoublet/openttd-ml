#!/usr/bin/env python3
"""Tests pour V168 — borne de distance des candidats rail.

Constat du 13/10 (banc rail contre rail V166, `v166_rail_vs_rail_10x3_20261013`) : la borne
`railMax` vaut 94 tuiles parce qu'elle est derivee du plafond d'A* (10k x 1,2) par une table de
noeuds ancienne (7 745 iterations predites a 81 tuiles ; 2 204 mesurees en mediane a 80-94),
alors qu'AAAHogEx pose ses lignes rail a 117 tuiles medianes.

Contrats statiques :
1. `v168_rail_max_dist` declare (entier 0..512, defaut 160 depuis les portes A et B du 13/10) et lu
   une fois dans OpexLoadSettings.
2. A 0, chemin historique : la borne derivee de la table et les deux filtres d'iterations
   predites restent en place.
3. Hors defaut, la valeur remplace la borne dans les deux fonctions de bornes, et les deux
   filtres d'iterations predites (candidat et chaine marchandises) sont leves ; la borne de
   carte (`mapSpan`) s'applique toujours apres.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_setting_specs  # noqa: E402


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("unterminated " + name)


class Declaration(unittest.TestCase):
    def test_setting(self):
        spec = parse_ai_setting_specs(AI / "info.nut")["v168_rail_max_dist"]
        self.assertEqual(spec["default"], 160)
        self.assertFalse(spec["boolean"])
        self.assertEqual((spec["min_value"], spec["max_value"]), (0, 512))
        block = _read("info.nut").split('name = "v168_rail_max_dist"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 160\b")

    def test_loaded_once(self):
        self.assertIn("V168_RAIL_MAX_DIST <- 160;", _read("globals_pre.nut"))
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertEqual(body.count('AIController.GetSetting("v168_rail_max_dist")'), 1)
        self.assertIn("if (V168_RAIL_MAX_DIST < 0) V168_RAIL_MAX_DIST = 0;", body)


class Bounds(unittest.TestCase):
    def test_epoch_bounds_override_before_map_clamp(self):
        body = _function_body(_read("candidates.nut"), "OpexRefreshEpochBounds")
        derived = body.index("local railMax = OpexRailDistanceForIterations(iterCap);")
        override = body.index("if (V168_RAIL_MAX_DIST > 0) railMax = V168_RAIL_MAX_DIST;")
        clamp = body.index("if (railMax > mapSpan) railMax = mapSpan;")
        self.assertLess(derived, override)
        self.assertLess(override, clamp)
        # la borne route ne peut pas depasser la borne rail : l'ordre est conserve
        self.assertLess(override, body.index("if (roadGenMax > railMax) roadGenMax = railMax;"))

    def test_fallback_bounds_override(self):
        body = _function_body(_read("candidates.nut"), "OpexCatalogBounds")
        derived = body.index("local railMax = OpexRailDistanceForIterations((HARD_ITERATION_CAP * 12) / 10);")
        override = body.index("if (V168_RAIL_MAX_DIST > 0) railMax = V168_RAIL_MAX_DIST;")
        self.assertLess(derived, override)
        self.assertLess(override, body.index("return {"))


class IterationFilters(unittest.TestCase):
    def test_candidate_filter_kept_at_default(self):
        body = _function_body(_read("candidates.nut"), "OpexMakeCandidate")
        self.assertIn("if (V168_RAIL_MAX_DIST <= 0 && iterations > (HARD_ITERATION_CAP * 12) / 10) {", body)
        # la borne de distance reste testee avant le filtre d'iterations
        self.assertLess(body.index("if (distance > bounds.railMax) {"),
                        body.index("if (V168_RAIL_MAX_DIST <= 0 && iterations >"))

    def test_goods_chain_filter_kept_at_default(self):
        source = _read("candidates.nut")
        self.assertIn("if (goodsDist > bounds.railMax) continue;", source)
        self.assertIn("if (V168_RAIL_MAX_DIST <= 0 && itersGoods > (HARD_ITERATION_CAP * 12) / 10) continue;",
                      source)

    def test_no_other_predicted_iteration_filter(self):
        # tout filtre par iterations predites contre le plafond doit etre gouverne par V168
        for path in AI.glob("*.nut"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if "(HARD_ITERATION_CAP * 12) / 10" in line and (" > " in line or ">" in line.split("(HARD")[0]):
                    if "OpexRailDistanceForIterations" in line or "local iterCap" in line:
                        continue
                    self.assertIn("V168_RAIL_MAX_DIST <= 0", line, (path.name, line.strip()))

    def test_opcode_estimate_still_capped(self):
        # le score d'opcodes borne deja les iterations predites au plafond dur (C21)
        body = _function_body(_read("projects_builders.nut"), "OpexProjectFromCandidate")
        self.assertIn("if (iters > HARD_ITERATION_CAP) iters = HARD_ITERATION_CAP;", body)


if __name__ == "__main__":
    unittest.main()
