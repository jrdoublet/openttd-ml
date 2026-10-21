"""V261: contrats source, sans VM ni partie (limites détaillées dans l'audit).

F2.1 est clos par l'audit T28 : `vehicle.forbid_90_deg` n'existe pas en 15.3.
`pf.forbid_90_deg` vaut vrai par défaut et le filtre A* refuse déjà le
demi-tour de tuile (d2 == -d0). Le contrat constate ce filtre ; il n'exige
pas une lecture script du réglage.
Une présence textuelle ne prouve ni fluidité, ni absence de deadlock, ni type
récursif du graphe Save. Aucun chemin externe n'est requis par cette suite.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def uncomment(text):
    # Garder les chaînes (réglages/types) et les sauts de ligne ; ignorer les
    # exemples commentés. Une chaîne contenant // n'est pas un commentaire.
    return re.sub(r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*',
                  lambda m: m[0] if m[0].startswith('"') else
                  re.sub(r"[^\n]", " ", m[0]), text)


def body(name, function):
    text = uncomment(source(name))
    match = re.search(r"\bfunction\s+" + re.escape(function) + r"\s*\(", text)
    if match is None:
        raise AssertionError(f"fonction absente: {name}:{function}")
    start = text.index("{", match.end())
    depth = 0
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|[{}]', text[start:]):
        if token[0] == "{":
            depth += 1
        elif token[0] == "}":
            depth -= 1
            if depth == 0:
                return text[start:start + token.end()]
    raise AssertionError(f"fonction non fermée: {function}")


def all_code():
    return {p.relative_to(AI).as_posix(): uncomment(p.read_text(encoding="utf-8"))
            for p in AI.rglob("*.nut")}


class ForumBehaviours(unittest.TestCase):
    def test_1_1_road_stops_have_owned_spacing_filter(self):
        code = body("builder_road.nut", "OpexBuildRoadRoute")
        self.assertIn("OpexRoadTileTooClose(", code)
        self.assertIn("OpexRoadOurBusTiles(", source("builder_road.nut"))

    def test_1_1_air_joined_stops_require_courtesy_gate(self):
        code = body("air_construction.nut", "OpexAirBuildJoinedStops")
        build = code.index("AIRoad.BuildDriveThroughRoadStation(")
        self.assertIn('if (!OpexLevelAllows("air_joined_road_stops")) return summary;', code[:build])

    def test_1_2_water_does_not_build_canals_buoys_or_terraform(self):
        code = uncomment(source("builder_water.nut"))
        self.assertNotRegex(code, r"AIMarine\.(?:BuildCanal|BuildLock|BuildBuoy)\s*\(")
        self.assertNotRegex(code, r"AITile\.(?:LevelTiles|RaiseTile|LowerTile)\s*\(")
        for bound in ("WATER_MAX_SITE_PROBES", "WATER_MAX_DEPOT_PROBES", "WATER_BFS_MAX_NODES"):
            self.assertIn(bound, code)

    def test_1_3_depot_excludes_both_dock_loading_fronts(self):
        code = body("builder_water.nut", "OpexWaterFindDepot")
        probe = code.index("AIMarine.BuildWaterDepot(")
        prefix = code[:probe]
        self.assertIn('if (!OpexLevelAllows("water_depot_dock_front"))', prefix)
        for site in ("siteA", "siteB"):
            self.assertIn(f'foreach (tile in {site}.waterTiles) protectedFronts[tile] <- true;', prefix)
        self.assertIn('if (!(current in protectedFronts) && !(next in protectedFronts))', prefix)
        # Une paire interdite n'empêche pas l'exploration depuis le front.
        self.assertIn('if (!(next in seen)) { seen.rawset(next, true); queue.append(next); }', code)
        self.assertIn('return null;', code)
        self.assertNotRegex(code, r'\b(?:DemolishTile|RemoveWaterDepot)\(')

    def test_1_4_airport_difficulty_capabilities(self):
        code = uncomment(source("difficulty.nut"))
        self.assertRegex(code, r"preempt_last_airport_slot\s*=\s*2")
        self.assertRegex(code, r"airport_rival_town\s*=\s*1")
        self.assertIn('OpexLevelAllows("preempt_last_airport_slot")', source("air_towns.nut"))

    def test_1_5_exclusive_rights_only_custom(self):
        self.assertRegex(uncomment(source("difficulty.nut")), r"v250_rights\s*=\s*3")
        code = body("task_v250.nut", "OpexAI::_dispatchV250Rights")
        self.assertIn('if (!OpexLevelAllows("v250_rights")) return false;', code)

    def test_1_6_secondary_graft_requires_courtesy_gate(self):
        guard = body("goods_v233.nut", "OpexV233SecondaryRivalServed")
        self.assertIn('if (OpexLevelAllows("secondary_graft_rival_served")) return false;', guard)
        for api in ('AITileList_IndustryAccepting(factory, radius)', 'AIStation.GetCoverageRadius(stationType)',
                    'AITile.GetOwner(tile)', 'AICompany.IsMine(owner)', 'AICompany.COMPANY_INVALID',
                    'AIRail.IsRailStationTile(tile)', 'AITile.TRANSPORT_ROAD', 'AIMarine.IsDockTile(tile)'):
            self.assertIn(api, guard)
        context = body("goods_v233.nut", "OpexV233JoinContextValid")
        self.assertIn('if (OpexV233SecondaryRivalServed(context.v233FactoryId)) return false;', context)
        for function in ('OpexAI::_v233CandidateLive', 'OpexV233SpendAllowed'):
            self.assertIn('OpexV233JoinContextValid(', body('goods_v233.nut', function))

    def test_1_7_demolition_protects_rival_rail_and_rail_stations(self):
        code = body("builder_rail.nut", "OpexV199CanDemolishTile")
        self.assertIn("AIRail.IsRailStationTile", code)
        self.assertIn("if (!AICompany.IsMine(AITile.GetOwner(tile))) return false;", code)
        self.assertIn("AITile.GetOwner", code)

    def test_1_8_partial_construction_has_rollback(self):
        for name, function, api in (
            ("builder_road.nut", "OpexRoadRollback", "AIRoad.RemoveRoad"),
            ("builder_water.nut", "OpexWaterRollback", "AIMarine.RemoveWaterDepot"),
            ("builder_rail.nut", "OpexRollback", "AIRail.RemoveRail"),
        ):
            with self.subTest(name=name):
                self.assertIn(api, body(name, function))
        self.assertIn("IsStoppedInDepot", source("air_recovery.nut"))
        self.assertIn("OPEX_AIR_ROLLBACKS", source("persist.nut"))

    def test_1_9_diagnostics_are_user_configurable(self):
        code = uncomment(source("settings.nut"))
        for setting in ("debug_signs", "probes", "decision_log"):
            self.assertIn(f'AIController.GetSetting("{setting}")', code)
            self.assertIn(f'name = "{setting}"', source("info.nut"))
        self.assertIn("if (!DEBUG_SIGNS) return;", body("probes.nut", "OpexSign"))

    def test_1_9_budget_signs_honor_debug_signs(self):
        code = uncomment(source("task_report.nut"))
        begin = code.index('local btText')
        end = code.index('AISign.BuildSign', begin)
        self.assertIn("DEBUG_SIGNS", code[begin:end])

    def test_1_9_all_direct_sign_builds_are_guarded(self):
        # Inventaire exhaustif : chaque appel direct doit être dans OpexSign
        # (retour anticipé testé plus haut) ou sous une garde positive englobante.
        for name, code in all_code().items():
            if name == 'probes.nut':
                wrapper = body(name, 'OpexSign')
                self.assertEqual(code.count('AISign.BuildSign('), wrapper.count('AISign.BuildSign('))
                continue
            scopes = []
            previous = 0
            for token in re.finditer(r'"(?:\\.|[^"\\])*"|[{}]|AISign\.BuildSign\s*\(', code):
                if token[0] == '{':
                    scopes.append(bool(re.search(r'if\s*\(DEBUG_SIGNS\)\s*$', code[previous:token.start()])))
                elif token[0] == '}':
                    scopes.pop()
                elif token[0].startswith('AISign.'):
                    self.assertTrue(any(scopes), f'{name}: panneau sans DEBUG_SIGNS')
                previous = token.end()

    def check_level_capability(self, feature, expected):
        code = uncomment(source('difficulty.nut'))
        table = re.search(r'OPEX_DIFFICULTY_MIN_LEVEL\s*<-\s*\{(.*?)\};', code, re.S)[1]
        entries = re.findall(r'\b' + re.escape(feature) + r'\s*=\s*(\d+)\b', table)
        self.assertEqual(len(entries), 1)
        resolver = body('difficulty.nut', 'OpexLevelAllows')
        self.assertIn('if (OPEX_DIFFICULTY >= 3) return true;', resolver)
        self.assertIn('return OPEX_DIFFICULTY >= OPEX_DIFFICULTY_MIN_LEVEL[feature];', resolver)
        self.assertEqual([level >= int(entries[0]) for level in range(4)], expected)

    def test_air_joined_road_stops_levels(self):
        self.check_level_capability('air_joined_road_stops', [False, False, True, True])

    def test_water_depot_dock_front_levels(self):
        self.check_level_capability('water_depot_dock_front', [False, False, False, True])

    def test_secondary_graft_rival_served_levels(self):
        self.check_level_capability('secondary_graft_rival_served', [False, False, False, True])

    def test_1_10_freight_generation_exists(self):
        for function in ("OpexFreightCandidates", "OpexRoadFreightCandidates"):
            self.assertIn("cargo", body("candidates.nut", function))
        self.assertIn("generateFreight", body("candidates.nut", "OpexBuildCandidates"))

    def test_2_1_forbid_90_setting_is_consulted(self):
        # Audit T28 : les deux pathfinders sautent le voisin d2 == -d0
        # (pathfinder_v90/v129.nut, pathfinder_v90/rail.nut). Le nom
        # vehicle.forbid_90_deg n'existe pas. Lire pf.forbid_90_deg ici ne
        # changerait aucun tracé : l'A* applique déjà la règle.
        v129 = source("pathfinder_v90/v129.nut")
        rail = source("pathfinder_v90/rail.nut")
        self.assertIn("/* Disallow 90 degree turns */", v129)
        self.assertIn("local blocked = (gp != null) ? (gp._tile - par_tile) : 0;", v129)
        self.assertIn("if (gp != null && offset == blocked) continue;", v129)
        self.assertIn("/* Disallow 90 degree turns */", rail)
        self.assertIn(
            "next_tile - cur_node == path.GetParent().GetParent().GetTile() - path.GetParent().GetTile()",
            rail)
        self.assertIn("OpexNewRailPathfinderV129()", source("builder_rail.nut"))
        tree = "\n".join(all_code().values())
        self.assertNotIn("vehicle.forbid_90_deg", tree)
        self.assertNotRegex(tree, r'AIGameSettings\.(?:GetValue|IsValid)\("pf\.forbid_90_deg"\)')
        self.assertNotRegex(tree, r'AIGameSettings\.(?:GetValue|IsValid)\("vehicle\.forbid_90_deg"\)')

    def test_2_1_train_zero_limit_checked_before_build(self):
        code = body("builder_rail.nut", "OpexRailVehicleSlotAvailable")
        for fragment in ('"vehicle.max_trains"', "AIGameSettings.GetValue(setting)", "return used < cap"):
            self.assertIn(fragment, code)
        for function in ("OpexExecuteRailPlan", "OpexV190ExecuteRailPlan"):
            self.assertIn("OpexRailVehicleSlotAvailable()", body("builder_rail.nut", function))
        self.assertIn("OpexRailVehicleSlotAvailable()", source("task_rail.nut"))

    def test_2_1_disabled_vehicle_types_are_read(self):
        # Decision utilisateur du 18/10 : correctif de robustesse a tous les niveaux.
        self.assertIn("AIGameSettings.IsDisabledVehicleType(", source("tension.nut"))
        settings = source("settings.nut")
        for mode in ("AIR", "RAIL", "ROAD", "WATER"):
            with self.subTest(mode=mode):
                self.assertIn("if (MODE_%s && !OpexModeAllowedByGame(" % mode, settings)
        self.assertLess(settings.index('MODE_WATER = AIController.GetSetting("mode_water")'),
                        settings.index("ROAD_BUILD_ENABLED = MODE_ROAD"))
        self.assertIn("if (!OpexModeVehicleRoom(project.mode, OpexTensionProjectVehicleCount(project))) continue;",
                      source("task_projects.nut"))

    def test_2_2_no_numeric_cargo_or_transport_type_ids(self):
        # Sentinelles -1 autorisées ; aucune exception pour un identifiant réel.
        patterns = (
            r"\b(?:cargo(?:Id)?|paxCargo|mailCargo|railType|roadType)\s*(?:=|<-)\s*\d+\b",
            r"AI(?:Rail|Road)\.SetCurrent(?:Rail|Road)Type\(\s*\d+",
            r"AICargo\.\w+\(\s*\d+\s*[,)]",
            r"(?:CanRefitCargo|RefitVehicle|BuildVehicleWithRefit)\([^,\n]+,\s*\d+\s*[,)]",
        )
        for name, code in all_code().items():
            for pattern in patterns:
                with self.subTest(file=name, pattern=pattern):
                    self.assertNotRegex(code, pattern)
        self.assertIn("AICargoList()", source("catalog.nut"))
        self.assertIn("AICargo.CC_PASSENGERS", source("catalog.nut"))
        self.assertIn("AIRailTypeList()", source("catalog.nut"))

    def test_2_2_road_reuse_checks_each_edge_and_vehicle_power(self):
        code = body("builder_road.nut", "OpexRoadBfsPath")
        self.assertIn("AIRoad.IsRoadTile(nxt)", code)
        self.assertIn("AIRoad.AreRoadTilesConnected(cur, nxt)", code)
        code = body("builder_road.nut", "OpexBuildRoadRoute")
        self.assertIn("AIRoad.SetCurrentRoadType(catalog.roadType)", code)
        self.assertIn("AIRoad.RoadVehHasPowerOnRoad(", code)

    def test_2_3_double_track_rollback_checks_primary_integrity(self):
        self.assertIn("OpexV190VerifyPrimaryTrackIntact(",
                      body("builder_rail.nut", "OpexV190RollbackDoubleTrack"))

    def test_2_4_train_length_measured_before_wagon_attach(self):
        code = uncomment(source("builder_rail.nut"))
        start = code.index("local trainLengthLimit = platformLength * 16;")
        end = code.index("AIVehicle.MoveWagon(car", start)
        for fragment in ("AIVehicle.GetLength(train)", "AIVehicle.GetLength(car)",
                         "trainLength + carLength > trainLengthLimit", 'failure = "LENGTH"'):
            self.assertIn(fragment, code[start:end])

    def test_2_4_train_model_uses_tractive_effort(self):
        self.assertIn("AIEngine.GetMaxTractiveEffort(e)", source("catalog.nut"))
        self.assertIn("OpexRailEffectiveSpeed(", source("economy.nut"))

    def test_3_1_main_loop_yields_and_rail_search_is_sliced(self):
        self.assertIn("AIController.Sleep(1)", uncomment(source("main.nut")))
        code = body("builder_rail.nut", "OpexAdvanceRailPathfinder")
        for fragment in ("spent < iterationBudget", "sliceSpent < sliceIters",
                         "AIController.GetTick() < deadlineTick", "FindPath(PATH_CHUNK)"):
            self.assertIn(fragment, code)

    def test_3_2_valuate_callbacks_are_native_inventory(self):
        # Inventaire exhaustif des premiers arguments. Liste blanche Squirrel vide :
        # aucun petit AIList évalué par closure dans l'arbre actuel.
        native = {
            "AIAirport.GetNearestTown", "AIBridge.GetMaxSpeed", "AIEngine.CanRefitCargo",
            "AIEngine.GetMaxSpeed", "AIEngine.HasPowerOnRail", "AIEngine.IsArticulated",
            "AIEngine.IsBuildable", "AIEngine.IsWagon", "AIMap.GetTileX", "AIMap.DistanceManhattan",
            "AIRail.IsRailTypeAvailable", "AIRoad.IsRoadDepotTile", "AIRoad.IsRoadStationTile",
            "AIRoad.IsRoadTile", "AIStation.GetNearestTown", "AITile.GetCargoProduction",
            "AITile.GetClosestTown", "AITile.GetMaxHeight", "AITile.GetMinHeight",
            "AITile.GetSlope", "AITile.IsBuildable", "AITile.IsCoastTile",
            "AITile.IsStationTile", "AITile.IsWaterTile", "AIVehicle.GetRunningCost",
            "AITown.GetPopulation", "AIIndustry.GetLastMonthProduction",
        }
        api = set()
        for line in (ROOT / "docs/noai_api_15.3.tsv").read_text().splitlines():
            fields = line.split("\t")
            if len(fields) == 3 and fields[0] == "static":
                api.add(".".join(fields[1:]))
        seen = set()
        for name, code in all_code().items():
            for match in re.finditer(r"\.Valuate\s*\(\s*([^,\)]+)", code):
                callback = match[1].strip()
                with self.subTest(file=name, callback=callback):
                    self.assertIn(callback, native)
                    self.assertIn(callback, api)
                seen.add(callback)
        self.assertEqual(native, seen)  # Retrait/ajout à réexaminer, sans compter les appels.

    def test_3_3_real_opcode_api_and_no_debug_break(self):
        for name, code in all_code().items():
            with self.subTest(file=name):
                self.assertNotRegex(code, r"\b(?:AIController\.)?(?:GetOpsLimit|GetOps|Break)\s*\(")
        self.assertIn("AIController.GetOpsTillSuspend()", source("scheduler.nut"))

    def test_3_3_idle_and_terrain_respect_remaining_budget(self):
        self.assertIn("AIController.GetOpsTillSuspend() >= minThreshold", source("scheduler.nut"))
        self.assertIn("AIController.GetOpsTillSuspend() < C67_SLACK_MIN", source("task_terrain.nut"))

    def test_3_4_astar_uses_current_cap_not_forum_constant(self):
        self.assertRegex(uncomment(source("globals_pre.nut")), r"HARD_ITERATION_CAP\s*<-\s*5000\s*;")
        self.assertNotIn("function OpexDynamicHardCap", source("builder_rail.nut"))
        self.assertIn("local hardCap = HARD_ITERATION_CAP;", source("task_rail.nut"))

    def test_3_4_map_work_is_bounded_and_resumable(self):
        code = uncomment(source("terrain_map.nut"))
        self.assertIn("function Step(ops_budget, deadline_tick)", code)
        self.assertIn("this._capacity", code)
        self.assertIn("function Cancel(id)", code)

    def test_3_4_town_pairs_use_spatial_index(self):
        code = body("candidates.nut", "OpexPaxCandidates")
        self.assertIn("grid.Build(towns, cellSize)", code)
        self.assertIn("grid.GetCandidatesFor(a)", code)

    def test_3_4_geometry_precedes_water_dry_run(self):
        code = body("builder_water.nut", "OpexWaterFindSite")
        self.assertLess(code.index("AIMap.DistanceManhattan("), code.index("AITestMode()"))

    def test_4_1_and_4_2_terrain_cache_capacity_and_clear(self):
        code = uncomment(source("terrain_map.nut"))
        self.assertIn("this._cache.len() >= this._capacity", code)
        self.assertIn("function Clear()", code)
        self.assertIn("this._active = null", code)

    def test_4_3_valuate_results_are_consumed_without_recomputing(self):
        for name, function in (("capital.nut", "OpexCashReserve"),
                               ("tension.nut", "OpexTensionFleetScan")):
            code = body(name, function)
            self.assertEqual(code.count("AIVehicle.GetRunningCost"), 1)
            self.assertIn("vehicles.GetValue(v)", code)

    def test_4_4_save_projects_lines_and_does_not_export_pathfinder(self):
        code = body("persist.nut", "OpexAI::Save")
        self.assertIn("return shortSave;", code)
        self.assertIn("return saveObj;", code)
        self.assertIn("OpexSaveProjectLine(line)", code)
        self.assertNotRegex(code, r"(?:=|<-)\s*this\._railSearch\s*[,;]")
        projection = body("persist.nut", "OpexSaveProjectLine")
        for kind in ("integer", "string", "bool", "null", "array", "table"):
            self.assertIn(f'valType != "{kind}"', projection)
        self.assertIn("val.tointeger()", projection)
        self.assertIn("delete serializableLine[key]", projection)
        # Pas une preuve récursive de typage : graphes mutables vérifiés en VM
        # lors d'un futur Save/Load, voir audit F4.4b.


if __name__ == "__main__":
    unittest.main()
