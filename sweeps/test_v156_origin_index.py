#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test V156: equivalence of diamond spatial index and DistanceManhattan < ORIGIN_SEPARATION.

Verifies that for map origins (including corner and edge cases), the diamond of
radius (ORIGIN_SEPARATION - 1) produces identical results to Manhattan distance < ORIGIN_SEPARATION
for all tiles within the map bounds.
"""

import random
import unittest

ORIGIN_SEPARATION = 3
RADIUS = ORIGIN_SEPARATION - 1  # 2


def build_diamond_index(origins, map_w, map_h, radius=RADIUS):
    served = set()
    for ox, oy in origins:
        for dx in range(-radius, radius + 1):
            x = ox + dx
            if x < 0 or x >= map_w:
                continue
            dy_limit = radius - abs(dx)
            for dy in range(-dy_limit, dy_limit + 1):
                y = oy + dy
                if y < 0 or y >= map_h:
                    continue
                served.add((x, y))
    return served


def is_served_manhattan(tile, origins, separation=ORIGIN_SEPARATION):
    tx, ty = tile
    for ox, oy in origins:
        if abs(tx - ox) + abs(ty - oy) < separation:
            return True
    return False


class TestV156OriginDiamondIndex(unittest.TestCase):

    def check_map(self, map_w, map_h, origins):
        index = build_diamond_index(origins, map_w, map_h)

        # 1. Every tile in the index must satisfy Manhattan distance < ORIGIN_SEPARATION
        for tx, ty in index:
            self.assertTrue(0 <= tx < map_w, f"Tile x={tx} out of bounds [0, {map_w})")
            self.assertTrue(0 <= ty < map_h, f"Tile y={ty} out of bounds [0, {map_h})")
            self.assertTrue(
                is_served_manhattan((tx, ty), origins),
                f"Tile ({tx}, {ty}) in index but Manhattan distance >= {ORIGIN_SEPARATION}",
            )

        # 2. Check all tiles in bounding boxes around all origins
        for ox, oy in origins:
            for dx in range(-ORIGIN_SEPARATION - 2, ORIGIN_SEPARATION + 3):
                tx = ox + dx
                if tx < 0 or tx >= map_w:
                    continue
                for dy in range(-ORIGIN_SEPARATION - 2, ORIGIN_SEPARATION + 3):
                    ty = oy + dy
                    if ty < 0 or ty >= map_h:
                        continue
                    in_index = (tx, ty) in index
                    expected = is_served_manhattan((tx, ty), origins)
                    self.assertEqual(
                        in_index,
                        expected,
                        f"Mismatch at ({tx}, {ty}) for origin ({ox}, {oy}): index={in_index}, expected={expected}",
                    )

    def test_corners(self):
        map_w, map_h = 64, 64
        corners = [
            (0, 0),
            (map_w - 1, 0),
            (0, map_h - 1),
            (map_w - 1, map_h - 1),
        ]
        for corner in corners:
            self.check_map(map_w, map_h, [corner])
        self.check_map(map_w, map_h, corners)

    def test_edges(self):
        map_w, map_h = 128, 64
        edges = [
            (0, 10),
            (1, 10),
            (map_w - 1, 20),
            (map_w - 2, 20),
            (30, 0),
            (30, 1),
            (40, map_h - 1),
            (40, map_h - 2),
        ]
        for edge in edges:
            self.check_map(map_w, map_h, [edge])
        self.check_map(map_w, map_h, edges)

    def test_full_small_map_exhaustively(self):
        map_w, map_h = 16, 16
        origins = [(2, 3), (0, 0), (15, 15), (7, 8), (15, 0)]
        index = build_diamond_index(origins, map_w, map_h)
        for x in range(map_w):
            for y in range(map_h):
                in_index = (x, y) in index
                expected = is_served_manhattan((x, y), origins)
                self.assertEqual(in_index, expected, f"Mismatch at ({x}, {y})")

    def test_random_maps_and_origins(self):
        rng = random.Random(42)
        for _ in range(20):
            map_w = rng.randint(32, 256)
            map_h = rng.randint(32, 256)
            num_origins = rng.randint(1, 30)
            origins = [(rng.randint(0, map_w - 1), rng.randint(0, map_h - 1)) for _ in range(num_origins)]
            self.check_map(map_w, map_h, origins)


class TestV156Contracts(unittest.TestCase):
    """Verifies settings, globals, and Squirrel implementations for V156."""

    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        cls.root = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"

    def read(self, name):
        return (self.root / name).read_text(encoding="utf-8")

    def test_setting_and_global_defaults(self):
        info = self.read("info.nut")
        self.assertIn('name = "incr_revalidate_index",', info)
        block = info.split('name = "incr_revalidate_index",', 1)[1].split("});", 1)[0]
        self.assertIn("min_value = 0, max_value = 2,", block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"\b{level}_value\s*=\s*0\b")

        globals_pre = self.read("globals_pre.nut")
        self.assertIn("INCR_REVALIDATE_INDEX <- 0;", globals_pre)

        settings = self.read("settings.nut")
        self.assertIn('INCR_REVALIDATE_INDEX = AIController.GetSetting("incr_revalidate_index");', settings)

    def test_functions_exist_and_signatures(self):
        gen = self.read("projects_generation.nut")
        self.assertIn("function OpexIncrRevalidateIndexContext(lines)", gen)
        self.assertIn("function OpexCandidateStillValidIndexed(p, lines, abandonedPairs, ctx)", gen)
        self.assertIn("function OpexIncrementalCandidateStillValid(p, lines, abandonedPairs = null, ctx = null)", gen)

        task_air = self.read("task_air.nut")
        self.assertIn("function OpexAirTownServedIndexed(town, lines, ctx)", task_air)
        self.assertIn("function OpexAirBatchHubHasCapacityIndexed(anchor, plane, ctx)", task_air)
        self.assertIn("function OpexAirSiteStillBuildableIndexed(site, airport, plane, reuse, ctx)", task_air)
        self.assertIn("function OpexAirBatchPlanStillLiveIndexed(plan, lines, ctx)", task_air)

    def test_projects_update_orchestration(self):
        upd = self.read("projects_update.nut")
        self.assertIn("local ctx = (INCR_REVALIDATE_INDEX != 0) ? OpexIncrRevalidateIndexContext(lines) : null;", upd)
        self.assertIn("if (INCR_REVALIDATE_INDEX == 1) {", upd)
        self.assertIn("isValid = OpexCandidateStillValidIndexed(p, lines, abandonedPairs, ctx);", upd)
        self.assertIn("} else if (INCR_REVALIDATE_INDEX == 2) {", upd)
        self.assertIn("INCR_INDEX_MISMATCH", upd)
        self.assertIn("INCR_INDEX_CHECK", upd)
        self.assertIn("OpexFilterAirAlternativesStillValid(alternatives, abandonedPairs, lines, extValidity, extTownLim);", upd)


if __name__ == "__main__":
    unittest.main()

