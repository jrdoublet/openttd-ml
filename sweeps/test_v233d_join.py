"""V233d source contracts. No engine, compilation or economic qualification."""
import unittest

from test_v233b_exposure import body
from test_v233_contracts import AI


class V233dContracts(unittest.TestCase):
    def test_prefilter_failure_reaches_persisted_abandonment(self):
        generate = body('goods_v233.nut', 'function OpexAI::_v233GraftStep(')
        failure = generate.split('if (sites.reason != "OK")', 1)[1].split(
            'if (!this._v233CandidateLive(candidate)', 1)[0]
        self.assertIn('("sourceFailed" in sites) && sites.sourceFailed', failure)
        plans = body('goods_v233.nut', 'function OpexV233PlatformPlans(')
        self.assertIn('sourceFailed = !sawA', plans)
        self.assertIn('_markPairAbandoned(OpexV233SourceSiteKey(candidate, candidate.cargo))', failure)
        self.assertIn('gen.current = null;', failure)
        self.assertIn('_markPairAbandoned(OpexAbandonedPairKey(candidate))', failure)
        self.assertIn('OpexV233SourceSiteKey(state.context, state.row.cargo) in this._abandonedPairs', generate)
        live = body('goods_v233.nut', 'function OpexAI::_v233CandidateLive(')
        self.assertIn('V233_GOODS_POLICY == 2 && OpexV233SourceSiteKey', live)
        save = body('persist.nut', 'function OpexAI::Save(')
        self.assertIn('abandonedPairs = abandoned', save)

    def test_source_key_is_shared_across_towns_but_changes_with_platform(self):
        key = body('goods_v233.nut', 'function OpexV233SourceSiteKey(')
        for field in ('context.v233FactoryId', 'cargo', 'context.joinStationId',
                      'p.anchor', 'p.direction', 'p.length'):
            self.assertIn(field, key)
        self.assertNotIn('dstTown', key)
        self.assertNotIn('revision', key)
        self.assertIn('"v233_siteA|"', key)

    def test_join_all_lengths_before_new_station_fallback(self):
        plans = body('goods_v233.nut', 'function OpexV233PlatformPlans(')
        self.assertLess(plans.index('foreach (joinB in [true, false])'),
                        plans.index('for (local length = wanted;'))
        self.assertIn('if (!sawA) break;', plans)
        self.assertIn('joinB ? OpexV233JoinedTownPlans(', plans)
        self.assertIn(': OpexV233TownPlans(candidate.dst', plans)
        self.assertIn('candidate.v233JoinB <- joinB ? plansB[0].stationId : -1', plans)
        dispatch = body('builder_rail.nut', 'function OpexRailPlatformPlans(')
        self.assertIn('V233_GOODS_GRAFT && (V233_GOODS_POLICY == 2 || V233_GOODS_POLICY == 3) && OpexV233IsGraft(candidate)', dispatch)

    def test_multimodal_station_must_be_ours_accepting_and_in_destination_town(self):
        finder = body('goods_v233.nut', 'function OpexV233JoinedTownPlans(')
        for token in ('AIStationList(AIStation.STATION_ANY)',
                      'station == candidate.joinStationId',
                      'AIStation.GetNearestTown(station) != candidate.dstTown',
                      'OpexV233AcceptingStation(station, tile, candidate.cargo)'):
            self.assertIn(token, finder)
        check = body('goods_v233.nut', 'function OpexV233AcceptingStation(')
        for token in ('AIStation.IsValidStation', 'AIStation.GetStationID(tile) != station',
                      'AICompany.IsMine', 'AICargoList_StationAccepting(station).HasItem(cargo)'):
            self.assertIn(token, check)

    def test_new_platform_join_uses_native_command_and_game_spread(self):
        finder = body('goods_v233.nut', 'function OpexV233TownPlans(')
        for token in ('AIGameSettings.GetValue("station.station_spread") - 1',
                      'AITile.IsBuildable(tile)', 'SLOPE_FLAT', 'AITestMode()', 'AIAccounting()',
                      'AIRail.BuildRailStation(anchor, axis[0], 1, length, stationId)',
                      'p.stationId <- stationId', 'p.v233StationTile <- center',
                      '!joining && acceptance < 8'):
            self.assertIn(token, finder)

    def test_join_identity_and_acceptance_revalidated_in_stock_and_before_spend(self):
        validate = body('task_rail.nut', 'function OpexV131PlatformCargoOk(')
        for token in ('p.stationId != candidate.v233JoinB', '"v233StationTile" in p',
                      'OpexV233AcceptingStation(p.stationId, p.v233StationTile, candidate.cargo)',
                      'OpexV233TownAcceptance(p, candidate.cargo, coverage) >= 8'):
            self.assertIn(token, validate)
        for signature in ('function OpexV233SpendAllowed(', 'function OpexAI::_v233PlanStep('):
            self.assertIn('OpexV131PlatformCargoOk(plan.planB', body('goods_v233.nut', signature))

    def test_both_stations_all_facilities_protected_and_only_new_platforms_built(self):
        guard = body('goods_v233.nut', 'function OpexV233SpendAllowed(')
        for token in ('V233_GOODS_POLICY == 2', 'foreach (p in [plan.planA, plan.planB])',
                      'AITileList_StationType(p.stationId, AIStation.STATION_ANY)',
                      'protectedTiles[tile] <- true', 'OpexV233NewPlatform(p)',
                      'p.v233Protected <- protectedTiles', 'tile in protectedTiles'):
            self.assertIn(token, guard)
        rollback = body('builder_rail.nut', 'function OpexRollback(')
        self.assertIn('!(depot in v233Protected)', rollback)
        secondary = body('builder_rail.nut', 'function OpexV190RollbackDoubleTrack(')
        self.assertIn('planA1.v233Protected', secondary)

    def test_separation_exempts_only_selected_destination_station(self):
        generate = body('goods_v233.nut', 'function OpexAI::_v233GraftStep(')
        self.assertIn('V233_GOODS_POLICY != 2 && OpexOriginService', generate)
        separation = body('lines.nut', 'function OpexAI::_tooClose(')
        self.assertIn('v233Join && (V233_GOODS_POLICY == 2 || V233_GOODS_POLICY == 3)', separation)
        self.assertEqual(separation.count('entry[0] == "B" && graftDestStation >= 0'), 2)
        self.assertIn('OpexLineStationId(line, lineEnd) == graftDestStation', separation)
        self.assertIn('stationId == graftDestStation', separation)
        self.assertIn('OpexRememberClosest(d, MIN_SEPARATION', separation)

    def test_shared_line_identity_survives_flags_off_and_scrap_is_vehicle_only(self):
        record = body('task_rail.nut', 'function OpexAI::_tryBuildRailProject(')
        self.assertIn('line.v233SharedStationBId <- candidate.v233JoinB', record)
        self.assertIn('this._saveProjection = null', record)
        codec = body('persist.nut', 'function OpexSaveProjectLine(')
        self.assertIn('local serializableLine = clone line', codec)
        self.assertNotIn('v233SharedStationBId', (AI / 'globals_pre.nut').read_text())
        vehicles = body('lines.nut', 'function OpexLineVehicleIds(')
        self.assertNotIn('V233_GOODS_POLICY', vehicles)
        self.assertNotIn('V233_GOODS_GRAFT', vehicles)
        self.assertIn('"v233SharedStationBId" in line', vehicles)
        self.assertIn('other == stationId) other = OpexLineStationId(line, "A")', vehicles)
        self.assertIn('OpexVehicleServesStation(v, other)', vehicles)
        scrap = body('task_report.nut', 'function OpexAI::_scrapDeadLines(')
        self.assertNotIn('DemolishTile', scrap)
        self.assertNotIn('RemoveRailStation', scrap)

    def test_destination_choice_logged_only_under_decision_log(self):
        plans = body('goods_v233.nut', 'function OpexV233PlatformPlans(')
        self.assertIn('if (DECISION_LOG) OpexDecide("V233_SITE"', plans)
        self.assertIn('" joinB=" + candidate.v233JoinB : " newB"', plans)


if __name__ == '__main__':
    unittest.main()
