"""V262 : sentinelles statiques, sans moteur ; limites détaillées dans l'audit §6.

Un test vert ne prouve que le contrat nommé, pas l'absence universelle du défaut.
Les expectedFailure décrivent des lacunes concrètes ; aucun seuil nouveau imposé.
"""
import json
import re
import unittest
from collections import Counter

from test_v261_forum_behaviours import ROOT, all_code, body, source, uncomment


class TipsyfoxBehaviours(unittest.TestCase):
    def test_cpu_each_valuate_site_is_reviewed(self):
        expected = json.loads((ROOT / 'sweeps/fixtures/v262_valuate_inventory.json').read_text())
        found = []
        for name, code in all_code().items():
            for m in re.finditer(r'(\w+)\.Valuate\s*\(([^()]*)\)', code):
                found.append((name, m[1], re.sub(r'\s+', '', m[2])))
        self.assertEqual(Counter(found), Counter(tuple(row) for row in expected))

    def test_cpu_fleet_valuators_are_native_and_single_pass(self):
        for name, fn in [('capital.nut', 'OpexCashReserve'),
                         ('tension.nut', 'OpexTensionFleetScan')]:
            code = body(name, fn)
            self.assertIn('local vehicles = AIVehicleList();', code)
            self.assertEqual(code.count('Valuate(AIVehicle.GetRunningCost)'), 1)
            self.assertIn('vehicles.GetValue(v)', code)

    def test_cpu_air_ring_removes_interior_before_valuate(self):
        code = body('air_sites.nut', 'OpexAirFindSiteRing')
        self.assertLess(code.index('tiles.RemoveRectangle('), code.index('tiles.Valuate('))
        self.assertIn('r <= AIR_SITE_RADIUS', body('air_sites.nut', 'OpexAirFindSiteListed'))

    def test_pathfinding_has_failure_bounds_not_busy_wait(self):
        self.assertIn('if (n > maxNodes) return null;', body('builder_road.nut', 'OpexRoadBfsPath'))
        self.assertIn('head < WATER_BFS_MAX_NODES', body('builder_water.nut', 'OpexWaterFindConnection'))
        self.assertIn('FindPath(PATH_CHUNK)', body('builder_rail.nut', 'OpexAdvanceRailPathfinder'))

    def test_save_projection_is_outside_save_and_reused(self):
        projection = body('persist.nut', 'OpexAI::_refreshSaveProjection')
        self.assertIn('month == this._saveProjectionMonth', projection)
        self.assertIn('OpexSaveProjectLine(line)', projection)
        self.assertIn('projectedLines.append(cache[line])', body('persist.nut', 'OpexAI::Save'))

    @unittest.expectedFailure  # Save reste O(abandons + lignes + nouvelles projections), §6.3.
    def test_save_payload_preparation_has_no_state_sized_loop(self):
        self.assertNotRegex(body('persist.nut', 'OpexAI::Save'), r'\bforeach\s*\(')

    def test_load_reconciles_objects_and_discards_missing_vehicles(self):
        code = body('persist.nut', 'OpexAI::_reconcileAfterLoad')
        for token in ['AIMap.IsValidTile(line.stationA)', 'AIStation.IsValidStation(stationA)',
                      'AICompany.IsMine(AITile.GetOwner(line.stationA))',
                      'if (AIVehicle.IsValidVehicle(vehicle)) liveVehicles.append(vehicle);',
                      'this._lines = liveLines;', 'this._pendingLines = null;']:
            self.assertIn(token, code)

    def test_town_founded_refreshes_catalog_with_validity_guard(self):
        code = body('event_handlers.nut', 'OpexAI::_onTownFounded')
        self.assertLess(code.index('AITown.IsValidTown(townId)'), code.index('AITown.GetPopulation(townId)'))
        self.assertIn('this._catalog._refreshTowns()', code)
        self.assertIn('AIEvent.ET_TOWN_FOUNDED', uncomment(source('events.nut')))

    def test_industry_closed_invalidates_and_subsidy_locations_revalidate(self):
        self.assertIn('this._markDirty("industry_close"', body('event_handlers.nut', 'OpexAI::_onIndustryClose'))
        code = uncomment(source('candidates.nut'))
        for end in ['src', 'dst']:
            self.assertIn(f'if (!AIIndustry.IsValidIndustry(sub.{end}Id)) continue;', code)
            self.assertIn(f'if (!AITown.IsValidTown(sub.{end}Id)) continue;', code)

    def test_getlocation_spatial_fallback_checks_station_validity(self):
        code = body('lines.nut', 'OpexFindLineForVehicle')
        for end in ['A', 'B']:
            self.assertLess(code.index(f'if (AIStation.IsValidStation(st{end}))'),
                            code.index(f'AIStation.GetLocation(st{end})'))

    def test_missing_getlocation_method_is_not_a_persisted_instance_call(self):
        # Mungo : méthode d'instance perdue. Ici les appels sont des méthodes API.
        for name, code in all_code().items():
            for m in re.finditer(r'\b(\w+)\.GetLocation\s*\(', code):
                self.assertIn(m[1], {'AITown', 'AIIndustry', 'AIStation', 'AIVehicle'}, name)

    def test_depot_orders_are_not_repeatedly_toggled(self):
        for name, fn in [('air_recovery.nut', 'OpexAirContinueRollback'),
                         ('task_report.nut', 'OpexAI::_scrapRetiredVehicles')]:
            code = body(name, fn)
            self.assertIn('AIOrder.IsGotoDepotOrder(', code)
            self.assertIn('AIOrder.OF_STOP_IN_DEPOT', code)
            self.assertIn('AIVehicle.IsValidVehicle(', code)

    def test_rail_cloning_has_line_cap_and_global_slot_check(self):
        code = body('task_rail.nut', 'OpexAI::_expandRailLines')
        clone = code.index('AIVehicle.CloneVehicle(')
        self.assertIn('line.trains < V190_RAIL_MAX_TRAINS', code[:clone])
        self.assertIn('if (!OpexRailVehicleSlotAvailable()) continue;', code[:clone])
        self.assertIn('if (trainWaitingAtSource) continue;', code[:clone])

    def test_road_reinforcement_is_capped_even_when_profitable(self):
        code = body('task_road.nut', 'OpexAI::_refleetRoadLines')
        self.assertIn('if (target > physicalCap) target = physicalCap;', code)
        self.assertIn('!isAnyWaiting', code)
        self.assertIn('return 2 * nMin;', body('economy.nut', 'OpexRoadPhysicalVehicleCap'))
        self.assertIn('economics.profitAnnual <= 0', uncomment(source('candidates.nut')))

    def test_road_depot_connectivity_is_checked_before_purchase(self):
        code = body('builder_road.nut', 'OpexBuildRoadRoute')
        check = code.index('AIRoad.AreRoadTilesConnected(plan.depot.tile, plan.depot.front)')
        self.assertLess(check, code.index('AIVehicle.BuildVehicleWithRefit('))
        self.assertIn('OpexRoadRollback(', code[check:])

    def test_road_passenger_reuse_traverses_connected_existing_roads(self):
        code = body('builder_road.nut', 'OpexRoadBfsPath')
        for token in ['AIRoad.IsRoadTile(nxt)', 'AIRoad.AreRoadTilesConnected(cur, nxt)',
                      'OpexRoadOnDtAxis(src, srcFront, nxt)']:
            self.assertIn(token, code)

    def test_road_construction_builds_one_depot_not_one_per_path_tile(self):
        code = body('builder_road.nut', 'OpexBuildRoadRoute')
        self.assertEqual(code.count('AIRoad.BuildRoadDepot('), 1)
        self.assertIn('plan.depot.tile, plan.depot.front', code)

    @unittest.expectedFailure  # Retire le registre mais ne démolit pas les ouvrages, §6.4 T10/T15.
    def test_retired_lines_schedule_physical_infrastructure_cleanup(self):
        code = body('task_report.nut', 'OpexAI::_scrapDeadLines')
        self.assertRegex(code, r'(?:RemoveAirport|RemoveRoadStation|RemoveRailStation|RemoveDock|Rollback|[Cc]leanup)\s*\(')

    def test_air_build_failure_retains_retryable_cleanup_ticket(self):
        code = body('air_construction.nut', 'OpexAirRollback')
        self.assertLess(code.index('OPEX_AIR_ROLLBACKS.append(ticket)'), code.index('OpexAirContinueRollback(ticket)'))
        for token in ['AIVehicleList_Station(station)', 'if (!used && AIAirport.RemoveAirport(tile)) continue;']:
            self.assertIn(token, body('air_recovery.nut', 'OpexAirContinueRollback'))
        self.assertIn('airRollbacks', body('persist.nut', 'OpexAI::Save'))

    def test_road_vehicle_limit_rechecked_before_infrastructure(self):
        prefix = body('builder_road.nut', 'OpexBuildRoadRoute').split('OpexRoadBuildTrace(')[0]
        self.assertRegex(prefix, r'Opex\w*SlotAvailable\(|"vehicle.max_roadveh"')

    def test_air_vehicle_limit_rechecked_before_infrastructure(self):
        prefix = body('air_construction.nut', 'OpexBuildAirRoute').split('OpexAirLevelFootprint(')[0]
        self.assertRegex(prefix, r'Opex\w*SlotAvailable\(|"vehicle.max_aircraft"')

    def test_ship_vehicle_limit_rechecked_before_infrastructure(self):
        code = body('builder_water.nut', 'OpexBuildWaterRoute')
        prefix = code.split('AIMarine.BuildDock(')[0]
        self.assertRegex(prefix, r'Opex\w*SlotAvailable\(|"vehicle.max_ships"')

    def test_vehicle_slot_helper_covers_all_modes_and_disabled_types(self):
        code = body('builder_rail.nut', 'OpexVehicleSlotAvailable')
        for fragment in ('AIGameSettings.IsDisabledVehicleType(vehicleType)',
                         '"vehicle.max_trains"', '"vehicle.max_roadveh"',
                         '"vehicle.max_aircraft"', '"vehicle.max_ships"',
                         'AIGameSettings.GetValue(setting)',
                         'AIGroup.GetNumVehicles(AIGroup.GROUP_ALL, vehicleType)',
                         'return used < cap'):
            self.assertIn(fragment, code)
        self.assertIn('OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, plannedRoad)',
                      body('builder_road.nut', 'OpexBuildRoadRoute'))
        self.assertIn('OpexVehicleSlotAvailable(AIVehicle.VT_AIR, plannedAir)',
                      body('air_construction.nut', 'OpexBuildAirRoute'))
        self.assertIn('OpexVehicleSlotAvailable(AIVehicle.VT_WATER, 1)',
                      body('builder_water.nut', 'OpexBuildWaterRoute'))
        self.assertIn('result.reason = "NOSLOT"', body('builder_road.nut', 'OpexBuildRoadRoute'))
        self.assertIn('reason == "NOSLOT"', body('lines.nut', 'OpexBuildFailureIsAbandonable'))

    def test_road_partial_rollback_removes_added_edges_in_reverse(self):
        code = body('builder_road.nut', 'OpexRoadRollback')
        self.assertIn('local i = added.len() - 1; i >= 0; i--', code)
        self.assertIn('AIRoad.RemoveRoad(added[i].from, added[i].to)', code)

    def test_buoys_canals_and_locks_are_not_built(self):
        for name, code in all_code().items():
            self.assertNotRegex(code, r'AIMarine\.(?:BuildBuoy|BuildCanal|BuildLock)\s*\(', name)

    def test_adjacent_join_attempt_has_rollback_on_failure(self):
        code = body('builder_road.nut', 'OpexRoadTryJoinStop')
        self.assertIn('stationId', code)
        self.assertIn('AIRoad.RemoveRoad(added[i].from, added[i].to)', code)
        self.assertIn('return null;', code)

    def test_terrain_is_tested_by_commands_not_a_marshland_enum(self):
        code = body('builder_road.nut', 'OpexRoadTraceBuildable')
        self.assertIn('AITestMode()', code)
        self.assertIn('AIRoad.BuildRoad(', code)

    def test_double_head_cannot_create_an_unbounded_wagon_retry(self):
        code = body('builder_rail.nut', 'OpexBuildTrains')
        self.assertIn('w < wagons + wagons2; w++', code)
        self.assertIn('trainLength + carLength > trainLengthLimit', code)
        self.assertIn('if (!AIVehicle.MoveWagon(car, 0, train, 0))', code)
        self.assertNotRegex(code, r'\bwhile\s*\(')

    @unittest.expectedFailure  # Le clamp max_train_length est limité aux pax V207, fret exclu.
    def test_max_train_length_clamp_is_not_limited_to_v207_pax(self):
        code = body('economy.nut', 'OpexLineEconomics')
        self.assertNotRegex(code, r'kind == "pax" && OpexV207Active\(\) && catalog.maxTrainLength')

    def test_all_mode_switches_are_loaded(self):
        code = uncomment(source('settings.nut'))
        for mode in ['rail', 'road', 'air', 'water']:
            self.assertIn(f'AIController.GetSetting("mode_{mode}")', code)

    def test_optional_loaded_keys_have_membership_guards(self):
        code = body('persist.nut', 'OpexAI::Load')
        self.assertIn('if (data == null) return;', code)
        for key in ['lines', 'airRollbacks', 'startYear']:
            self.assertIn(f'"{key}" in data', code)

    @unittest.expectedFailure  # line != null ne valide pas son type avant l'opérateur in.
    def test_loaded_line_type_checked_before_field_membership(self):
        code = body('persist.nut', 'OpexAI::_reconcileAfterLoad')
        prefix = code.split('!("stationA" in line)')[0]
        self.assertRegex(prefix, r'typeof line\s*(?:!=|==)\s*"table"')

    def test_order_removal_loop_checks_progress(self):
        code = body('builder_rail.nut', 'OpexConvertDoubleTrackToLoop')
        loop = re.search(r'while \(AIOrder.GetOrderCount\(otherTrain\) > 0\) \{([^}]+)', code)[1]
        self.assertRegex(loop, r'if\s*\([^\n]*AIOrder.RemoveOrder|\bbreak\b|\breturn\b')


if __name__ == '__main__':
    unittest.main()
