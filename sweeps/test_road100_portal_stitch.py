"""ROAD100-35 portal-stitch: source-level contracts and seed42 budget arithmetic.

This module does not simulate OpenTTD road topology, AI opcodes, or money.
Those are deliberately left for the paired engine smoke and LongVerifyTrace.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "ai" / "OpexAI" / "road100_sparse_corridor.nut").read_text(
    encoding="utf-8"
)
PORTAL = "function OpexRoad100PortalUsable(" + SOURCE.split(
    "function OpexRoad100PortalUsable(", 1
)[-1]


def body(name: str) -> str:
    """The new helpers are top-level, independently named Squirrel functions."""
    match = re.search(rf"(?m)^function {re.escape(name)}\(", SOURCE)
    if match is None:
        raise AssertionError(f"Missing new function {name}")
    later = SOURCE.find("\nfunction ", match.end())
    return SOURCE[match.start() : later if later != -1 else len(SOURCE)]


class PortalStitchContracts(unittest.TestCase):
    def test_autonomous_entrypoint_and_unmodified_v33_contract(self):
        old, added = SOURCE.split("function OpexRoad100PortalUsable(", 1)
        for signature in (
            "function OpexRoad100SparseGap(",
            "function OpexRoad100SparseAnchor(",
            "function OpexRoad100SparseTrial(",
            "function OpexRoad100SparseTestTrace(",
            "function OpexRoad100SparseCorridorTrace(",
        ):
            self.assertIn(signature, old)
        self.assertNotIn("function OpexRoad100PortalStitchTrace(", old)
        self.assertIn("function OpexRoad100PortalStitchTrace(", added)
        entry = body("OpexRoad100PortalStitchTrace")
        for contract in (
            "OpexRoad100PortalSleeve(siteA, siteB,",
            "OpexRoad100PortalSleeve(siteB, siteA,",
            "OpexRoad100PortalBand(current, target,",
            "trace = null", "reason =", "reason_detail =", "ops = 0",
            "stats =", "out.trace = trace;",
        ):
            self.assertIn(contract, entry)
        for forbidden in (
            "OpexRoad100SparseGap(", "OpexRoad100SparseTrial(",
            "OpexRoad100SparseAnchor(", "OpexRoad100SparseTestTrace(",
            "OpexRoad100SparseCorridorTrace(",
        ):
            self.assertNotIn(forbidden, PORTAL)

    def test_true_drive_through_fronts_are_bidirectionally_connected(self):
        entry = body("OpexRoad100PortalStitchTrace")
        self.assertIn("AIMap.DistanceManhattan(siteA.tile, siteA.front) != 1", entry)
        self.assertIn("AIMap.DistanceManhattan(siteB.tile, siteB.front) != 1", entry)
        for old, new in (
            ("siteA.tile", "siteA.front"),
            ("siteA.front", "siteA.tile"),
            ("siteB.tile", "siteB.front"),
            ("siteB.front", "siteB.tile"),
        ):
            self.assertIn(f"AreRoadTilesConnected({old}, {new})", entry)
        self.assertIn('out.reason = "FRONT_ESCAPE"', entry)
        self.assertIn('out.reason_detail = "DT_FRONT_LINK"', entry)
        self.assertIn("local path = [siteA.tile];", entry)
        self.assertIn("path.append(siteB.tile);", entry)

    def test_bfs_only_existing_bidirectional_streets_and_three_portals(self):
        sleeve = body("OpexRoad100PortalSleeve")
        for fragment in (
            "out.expanded < 16", "node.depth >= 9",
            "out.portals.len() < 3", "AIRoad.IsRoadTile(tile)",
            "AIRoad.AreRoadTilesConnected(node.tile, tile)",
            "AIRoad.AreRoadTilesConnected(tile, node.tile)",
            "chosenBranches.rawset", "prevIndex = currentIndex",
            "out.reason = \"OPCAP\"",
            "tile = start, tiles = [start]",
        ):
            self.assertIn(fragment, sleeve)
        self.assertNotIn("BuildRoad(", sleeve)
        self.assertNotIn("AITestMode(", sleeve)

    def test_bands_are_cardinal_bounded_and_preserve_real_links(self):
        entry = body("OpexRoad100PortalStitchTrace")
        leg = body("OpexRoad100PortalBand")
        for fragment in (
            "if (bands > 12)", "mode < 3",
            "pairIndex < pairChoices.len()", "if (pairChoices.len() < 3",
            "local offset = mode == 0 ? 0 : mode == 1 ? 2 : -2;",
            "out.stats.first_reject", "out.reason_detail = \"BAND_\"",
        ):
            self.assertIn(fragment, entry)
        for fragment in (
            "length > 24", "candidate.len() + length > 190",
            "AIMap.DistanceManhattan(tile, last) != 1",
            "AIRoad.AreRoadTilesConnected(last, tile)",
            "AIRoad.AreRoadTilesConnected(tile, last)",
            "AITile.GetSlope(last) != AITile.SLOPE_FLAT",
            "tile in occupied", "tile in localSeen",
            'out.reason = "EDGE_OCCUPIED"',
        ):
            self.assertIn(fragment, leg)
        for forbidden in ("Pathfinder.", "OpexRoad100LongObstacleTrace(", "OpexRoad100SegmentedGap("):
            self.assertNotIn(forbidden, PORTAL)

    def test_hard_budget_and_rollback_ownership(self):
        entry = body("OpexRoad100PortalStitchTrace")
        self.assertIn("limitOps > 180000", entry)
        self.assertIn("local ceiling = entry + 42000;", entry)
        self.assertIn("ceiling > limitOps - 66000", entry)
        self.assertIn("OpexOpsMeasureEnd(mark) >= limitOps - 65000", entry)
        self.assertIn("out.ops > 43000", entry)
        self.assertIn("out.trace = null;", entry)
        self.assertIn("out.reason = \"OPCAP\"", entry)
        # No money, vehicles, station or road is built in this module.
        for forbidden in (
            "AIRoad.BuildRoad(", "AIRoad.BuildRoadDepot(",
            "AIRoad.BuildDriveThroughRoadStation(",
            "AIVehicle.Build", "AIOrder.AppendOrder(",
            "GetCargoWaiting(", "AITestMode(",
        ):
            self.assertNotIn(forbidden, PORTAL)

    def test_cycle_endpoint_and_tail_reservation(self):
        entry = body("OpexRoad100PortalStitchTrace")
        for fragment in (
            "foreach (tile in b.tiles) reserved.rawset(tile, true);",
            "foreach (tile, unused in reserved) occupied.rawset(tile, true);",
            "local pathSeen = {};", "if (nextTile in pathSeen)",
            "pathSeen.rawset(current, true);",
            "path.len() - 1 < 80 || path.len() - 1 > 190",
            "path[0] != siteA.tile || path[1] != siteA.front",
            "path[path.len() - 2] != siteB.front",
            "path[n] in seen",
            "AIMap.DistanceManhattan(path[n - 1], path[n]) != 1",
            "trace.append({ from = path[n - 1], to = path[n] });",
        ):
            self.assertIn(fragment, entry)

    def test_seed42_v34_distances_and_opcode_envelopes(self):
        self.assertIn('centres < 80 || centres > 190', body('OpexRoad100PortalStitchTrace'))
        # Demand is V34's *potential* PASS/month (not transported PASS).
        # This router must never treat the raw producer counts as revenue.
        self.assertEqual((355 * 18) // 46 + (327 * 17) // 46, 258)
        self.assertEqual((332 * 17) // 49 + (112 * 13) // 24, 175)
        # Physical front/site tile IDs from frozen V34 engine evidence (256x256).
        for site_a, site_b, expected_bands in (
            (32418, 25381, 10),  # 18 -> 2, center 158
            (60234, 28973, 10),  # 26 -> 10, center 154
        ):
            manhattan = abs(site_a % 256 - site_b % 256) + abs(
                site_a // 256 - site_b // 256
            )
            self.assertEqual((manhattan + 15) // 16, expected_bands)
            self.assertLessEqual(expected_bands, 12)

        # The two 77k scan cases leave only about 35k for the new module.
        for spent, attempt_cap in (
            (77_437, 180_000),
            (76_554 + 3_481, 180_000),
            (116_000, 180_000),
            (77_437, 170_000),
        ):
            ceiling = min(spent + 42_000, attempt_cap - 66_000)
            if ceiling > spent:
                self.assertLessEqual(ceiling - spent, 42_000)
                self.assertLess(ceiling, attempt_cap - 65_000)
            else:
                self.assertLessEqual(ceiling, spent)

    def test_squirrel_source_delimiters_and_reserved_locals(self):
        for opener, closer in (("{", "}"), ("(", ")"), ("[", "]")):
            self.assertEqual(PORTAL.count(opener), PORTAL.count(closer))
        self.assertNotRegex(PORTAL, r"\blocal\s+(?:base|clone|delete|class|function)\b")
        self.assertNotIn(".find(", PORTAL)
        self.assertNotIn("const ", PORTAL)


if __name__ == "__main__":
    unittest.main()
