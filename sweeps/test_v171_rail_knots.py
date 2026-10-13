#!/usr/bin/env python3
"""Tests pour V171 — recalibrage de la table de noeuds d'iterations A* rail.

Contrats statiques et comportementaux :
1. Declaration : reglages `v171_rail_knots` (booleen, defaut 0, les 4 *_value egaux a 0).
2. Globale et chargement : V171_RAIL_KNOTS dans globals_pre.nut, lu une seule fois dans
   OpexLoadSettings (settings.nut).
3. Monotonie de V2 : KNOT_ITERATIONS_V2 est constitue d'entiers strictement croissants
   alignes sur KNOT_DISTANCE.
4. V1 intact : KNOT_ITERATIONS_V1 et KNOT_DISTANCE conservent strictement leurs valeurs historiques.
5. Inversion : OpexRailDistanceForIterations ne touche PAS a V2 (garde KNOT_ITERATIONS_V1).
6. Aiguillage : OpexRailIterations utilise V1 quand V171_RAIL_KNOTS == 0, V2 quand != 0.
"""
from __future__ import annotations

import re
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


def _parse_nut_array(source: str, var_name: str) -> list[int]:
    pattern = rf"{var_name}\s*<-\s*\[([^\]]+)\];"
    m = re.search(pattern, source)
    if not m:
        raise ValueError(f"Array {var_name} not found in source")
    items = [int(x.strip()) for x in m.group(1).split(",") if x.strip()]
    return items


def py_rail_iterations(distance: int, knots: list[int], knot_dist: list[int]) -> int:
    n = len(knot_dist)
    if distance <= knot_dist[0]:
        return knots[0]
    for i in range(1, n):
        if distance <= knot_dist[i]:
            d0 = knot_dist[i - 1]
            d1 = knot_dist[i]
            v0 = knots[i - 1]
            v1 = knots[i]
            return v0 + ((v1 - v0) * (distance - d0)) // (d1 - d0)
    dLast = knot_dist[n - 1]
    vLast = knots[n - 1]
    return (vLast * distance * distance) // (dLast * dLast)


class Declaration(unittest.TestCase):
    def test_setting_declaration(self):
        spec = parse_ai_setting_specs(AI / "info.nut")["v171_rail_knots"]
        self.assertEqual(spec["default"], 0)
        self.assertTrue(spec["boolean"])

        block = _read("info.nut").split('name = "v171_rail_knots"', 1)[1].split("});", 1)[0]
        self.assertIn("AICONFIG_BOOLEAN", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r"\s*=\s*0\b")

    def test_global_declared_in_globals_pre(self):
        content = _read("globals_pre.nut")
        self.assertIn("V171_RAIL_KNOTS <- 0;", content)

    def test_loaded_once_in_settings(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertEqual(body.count('AIController.GetSetting("v171_rail_knots")'), 1)
        # Aucune autre lecture dans tout le repertoire ai/
        for p in AI.glob("*.nut"):
            if p.name == "settings.nut":
                continue
            self.assertNotIn('AIController.GetSetting("v171_rail_knots")', p.read_text(encoding="utf-8"))


class KnotTables(unittest.TestCase):
    def setUp(self):
        cand_src = _read("candidates.nut")
        self.knot_dist = _parse_nut_array(cand_src, "KNOT_DISTANCE")
        self.knot_v1 = _parse_nut_array(cand_src, "KNOT_ITERATIONS_V1")
        self.knot_v2 = _parse_nut_array(cand_src, "KNOT_ITERATIONS_V2")

    def test_v1_intact(self):
        self.assertEqual(self.knot_dist, [23, 33, 48, 63, 81, 105, 150])
        self.assertEqual(self.knot_v1, [371, 673, 2188, 4066, 7745, 15308, 53951])

    def test_v2_integers_and_monotonic(self):
        self.assertEqual(len(self.knot_v2), len(self.knot_dist))
        for val in self.knot_v2:
            self.assertIsInstance(val, int)
            self.assertGreater(val, 0)
        # Strictement monotone croissante
        for i in range(1, len(self.knot_v2)):
            self.assertGreater(
                self.knot_v2[i],
                self.knot_v2[i - 1],
                f"KNOT_ITERATIONS_V2 non croissant a index {i}: {self.knot_v2[i]} <= {self.knot_v2[i-1]}"
            )

    def test_v2_values_match_measurement(self):
        # Verification des valeurs mesurees
        self.assertEqual(self.knot_v2, [365, 2342, 2652, 4123, 4516, 5977, 7825])


class FunctionContracts(unittest.TestCase):
    def test_distance_for_iterations_does_not_use_v2(self):
        body = _function_body(_read("candidates.nut"), "OpexRailDistanceForIterations")
        self.assertIn("local knots = KNOT_ITERATIONS_V1;", body)
        self.assertNotIn("KNOT_ITERATIONS_V2", body)
        self.assertNotIn("V171_RAIL_KNOTS", body)

    def test_rail_iterations_uses_v2_conditionally(self):
        body = _function_body(_read("candidates.nut"), "OpexRailIterations")
        self.assertIn("KNOT_ITERATIONS_V2", body)
        self.assertIn("KNOT_ITERATIONS_V1", body)
        self.assertIn("V171_RAIL_KNOTS", body)

    def test_behavior_parity_at_default_0(self):
        cand_src = _read("candidates.nut")
        dist = _parse_nut_array(cand_src, "KNOT_DISTANCE")
        v1 = _parse_nut_array(cand_src, "KNOT_ITERATIONS_V1")
        v2 = _parse_nut_array(cand_src, "KNOT_ITERATIONS_V2")

        # Au defaut (V1), a 81 tuiles on a 7 745
        self.assertEqual(py_rail_iterations(81, v1, dist), 7745)
        # Sous V2, a 81 tuiles on a 4 516 (baisse de ~42 % par rapport a V1)
        self.assertEqual(py_rail_iterations(81, v2, dist), 4516)

        # Monotonie de la fonction d'interpolation sous V2 pour toutes les distances de 1 a 200
        prev_iters = py_rail_iterations(1, v2, dist)
        for d in range(2, 201):
            curr_iters = py_rail_iterations(d, v2, dist)
            self.assertGreaterEqual(curr_iters, prev_iters, f"Non monotone a d={d}")
            prev_iters = curr_iters


if __name__ == "__main__":
    unittest.main()
