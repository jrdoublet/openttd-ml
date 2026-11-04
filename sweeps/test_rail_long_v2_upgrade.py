"""Contrats hors moteur de la transaction de quais RAIL-LONG v2.

Ces tests ne simulent pas OpenTTD : ils verrouillent les gardes les plus
risquees avant le smoke reel (dont Save/Load est un essai distinct).
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "ai" / "OpexAI" / "task_rail_long_v2.nut").read_text(
    encoding="utf-8"
)


def body(symbol):
    start = SOURCE.index("function " + symbol + "(")
    brace = SOURCE.index("{", start)
    depth = 0
    for end in range(brace, len(SOURCE)):
        if SOURCE[end] == "{":
            depth += 1
        elif SOURCE[end] == "}":
            depth -= 1
            if depth == 0:
                return SOURCE[start : end + 1]
    raise AssertionError(f"Unterminated Squirrel function: {symbol}")


def platform_extension(width, height, anchor_xy, step_xy, length, exit_at,
                       target):
    """Reference geometry for boundary cases, independently of tile indices."""
    if target < length:
        return None
    dx, dy = step_xy
    ax, ay = anchor_xy
    if abs(dx) + abs(dy) != 1 or exit_at not in ("first", "last"):
        return None
    old = [(ax + i * dx, ay + i * dy) for i in range(length)]
    if any(x < 0 or x >= width or y < 0 or y >= height for x, y in old):
        return None
    before = old[-1] if exit_at == "first" else old[0]
    sign = 1 if exit_at == "first" else -1
    new = [
        (before[0] + sign * dx * i, before[1] + sign * dy * i)
        for i in range(1, target - length + 1)
    ]
    if any(x < 0 or x >= width or y < 0 or y >= height for x, y in new):
        return None
    return new, old[0] if exit_at == "first" else (new[-1] if new else old[0])


class RailLongV2GeometryContracts(unittest.TestCase):
    def test_the_two_backwards_directions_have_distinct_new_anchors(self):
        self.assertEqual(
            platform_extension(256, 256, (10, 20), (1, 0), 3, "first", 7),
            ([(13, 20), (14, 20), (15, 20), (16, 20)], (10, 20)),
        )
        self.assertEqual(
            platform_extension(256, 256, (10, 20), (1, 0), 3, "last", 7),
            ([(9, 20), (8, 20), (7, 20), (6, 20)], (6, 20)),
        )
        plan = body("OpexRailLongV2ExtendPlan")
        self.assertIn("plan.station_exit != plan.anchor && plan.station_exit != last", plan)
        self.assertIn("AIMap.DistanceManhattan(previous, tile) != 1", plan)
        anchor = body("OpexRailLongV2NewAnchor")
        self.assertIn("part.target.anchor == part.original.anchor", anchor)
        self.assertIn("part.tiles[part.tiles.len() - 1]", anchor)

    def test_map_edges_and_existing_station_tiles_are_protected(self):
        self.assertIsNone(
            platform_extension(256, 256, (254, 12), (1, 0), 2, "first", 7)
        )
        self.assertIsNone(
            platform_extension(256, 256, (0, 12), (1, 0), 3, "last", 7)
        )
        source = body("OpexRailLongV2ExtendPlan")
        for guard in (
            "AIMap.IsValidTile(tile)",
            "AIRail.IsRailStationTile(tile)",
            "AIStation.GetStationID(tile) != stationId",
            "!AICompany.IsMine(AITile.GetOwner(tile))",
            "!AITile.IsBuildable(tile)",
            "AITile.SLOPE_FLAT",
        ):
            self.assertIn(guard, source)

    def test_restricted_single_train_nonshared_freight_line(self):
        source = body("OpexRailLongV2LineSafe")
        for required in (
            'line.mode != "rail"',
            'line.kind != "freight"',
            "line.trains != 1",
            "line.vehicles.len() != 1",
            "line.wagons2 > 0",
            "line.doubleTrack != 0",
            "line.v190Directional",
            "line.v190Independent",
            "line.v271Tandem",
            "stationA == stationB",
            "foreach (other in owner._lines)",
        ):
            self.assertIn(required, source)


class RailLongV2TransactionContracts(unittest.TestCase):
    def test_no_vehicle_orders_or_rail_track_mutations(self):
        # The module can inspect vehicles but may only build/remove stations.
        prohibited = (
            "AIVehicle.SendVehicleToDepot", "AIVehicle.StartStopVehicle",
            "AIVehicle.SellVehicle", "AIVehicle.BuildVehicle",
            "AIVehicle.CloneVehicle", "AIOrder.", "AIRail.BuildRail(",
            "AIRail.RemoveRailTrack(", "AIRail.BuildSignal(",
            "AIRail.RemoveSignal(", "AIRail.RemoveRailStation(",
        )
        for call in prohibited:
            with self.subTest(call=call):
                self.assertNotIn(call, SOURCE)
        build = body("OpexRailLongV2BuildPart")
        self.assertIn("AIRail.BuildRailStation(", build)
        self.assertIn("OpexRailLongV2StationBuilt(tiles, stationId)", build)
        self.assertIn("OpexRailLongV2StationFree(tiles)", build)
        self.assertIn("OpexRailLongV2NoVehicleNear(tiles)", build)

    def test_only_intended_owned_and_unoccupied_tiles_can_be_removed(self):
        rollback = body("OpexRailLongV2RollbackPart")
        guards = (
            "if (!intent) return true",
            "before.len() != tiles.len()",
            "foreach (entry in before) if (entry) return false",
            "AIStation.GetStationID(tile) != stationId",
            "!AICompany.IsMine(AITile.GetOwner(tile))",
            "!OpexRailLongV2NoVehicleNear(tiles)",
            "AIRail.RemoveRailStationTileRectangle(tile, tile, false)",
        )
        for guard in guards:
            self.assertIn(guard, rollback)
        self.assertLess(
            rollback.index("!OpexRailLongV2NoVehicleNear(tiles)"),
            rollback.index("AIRail.RemoveRailStationTileRectangle("),
        )
        bounded = body("OpexRailLongV2NoVehicleNear")
        self.assertIn("checked > RAIL_LONG_V2_VEHICLE_SCAN_LIMIT", bounded)
        self.assertIn("AIVehicle.GetLength(vehicle)", bounded)
        self.assertIn("AIMap.DistanceManhattan(locoTile, tile) <= reach", bounded)

    def test_command_intents_precede_physical_build_and_rollback(self):
        step = body("OpexRailLongV2Step")
        self.assertLess(step.index('state.phase = "intent_a"'),
                        step.index('state.phase == "intent_a"'))
        self.assertLess(step.index('state.intentA = true'),
                        step.index('OpexRailLongV2BuildPart(state, "A")'))
        self.assertLess(step.index('state.intentB = true'),
                        step.index('OpexRailLongV2BuildPart(state, "B")'))
        self.assertLess(step.index('state.phase == "rollback"'),
                        step.index('state.phase == "commit"'))
        self.assertLess(step.index('OpexRailLongV2CommitReady(owner, line, state)'),
                        step.index("line.platformLength = state.targetLength"))
        self.assertIn('state.phase = "rollback"', body("OpexRailLongV2Cancel"))
        # An interrupted BuildRailStation is recognized by examining live tiles.
        self.assertLess(
            body("OpexRailLongV2BuildPart").index("OpexRailLongV2StationBuilt(tiles"),
            body("OpexRailLongV2BuildPart").index("AIRail.BuildRailStation("),
        )

    def test_no_commit_after_partial_build_or_changed_line(self):
        step = body("OpexRailLongV2Step")
        commit = step[step.index('if (state.phase == "commit")') :]
        safe = body("OpexRailLongV2CommitReady")
        for contract in (
            "line == null", "line.platformA.anchor != state.oldA.anchor",
            "line.platformB.length != state.oldB.length",
            "AIStation.GetStationID(line.stationA) != state.stationAId",
            "OpexRailLongV2StationBuilt(state.tilesA",
            "OpexRailLongV2StationBuilt(state.tilesB",
        ):
            # The guard may compare whole plans instead of individual fields.
            if "line.platformA.anchor" in contract:
                self.assertIn("OpexRailLongV2PlanMatches(line.platformA", safe)
            elif "line.platformB.length" in contract:
                self.assertIn("OpexRailLongV2PlanMatches(line.platformB", safe)
            else:
                self.assertIn(contract, safe)
        self.assertIn("owner._saveProjection = null", commit)
        self.assertIn("owner._v257Cache = null", commit)
        self.assertIn("if (!OpexRailLongV2CommitReady(owner, line, state))", commit)
        self.assertLess(
            commit.index("OpexRailLongV2CommitReady(owner, line, state)"),
            commit.index("line.platformA = clone state.targetA"),
        )

    def test_partial_metadata_commit_is_resumed_idempotently(self):
        safe = body("OpexRailLongV2CommitReady")
        step = body("OpexRailLongV2Step")
        for part in ("A", "B"):
            self.assertIn(
                f"OpexRailLongV2PlanMatches(line.platform{part}, state.old{part})",
                safe,
            )
            self.assertIn(
                f"OpexRailLongV2PlanMatches(line.platform{part}, state.target{part})",
                safe,
            )
        self.assertIn("line.platformLength != state.targetLength", safe)
        self.assertIn('if (OpexRailLongV2CommitReady(owner, line, state)) state.phase = "commit";',
                      step)
        self.assertLess(
            step.index('if (OpexRailLongV2CommitReady(owner, line, state))'),
            step.index('if (state.phase == "rollback")'),
        )

    def test_save_load_reconcile_is_mode_independent_for_pending_transaction(self):
        select = body("OpexRailLongV2Select")
        reconcile = body("OpexRailLongV2Reconcile")
        self.assertIn("!RAIL_LONG_V2 || !SAVE_FULL_STATE", select)
        self.assertIn("owner._railLongV2Pending != null", select)
        self.assertIn('(investStall ? !INVEST_STALL : !RAIL_LONG_V2) && state.phase != "rollback"', reconcile)
        self.assertIn('state.phase = "commit"', reconcile)
        self.assertIn('state.phase = "rollback"', reconcile)
        self.assertIn("typeof state != \"table\"", reconcile)
        self.assertIn("typeof state.tilesA != \"array\"", reconcile)
        self.assertIn('typeof plan[key] != "integer"', reconcile)
        self.assertIn('typeof state.intentA != "bool"', reconcile)
        self.assertIn("owner._saveProjection = null", reconcile)
        step = body("OpexRailLongV2Step")
        self.assertNotIn('if (!RAIL_LONG_V2) return', step)
        self.assertIn("owner._railLongV2Pending = null", step)

    def test_selection_and_retries_are_bounded(self):
        for name in (
            "RAIL_LONG_V2_SCAN_LIMIT", "RAIL_LONG_V2_VEHICLE_SCAN_LIMIT",
            "RAIL_LONG_V2_RETRY_LIMIT", "RAIL_LONG_V2_RETRY_DAYS",
        ):
            self.assertRegex(SOURCE, rf"const {name} = [0-9]+;")
        select = body("OpexRailLongV2Select")
        self.assertIn("min(count, RAIL_LONG_V2_SCAN_LIMIT)", select)
        self.assertIn("RAIL_LONG_V2_CURSOR = (RAIL_LONG_V2_CURSOR + scans) % count", select)
        self.assertIn("OpexAvailableCapital() < quote * 1.10 + 50000", select)
        step = body("OpexRailLongV2Step")
        self.assertIn("state.rollbackAttempts >= RAIL_LONG_V2_RETRY_LIMIT", step)
        self.assertIn("now < state.lastRollbackDay + 15", step)
        self.assertIn('OpexRailLongV2TransactionLog(state, "orphan_safe"', step)

    def test_squirrel_syntax_traps(self):
        self.assertNotRegex(SOURCE, r"\.find\s*\(")
        self.assertNotRegex(SOURCE, r"\bfunction\s*\(")
        self.assertNotRegex(SOURCE, r"\blocal\s+(?:clone|base|parent|resume|static)\b")
        for assignment in re.findall(r"(?m)^\s*const\s+\w+\s*=\s*([^;]+);", SOURCE):
            self.assertRegex(assignment.strip(), r"^\d+$")
        self.assertEqual(SOURCE.count("{"), SOURCE.count("}"))


if __name__ == "__main__":
    unittest.main()
