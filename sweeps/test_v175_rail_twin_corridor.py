#!/usr/bin/env python3
"""Tests statiques et de contrat pour V175 — corridor de recherche seconde voie (twin corridor).

Contrats verifiés sans lancer OpenTTD :
1. Declaration du reglage `v175_rail_twin_corridor` (entier 0..3, defaut 0, flags 0, 4 *_value a 0).
2. Globale V175_RAIL_TWIN_CORRIDOR dans globals_pre.nut et chargement unique borne dans settings.nut.
3. Persistance : trackTiles ignore dans OPEX_SAVE_LINE_SKIP (persist.nut).
4. Pathfinders V90 et V129 : SetCorridor, variable membre _corridor, filtrage dans _Neighbours.
5. Builder rail : OpexGetLineTrackTiles, OpexBuildTwinCorridor, propagation du corridor dans
   OpexCreateRailPathfinder, OpexCreateSegmentedSearch, OpexSearchPath, OpexPrepareUpgradeSearch.
6. Repli (fallback) sur la recherche non-contrainte en cas d'echec dans le couloir (bloquant et resumable).
7. Journalisation : champ corr= present dans RAIL_SEARCH, RAIL_SEARCH_END et RAIL_EXPAND.
8. Simulation algorithmique de la demi-largeur de couloir (BFS 4-connexite).
"""

from __future__ import annotations

import collections
import re
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"

try:
    import openttdlab  # noqa: F401
except ImportError:
    fake_lab = types.ModuleType("openttdlab")
    fake_lab.bananas_ai = mock.MagicMock()
    fake_lab.bananas_ai_library = mock.MagicMock()
    fake_lab.local_folder = mock.MagicMock()
    fake_lab.run_experiments = mock.MagicMock()
    sys.modules["openttdlab"] = fake_lab

sys.path.insert(0, str(ROOT / "sweeps"))
from campaign_freeze import parse_ai_setting_specs  # noqa: E402


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


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


class TestV175Settings(unittest.TestCase):
    def test_setting_declaration(self):
        specs = parse_ai_setting_specs(AI / "info.nut")
        self.assertIn("v175_rail_twin_corridor", specs)
        spec = specs["v175_rail_twin_corridor"]
        self.assertEqual(spec["default"], 0)
        self.assertEqual(spec["min_value"], 0)
        self.assertEqual(spec["max_value"], 3)
        self.assertFalse(spec["boolean"])

        block = _read("ai/OpexAI/info.nut").split('name = "v175_rail_twin_corridor"', 1)[1].split("});", 1)[0]
        self.assertIn("flags = 0", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r"\s*=\s*0\b")

    def test_global_declared_in_globals_pre(self):
        content = _read("ai/OpexAI/globals_pre.nut")
        self.assertIn("V175_RAIL_TWIN_CORRIDOR <- 0;", content)

    def test_loaded_once_in_settings(self):
        body = _function_body(_read("ai/OpexAI/settings.nut"), "OpexLoadSettings")
        self.assertEqual(body.count('AIController.GetSetting("v175_rail_twin_corridor")'), 1)
        self.assertIn("V175_RAIL_TWIN_CORRIDOR = (v175Twin >= 0 && v175Twin <= 3) ? v175Twin : 0;", body)

        for p in AI.glob("*.nut"):
            if p.name == "settings.nut":
                continue
            self.assertNotIn('AIController.GetSetting("v175_rail_twin_corridor")', p.read_text(encoding="utf-8"))

    def test_persist_skip_track_tiles(self):
        content = _read("ai/OpexAI/persist.nut")
        self.assertIn("trackTiles = true", content)


class TestV175Pathfinders(unittest.TestCase):
    def test_v90_pathfinder_corridor(self):
        content = _read("ai/OpexAI/pathfinder_v90/rail.nut")
        self.assertIn("_corridor = null;", content)
        self.assertIn("function OpexRailPathFinderV90::SetCorridor(corridor)", content)
        # Verifie le filtrage dans _Neighbours
        self.assertIn("if (self._corridor != null && !(next_tile in self._corridor)) continue;", content)
        self.assertIn("if (self._corridor != null && !(tile[0] in self._corridor)) continue;", content)

    def test_v129_pathfinder_corridor(self):
        content = _read("ai/OpexAI/pathfinder_v90/v129.nut")
        # OpexRailPathFinderV129 herite de OpexRailPathFinderV90 et surcharge _Neighbours et _TunnelsBridgesInto
        self.assertIn("class OpexRailPathFinderV129 extends OpexRailPathFinderV90", content)
        self.assertIn("if (self._corridor != null && !(next_tile in self._corridor)) continue;", content)
        self.assertIn("if (this._corridor != null && !(target in this._corridor)) continue;", content)
        self.assertIn("if (this._corridor != null && !(other_tunnel_end in this._corridor)) return;", content)


class TestV175BuilderRail(unittest.TestCase):
    def test_corridor_builder_functions_exist(self):
        content = _read("ai/OpexAI/builder_rail.nut")
        self.assertIn("function OpexGetLineTrackTiles(line)", content)
        self.assertIn("function OpexBuildTwinCorridor(line, radius)", content)

    def test_create_pathfinders_accept_corridor(self):
        content = _read("ai/OpexAI/builder_rail.nut")
        self.assertIn("function OpexCreateRailPathfinder(plansA, plansB, ignoredTiles = null, corridor = null)", content)
        self.assertIn("function OpexCreateSegmentedSearch(plansA, plansB, iterationBudget, ignoredTiles = null, corridor = null)", content)
        self.assertIn("function OpexSearchPath(plansA, plansB, iterationBudget, deadlineTick, ignoredTiles = null, corridor = null)", content)
        self.assertIn("pathfinder.SetCorridor(corridor);", content)

    def test_prepare_upgrade_search_corridor(self):
        body = _function_body(_read("ai/OpexAI/builder_rail.nut"), "OpexPrepareUpgradeSearch")
        self.assertIn("if (V175_RAIL_TWIN_CORRIDOR > 0)", body)
        self.assertIn("prep.corridor = OpexBuildTwinCorridor(line, V175_RAIL_TWIN_CORRIDOR);", body)

    def test_blocking_upgrade_fallback(self):
        body = _function_body(_read("ai/OpexAI/builder_rail.nut"), "OpexUpgradeRailLineToDoubleTrack")
        self.assertIn("corrVal = V175_RAIL_TWIN_CORRIDOR;", body)
        self.assertIn('corrVal = "fallback";', body)
        self.assertIn("result.corridorUsed <- corrVal;", body)


class TestV175TaskRail(unittest.TestCase):
    def test_start_rail_upgrade_search_passes_corridor(self):
        body = _function_body(_read("ai/OpexAI/task_rail.nut"), "OpexAI::_startRailUpgradeSearch")
        self.assertIn('local corridor = ("corridor" in prep) ? prep.corridor : null;', body)
        self.assertIn("corridor = (corridor != null) ? V175_RAIL_TWIN_CORRIDOR : 0", body)
        self.assertIn("corridorFallback = false", body)

    def test_continue_rail_search_fallback(self):
        body = _function_body(_read("ai/OpexAI/task_rail.nut"), "OpexAI::_continueRailSearch")
        self.assertIn('if (state.kind == "upgrade")', body)
        self.assertIn('state.corridorFallback <- true;', body)
        self.assertIn('corr=" + state.corridor + "_fail', body)

    def test_logging_contains_corr(self):
        body_search = _function_body(_read("ai/OpexAI/task_rail.nut"), "OpexAI::_continueRailSearch")
        self.assertIn('corr=" + corrTag', body_search)

        body_expand = _function_body(_read("ai/OpexAI/task_rail.nut"), "OpexAI::_consumeRailUpgrade")
        self.assertIn('corr=" + corrVal', body_expand)

        body_expand_lines = _function_body(_read("ai/OpexAI/task_rail.nut"), "OpexAI::_expandRailLines")
        self.assertIn('corr=" + corrVal', body_expand_lines)


class TestCorridorBFSAlgorithm(unittest.TestCase):
    """Simulation Python du BFS OpexBuildTwinCorridor pour valider le calcul de demi-largeur."""

    def _simulate_bfs(self, track_tiles: list[tuple[int, int]], radius: int) -> dict[tuple[int, int], int]:
        corridor: dict[tuple[int, int], int] = {}
        frontier: list[tuple[int, int]] = []
        for t in track_tiles:
            if t not in corridor:
                corridor[t] = 0
                frontier.append(t)

        offsets = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for r in range(1, radius + 1):
            next_frontier = []
            for t in frontier:
                for dx, dy in offsets:
                    nb = (t[0] + dx, t[1] + dy)
                    if nb not in corridor:
                        corridor[nb] = r
                        next_frontier.append(nb)
            frontier = next_frontier
        return corridor

    def test_radius_0_empty_or_inactive(self):
        # A radius 0, corridor = null (inactif)
        self.assertEqual(len(self._simulate_bfs([(5, 5)], 0)), 1)

    def test_radius_1_corridor(self):
        # Une ligne droite de 3 tuiles : (5,5), (5,6), (5,7)
        track = [(5, 5), (5, 6), (5, 7)]
        corr = self._simulate_bfs(track, 1)
        # Chaque tuile de track est a distance 0
        for t in track:
            self.assertEqual(corr[t], 0)
        # (4, 6) et (6, 6) sont adjacents donc a distance 1
        self.assertEqual(corr[(4, 6)], 1)
        self.assertEqual(corr[(6, 6)], 1)
        # (4, 4) est diagonale a (5,5), distance Manhattan = 2, pas dans rayon 1
        self.assertNotIn((4, 4), corr)
        # (5, 9) est a distance 2 du track, pas dans rayon 1
        self.assertNotIn((5, 9), corr)

    def test_radius_2_corridor(self):
        track = [(10, 10)]
        corr = self._simulate_bfs(track, 2)
        # Rayon 2 = losange de Manhattan 2 autour de (10,10)
        # Distance Manhattan <= 2
        for x in range(7, 14):
            for y in range(7, 14):
                manh = abs(x - 10) + abs(y - 10)
                if manh <= 2:
                    self.assertIn((x, y), corr)
                    self.assertEqual(corr[(x, y)], manh)
                else:
                    self.assertNotIn((x, y), corr)


if __name__ == "__main__":
    unittest.main()
