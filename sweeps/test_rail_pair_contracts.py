"""RAIL-PAIR: source isolation, physical safety, recovery and strict OFF projection."""
from pathlib import Path
import unittest

from rail_pair_legacy import CHUNKS, REPLACEMENTS, off_source

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class RailPairContracts(unittest.TestCase):
    def test_setting_default_zero_and_single_read(self):
        info = source("info.nut")
        setting = CHUNKS["info.nut"]
        self.assertEqual(info.count(setting), 1)
        self.assertIn('name = "rail_pair"', setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 0", setting)
        self.assertEqual(source("settings.nut").count('GetSetting("rail_pair")'), 1)
        self.assertIn("RAIL_PAIR <- 0;", source("globals_pre.nut"))

    def test_no_historical_bytes_change_after_projection(self):
        for name, fragments in CHUNKS.items():
            with self.subTest(name=name):
                original = source(name)
                projection = off_source(name, original)
                self.assertEqual(off_source(name, projection), projection)
                if isinstance(fragments, str):
                    fragments = [fragments]
                for fragment in fragments:
                    self.assertEqual(original.count(fragment), 1)
                    self.assertNotIn(fragment, projection)
        for name, edits in REPLACEMENTS.items():
            original = source(name)
            projected = off_source(name, original)
            for new, old in edits:
                self.assertEqual(original.count(new), 1)
                self.assertIn(old, projected)
                self.assertNotIn(new, projected)

    def test_incomplete_projection_is_rejected(self):
        for name, fragments in CHUNKS.items():
            if isinstance(fragments, str):
                fragments = [fragments]
            if len(fragments) < 2:
                continue
            with self.subTest(name=name):
                changed = source(name).replace(fragments[0], "", 1)
                with self.assertRaises(AssertionError):
                    off_source(name, changed)

    def test_isolated_single_track_freight_and_recoverable_transaction(self):
        task = source("task_rail_pair.nut")
        geometry = source("rail_pair_geometry.nut")
        self.assertIn('line.kind != "freight"', task)
        self.assertIn('line.trains != 1 || line.vehicles.len() != 1', task)
        self.assertIn('"doubleTrack" in line', task)
        self.assertIn('"shared_station_or_depot"', task)
        self.assertIn("OpexV271IsolatedRoute(line)", task)
        self.assertIn("OpexV271RestoreTracks(state.snapshots)", task)
        self.assertIn("state.phase = \"rollback\"", task)
        self.assertIn("SIGNALTYPE_PBS", task)
        self.assertIn("state.destLead", task)
        self.assertIn("OpexV271RouteIssue", geometry)
        self.assertIn("OpexV271TraceTrackTiles", geometry)
        self.assertIn('saveObj.railPair', source("persist.nut"))
        self.assertIn('"railPair" in data', source("persist.nut"))

    def test_full_load_and_vehicle_slot(self):
        task = source("task_rail_pair.nut")
        self.assertIn("OpexRailVehicleSlotAvailable()", task)
        self.assertIn("AIOrder.OF_FULL_LOAD_ANY", task)
        self.assertIn("AIVehicle.CloneVehicle", task)
        self.assertNotIn("OpexCashReserve()", task)

    def test_route_cannot_accept_a_partial_trace_or_a_cycle(self):
        geometry = source("rail_pair_geometry.nut")
        self.assertIn("OpexV284Trace(", geometry)
        self.assertIn("route[route.len() - 1] != endStationTile", geometry)
        self.assertIn("line.platformB.station_exit", geometry)
        self.assertIn("OpexV271TraceJoinedDestination(", geometry)
        self.assertIn("if (next != null) { V271_LAST_TRACE_ISSUE = \"junction\"; return null; }", geometry)
        self.assertIn("AIStation.GetStationID(tile) == targetId", geometry)
        self.assertIn("V271_LAST_TRACE_ISSUE = \"structure_axis_entry\"", geometry)
        self.assertIn("AIRail.IsRailStationTile(next)", geometry)
        self.assertIn('OpexDecide("RAIL_PAIR_TRACE"', source("task_rail_pair.nut"))
        self.assertIn("if (AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile)) continue;", geometry)
        self.assertIn('V271_LAST_GEOMETRY_ISSUE = "front_structure_before_signal"', geometry)
        self.assertNotIn("if (cur in visited) break", geometry)

    def test_stage_rechecks_exclusivity_and_protects_signals(self):
        task = source("task_rail_pair.nut")
        self.assertGreaterEqual(task.count("OpexRailPairStationsFree(this, line)"), 3)
        self.assertIn("state.signalBefore <- [", task)
        self.assertIn("snapshot.original == AIRail.SIGNALTYPE_NONE", task)
        self.assertIn("OpexV271MatchesClone(state, state.newVehicle)", task)
        self.assertIn('"clone_invalid_at_commit"', task)
        self.assertIn('"depot_order_invalid"', task)

    def test_shared_source_station_allows_depot_with_distinct_tracks(self):
        task = source("task_rail_pair.nut")
        free = task.split("function OpexRailPairStationsFree(owner, line)", 1)[1].split(
            "function OpexRailPairFreightOrders", 1
        )[0]
        self.assertIn('OpexLineStationId(other, "B") == a', free)
        self.assertIn('OpexLineStationId(other, "A") == b', free)
        self.assertIn('OpexLineStationId(other, "B") == b', free)
        self.assertIn('other.depot == line.depot', free)
        self.assertIn('other.depot2 == line.depot', free)
        self.assertIn('local otherA = OpexLineStationId(other, "A")', free)
        # Only a depot shared with an unrelated source is excluded. A sibling
        # from this same A may use the depot if the next checks isolate tracks.
        self.assertLess(free.index('if (otherA != a) {'), free.index('other.depot == line.depot'))
        self.assertLess(free.index('continue;', free.index('if (otherA != a) {')),
                        free.index('if (!("platformA" in other)'))
        self.assertIn('own.lead == sibling.lead', free)
        self.assertIn('own.station_exit == sibling.station_exit', free)
        self.assertIn('tile == sibling.anchor + j * sibling.step', free)
        self.assertNotIn('OpexLineStationId(other, "A") == a ||', free)

    def test_station_stock_counts_all_rail_trains_and_near_miss_is_observable(self):
        task = source("task_rail_pair.nut")
        self.assertIn("AIVehicleList_Station(station)", task)
        self.assertIn("AIVehicle.GetCapacity(vehicle, cargo)", task)
        self.assertIn("local threshold = max(capacity, fleet.capacity)", task)
        self.assertIn("waiting < threshold && rating >= 60", task)
        self.assertIn('"lastWaitingA" in line', task)
        self.assertIn('" station_trains="', task)
        self.assertIn('" station_capacity="', task)
        self.assertIn('" threshold="', task)
        self.assertIn('" fill_pct="', task)
        self.assertIn('state.fillPct <- (100 * near.waiting / max(1, near.threshold))', task)

    def test_rollback_does_not_claim_ambiguous_or_unverified_clone(self):
        task = source("task_rail_pair.nut")
        self.assertIn("function OpexV271MatchesClone(state, vehicle)", task)
        self.assertIn("AIOrder.GetOrderDestination(vehicle, i)", task)
        self.assertIn("AIOrder.GetOrderFlags(vehicle, i)", task)
        self.assertIn("if (found >= 0) return -2", task)
        self.assertIn('"clone_recovery_ambiguous"', task)
        self.assertIn('snapshot.added', source("rail_pair_geometry.nut"))
        self.assertIn('state.stationBefore', task)
        self.assertIn("OpexWaterContains(line.vehicles, vehicle)", task)
        self.assertIn("AIVehicle.IsStoppedInDepot(state.newVehicle)", task)
        self.assertIn('AIVehicle.GetWagonEngineType(vehicle, wagon)', task)
        self.assertIn('AIVehicle.GetWagonEngineType(state.vehicle, wagon)', task)
        self.assertIn('!OpexWaterContains(state.before, state.newVehicle)', task)
        self.assertIn('OpexWaterContains(state.before, state.newVehicle)', task)
        rollback = task.split('if (state.phase == "rollback") {', 1)[1].split(
            'if (state.phase == "dispatch")', 1
        )[0]
        self.assertLess(rollback.index("OpexV271MatchesClone"), rollback.index("AIVehicle.SellVehicle"))
        self.assertLess(rollback.index("AIVehicle.IsStoppedInDepot"), rollback.index("AIVehicle.SellVehicle"))


if __name__ == "__main__":
    unittest.main()
