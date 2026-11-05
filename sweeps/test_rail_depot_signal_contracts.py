"""RAIL-DEPOT-SIGNAL default-OFF exact projection and physical safety contracts."""

import unittest
from pathlib import Path

from rail_depot_signal_legacy import FIXTURE, off_source, off_sha256
from test_rail_search_prio_20261103 import off_config_bytes
from test_rail_search_prio_source_off import off_search_prio_source

AI = Path(__file__).resolve().parents[1] / "ai/OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class RailDepotSignalContracts(unittest.TestCase):
    def test_flag_at_zero_and_once_read(self):
        info = source("info.nut")
        setting = info.split('name = "rail_depot_signal"', 1)[1].split('flags = AICONFIG_BOOLEAN', 1)[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{difficulty}_value = 0", setting)
        self.assertIn("RAIL_DEPOT_SIGNAL <- false;", source("globals_pre.nut"))
        self.assertEqual(source("settings.nut").count('GetSetting("rail_depot_signal")'), 1)
        self.assertIn('require("rail_depot_signal.nut");', source("main.nut"))

    def test_exact_pre_intervention_historical_sha(self):
        for name, expected in FIXTURE["baseline_sha256"].items():
            with self.subTest(name=name):
                source_off = off_search_prio_source(name, source(name))
                if name in ("info.nut", "globals_pre.nut", "settings.nut"):
                    source_off = off_config_bytes(name, source_off.encode("utf-8")).decode("utf-8")
                self.assertEqual(off_sha256(name, source_off), expected)
                original = off_source(name, source_off)
                self.assertEqual(off_source(name, original), original)

    def test_strict_partial_hunk_rejection(self):
        for name, edits in FIXTURE["files"].items():
            with self.subTest(name=name):
                text = source(name).replace(edits[0]["new"], " /*broken*/ ", 1)
                with self.assertRaises(AssertionError):
                    off_source(name, text)

    def test_guarded_path_and_rollback_preserved(self):
        builder = source("builder_rail.nut")
        self.assertEqual(builder.count('RAIL_DEPOT_SIGNAL ? OpexRailDepotSignalBuildPrimary'), 5)
        self.assertIn(': OpexBuildDepot(tiles);', builder)
        self.assertIn(': OpexBuildDepot(tiles, forbiddenDepot1);', builder)
        self.assertIn(': OpexBuildDepot(tiles2, prep.forbidden);', builder)
        self.assertEqual(builder.count('result.depotSignal <- OpexRailDepotSignalEnhance('), 2)
        self.assertEqual(builder.count('result.depotEndB <- result.depotSignal.depotB;'), 2)
        self.assertIn('OpexRailDepotSignalRollbackTracked(depot)) depot = null;', builder)
        self.assertIn('delete RAIL_DEPOT_SIGNAL_SPURS[depot];', source('rail_depot_signal.nut'))
        self.assertIn('depot, newSignals, true, reverseBuilt, builtTrack);', source('rail_depot_signal.nut'))
        self.assertIn('AIRail.BuildRail(after, junction, branch[0]);', source('rail_depot_signal.nut'))
        self.assertIn('AIRail.AreTilesConnected(after, junction, branch[0])', source('rail_depot_signal.nut'))
        self.assertIn('"phase=primary"', source('rail_depot_signal.nut'))

    def test_depot_is_branch_and_not_in_station_throat(self):
        module = source("rail_depot_signal.nut")
        self.assertIn('function OpexRailDepotSignalTrySpur(', module)
        self.assertIn('function OpexRailDepotSignalRollbackSpur(', module)
        self.assertIn('2 * l + 3', module)
        self.assertIn('local clear = l + 2;', module)
        self.assertIn('local spurSignal = branch[l];', module)
        self.assertIn('local spurFront = branch[l + 1];', module)
        self.assertIn('for (local offset = 0; offset <= 100; offset++)', module)
        self.assertNotIn('for (local offset = 0; offset <= 12; offset++)', module)
        self.assertIn('local depot = OpexRailDepotSignalBuildNear(tiles, false, null, extraForbidden, trainTiles);', module)
        self.assertIn('return depot;', module)
        self.assertNotIn('return depot != null ? depot : OpexBuildDepot(', module)
        self.assertIn('if (depot != null && AIRail.IsRailDepotTile(depot)) AITile.DemolishTile(depot);', module)

    def test_join_signals_pbs_only_no_oneway_on_shared_track(self):
        module = source("rail_depot_signal.nut")
        self.assertIn('OpexC41BuildPbsAtApproach(platform)', module)
        self.assertIn('OpexC41BuildPbsAtApproach(platform, a ? line.stationA : line.stationB)', module)
        self.assertIn('AIRail.BuildSignal(tile, toward, AIRail.SIGNALTYPE_PBS)', module)
        self.assertNotIn('SIGNALTYPE_PBS_ONEWAY', module)
        self.assertNotIn('SIGNALTYPE_NORMAL', module)
        self.assertIn('OpexTileTrackCount(tile) != 1', module)

    def test_depot_b_protects_independent_and_existing_rail(self):
        module = source("rail_depot_signal.nut")
        self.assertIn('AIRail.IsRailTile(tile) || AIRail.IsRailStationTile(tile)', module)
        self.assertIn('!AITile.IsBuildable(tile)', module)
        self.assertIn('foreach (tile in tiles2) forbiddenB[tile] <- true;', module)
        self.assertIn('foreach (tile in tiles) forbiddenB2[tile] <- true;', module)
        self.assertIn('OpexRailDepotSignalBuildNear(tiles, true, depot, forbiddenB, trainTiles)', module)
        self.assertIn('OpexRailDepotSignalBuildNear(tiles2, true, depot2, forbiddenB2, trainTiles)', module)

    def test_pbs_on_all_three_incoming_tracks_not_after_junction(self):
        module = source("rail_depot_signal.nut")
        self.assertIn('local approach = [index - clear, index + clear];', module)
        self.assertIn('AIRail.BuildSignal(spurSignal, spurFront, AIRail.SIGNALTYPE_PBS)', module)
        self.assertIn('AIRail.BuildSignal(tiles[at], tiles[at - step], AIRail.SIGNALTYPE_PBS)', module)
        self.assertIn('local spurFront = branch[l + 1];', module)
        self.assertNotIn('AIRail.BuildSignal(tiles[at], tiles[at + step], AIRail.SIGNALTYPE_PBS)', module)
        self.assertIn('AIRail.GetSignalType(tiles[at], tiles[at + step])', module)
        self.assertIn('AIRail.GetSignalType(tiles[k], tiles[k + step])', module)
        self.assertIn('AIRail.RemoveSignal(placedSignals[s].tile, placedSignals[s].front)', module)
        builder = source('builder_rail.nut')
        self.assertIn('local signals = RAIL_DEPOT_SIGNAL && OpexRailDepotSignalSpurRoutingCertified()\n      ? { ok = 3, fail = 0, skip = 0, junc = 1, failures = [] }', builder)
        self.assertIn(': OpexPlaceJoinSignals(planA2, planB2, tiles2, depot2);', builder)

    def test_rds_failure_falls_back_to_historical_depot(self):
        module = source('rail_depot_signal.nut')
        primary = module.split('function OpexRailDepotSignalBuildPrimary(', 1)[1].split(
            'function OpexRailDepotSignalPathDistance(', 1)[0]
        self.assertIn('local depot = OpexRailDepotSignalBuildNear(', primary)
        self.assertIn('if (depot == null) {', primary)
        self.assertIn('depot = OpexBuildDepot(tiles, extraForbidden);', primary)
        self.assertIn('"phase=legacy_fallback"', primary)
        self.assertIn('"LEGACY_DEPFAIL"', primary)
        self.assertLess(primary.index('OpexRailDepotSignalBuildNear('),
                        primary.index('OpexBuildDepot(tiles, extraForbidden)'))

    def test_uncertified_pbs_spurs_fail_closed_without_harming_legacy(self):
        module = source('rail_depot_signal.nut')
        guard = module.split('function OpexRailDepotSignalSpurRoutingCertified()', 1)[1].split('}', 1)[0]
        self.assertIn('return false;', guard)
        near = module.split('function OpexRailDepotSignalBuildNear(', 1)[1].split(
            'function OpexRailDepotSignalBuildPrimary(', 1)[0]
        self.assertIn('if (!OpexRailDepotSignalSpurRoutingCertified()) return null;', near)
        enhance = module.split('function OpexRailDepotSignalEnhance(', 1)[1].split(
            'function OpexRailDepotSignalProtectExisting(', 1)[0]
        self.assertIn('if (!OpexRailDepotSignalSpurRoutingCertified())', enhance)
        self.assertIn('depotB = null, depotB2 = null', enhance)
        existing = module.split('function OpexRailDepotSignalProtectExisting(', 1)[1]
        self.assertIn('if (!OpexRailDepotSignalSpurRoutingCertified()) return acc;', existing)

    def test_intermediate_roughly_every_hundred_and_actual_length(self):
        module = source("rail_depot_signal.nut")
        self.assertIn('local gap = 100;', module)
        self.assertIn('local routeDist = OpexRailDepotSignalRouteLength(tiles);', module)
        self.assertIn('local sections = (routeDist + gap - 1) / gap;', module)
        self.assertIn('OpexRailDepotSignalIndexForDistance(tiles, (routeDist * section) / sections)', module)
        self.assertIn('OpexRailDepotSignalTrySpur(tiles, i, trainTiles, forbiddenB)', module)
        self.assertIn('OpexRailDepotSignalTrySpur(tiles2, i, trainTiles, forbiddenB2)', module)
        builder = source('builder_rail.nut')
        self.assertIn('OpexRailDepotSignalBuildPrimary(tiles, null, candidate.platformLength)', builder)
        self.assertIn('OpexRailDepotSignalBuildPrimary(tiles2, prep.forbidden, line.platformLength)', builder)
        self.assertIn('"phase=coverage"', module)
        self.assertIn('"phase=intermediate_skip"', module)
        self.assertIn('" mid_targets=" + targets', module)

    def test_record_actual_breakdowns_and_servicing_without_changing_game_settings(self):
        module = source("rail_depot_signal.nut")
        for setting in ('difficulty.vehicle_breakdowns', 'vehicle.servint_trains',
                        'vehicle.servint_ispercent'):
            self.assertIn(f'AIGameSettings.IsValid("{setting}")', module)
            self.assertIn(f'AIGameSettings.GetValue("{setting}")', module)
        self.assertIn('"phase=config breakdowns="', module)
        self.assertNotIn('AIGameSettings.SetValue', module)

    def test_cost_and_new_line_persistence(self):
        builder = source("builder_rail.nut")
        self.assertLess(builder.index('result.depotSignal <- OpexRailDepotSignalEnhance('),
                        builder.index('result.actualCost = primaryCost + doubleCost + postPathCosts.GetCosts();'))
        task = source("task_rail.nut")
        self.assertIn('builtLine.depotEndB <- result.depotEndB;', task)
        self.assertIn('builtLine.depotEndB2 <- result.depotEndB2;', task)
        self.assertIn('line.rawset("depotEndB2", upgrade.depotEndB2)', task)
        self.assertIn('OpexDecide("RAIL_DEPOT_SIGNAL", "phase=build line="', task)
        self.assertIn('"phase=upgrade line="', builder)


if __name__ == "__main__":
    unittest.main()
