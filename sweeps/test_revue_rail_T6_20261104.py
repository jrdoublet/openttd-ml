"""Revue rail T6 (construction, dépôt, rollback, signaux) — 04/11/2026.

Correctif F1 (sans condition) dans OpexRollback : seule NOTRE voie est défaite.
Avant, toute case du tracé prévu était rasée (DemolishTile), y compris une case
jamais posée après un échec (arbres, champ, route) et la route d'un passage à
niveau. Tests de source uniquement : le Squirrel ne se compile pas ici.
"""

import re
import sys
import unittest
from pathlib import Path

SWEEPS = Path(__file__).resolve().parent
sys.path.insert(0, str(SWEEPS))

from revue_rail_t6_off import MARKERS, REPLACED, off_source  # noqa: E402
from test_rail_loop_20261104 import function_body, read, strip_squirrel  # noqa: E402


class RollbackOnlyOurRail(unittest.TestCase):
    def setUp(self):
        body = strip_squirrel(function_body(read("builder_rail.nut"), "OpexRollback"))
        self.loop = body[body.index("if (tiles == null) return;"):]

    def test_level_crossing_loses_rail_not_road(self):
        crossing = self.loop.index("if (AIRail.IsLevelCrossingTile(t)) {")
        remove = self.loop.index("AIRail.RemoveRailTrack(t, AIRail.GetRailTracks(t));")
        demolish = self.loop.index("AITile.DemolishTile(t);")
        self.assertLess(crossing, remove)
        self.assertLess(remove, demolish)
        self.assertIn("continue;", self.loop[remove:demolish])

    def test_only_owned_rail_tiles_are_demolished(self):
        guard = self.loop.index("if (!AITile.HasTransportType(t, AITile.TRANSPORT_RAIL)")
        self.assertIn("|| !AICompany.IsMine(AITile.GetOwner(t))) continue;", self.loop)
        self.assertLess(guard, self.loop.index("AITile.DemolishTile(t);"))
        self.assertEqual(self.loop.count("DemolishTile"), 1)
        self.assertNotIn("DemolishTile(tiles[i])", self.loop)

    def test_endpoints_and_station_handling_unchanged(self):
        body = function_body(read("builder_rail.nut"), "OpexRollback")
        self.assertIn("for (local i = 1; i < tiles.len() - 1; i++) {", body)
        self.assertIn("AIRail.RemoveRailStationTileRectangle(t, t, false);", body)
        self.assertIn("if (depot != null) AITile.DemolishTile(depot);", body)

    def test_hunk_has_no_closure_or_reserved_word(self):
        hunk = strip_squirrel(REPLACED["builder_rail.nut"][0][0])
        self.assertIsNone(re.search(r"\b(clone|base)\b", hunk))
        self.assertIsNone(re.search(r"function\s*\(", hunk))


class T6FindingsDocumented(unittest.TestCase):
    def test_t6_02_depot_front_may_be_a_curve(self):
        depot = function_body(read("builder_rail.nut"), "OpexBuildDepot")
        self.assertIn("for (local index = 1; index < tiles.len() - 1; index++) {", depot)
        self.assertNotIn("anchor - stationSide != lineSide - anchor", depot)
        loop = read("rail_loop.nut")
        self.assertIn('front - route[k - 1] != route[k + 1] - front) return "depot_front_curve";', loop)

    def test_t6_03_primary_single_track_has_no_signals(self):
        callers = re.findall(r"OpexPlaceJoinSignals\(", strip_squirrel(read("builder_rail.nut")))
        # définition + appel unique (upgrade)
        self.assertEqual(len(callers), 2)

    def test_depot_probe_is_shielded(self):
        depot = function_body(read("builder_rail.nut"), "OpexBuildDepot")
        self.assertLess(depot.index("local shield = AIAccounting();"), depot.index("local testMode = AITestMode();"))


class RevueT6OffProjection(unittest.TestCase):
    def test_projection_restores_historic_loop_and_is_idempotent(self):
        source = read("builder_rail.nut")
        projected = off_source("builder_rail.nut", source)
        self.assertIn(REPLACED["builder_rail.nut"][0][1], projected)
        for marker in MARKERS:
            self.assertNotIn(marker, projected)
        self.assertEqual(off_source("builder_rail.nut", projected), projected)

    def test_other_modules_unchanged(self):
        for name in ("task_rail.nut", "rail_loop.nut", "orchestrator.nut"):
            with self.subTest(name=name):
                self.assertEqual(off_source(name, read(name)), read(name))

    def test_partial_or_duplicated_hunk_fails_closed(self):
        source = read("builder_rail.nut")
        with self.assertRaises(AssertionError):
            off_source("builder_rail.nut", source.replace("AIRail.RemoveRailTrack(t, AIRail.GetRailTracks(t));",
                                                          "AIRail.RemoveRailTrack(t, 0);"))
        with self.assertRaises(AssertionError):
            off_source("builder_rail.nut", source + REPLACED["builder_rail.nut"][0][0])

    def test_chain_head_strips_t6_first(self):
        chain = (SWEEPS / "invest_stall_diagnostic_off.py").read_text(encoding="utf8")
        self.assertLess(chain.index("revue_rail_t6_off"), chain.index("rail_keep_off"))


if __name__ == "__main__":
    unittest.main()
