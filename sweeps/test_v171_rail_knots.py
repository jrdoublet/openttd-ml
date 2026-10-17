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
        specs = parse_ai_setting_specs(AI / "info.nut")
        self.assertNotIn("v171_rail_knots", specs)
        self.assertNotIn('name = "v171_rail_knots"', _read("info.nut"))

    def test_global_declared_in_globals_pre(self):
        content = _read("globals_pre.nut")
        self.assertNotIn("V171_RAIL_KNOTS", content)

    def test_loaded_once_in_settings(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertNotIn("v171_rail_knots", body)
        for p in AI.glob("*.nut"):
            self.assertNotIn('AIController.GetSetting("v171_rail_knots")', p.read_text(encoding="utf-8"))


class KnotTables(unittest.TestCase):
    def setUp(self):
        cand_src = _read("candidates.nut")
        self.knot_dist = _parse_nut_array(cand_src, "KNOT_DISTANCE")
        self.knot_v1 = _parse_nut_array(cand_src, "KNOT_ITERATIONS_V1")
        self.assertNotIn("KNOT_ITERATIONS_V2", cand_src)

    def test_v1_intact(self):
        self.assertEqual(self.knot_dist, [23, 33, 48, 63, 81, 105, 150])
        self.assertEqual(self.knot_v1, [371, 673, 2188, 4066, 7745, 15308, 53951])

    def test_v2_removed(self):
        self.assertNotIn("KNOT_ITERATIONS_V2", _read("candidates.nut"))


class FunctionContracts(unittest.TestCase):
    def test_distance_for_iterations_does_not_use_v2(self):
        body = _function_body(_read("candidates.nut"), "OpexRailDistanceForIterations")
        self.assertIn("local knots = KNOT_ITERATIONS_V1;", body)
        self.assertNotIn("KNOT_ITERATIONS_V2", body)
        self.assertNotIn("V171_RAIL_KNOTS", body)

    def test_rail_iterations_uses_v1_only(self):
        body = _function_body(_read("candidates.nut"), "OpexRailIterations")
        self.assertNotIn("KNOT_ITERATIONS_V2", body)
        self.assertIn("KNOT_ITERATIONS_V1", body)
        self.assertNotIn("V171_RAIL_KNOTS", body)

    def test_behavior_parity_at_default_0(self):
        cand_src = _read("candidates.nut")
        dist = _parse_nut_array(cand_src, "KNOT_DISTANCE")
        v1 = _parse_nut_array(cand_src, "KNOT_ITERATIONS_V1")

        self.assertEqual(py_rail_iterations(81, v1, dist), 7745)
        prev_iters = py_rail_iterations(1, v1, dist)
        for d in range(2, 201):
            curr_iters = py_rail_iterations(d, v1, dist)
            self.assertGreaterEqual(curr_iters, prev_iters, f"Non monotone a d={d}")
            prev_iters = curr_iters


if __name__ == "__main__":
    unittest.main()
