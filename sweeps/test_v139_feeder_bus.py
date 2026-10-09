from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
MAIN = (ROOT / "ai" / "OpexAI" / "main.nut").read_text(encoding="utf-8")
PROJECTS = (ROOT / "ai" / "OpexAI" / "projects.nut").read_text(encoding="utf-8")
PROJECTS_GEN = (ROOT / "ai" / "OpexAI" / "projects_generation.nut").read_text(encoding="utf-8")
TASK_ROAD = (ROOT / "ai" / "OpexAI" / "task_road.nut").read_text(encoding="utf-8")
FEEDER_BUS = (ROOT / "ai" / "OpexAI" / "feeder_bus.nut").read_text(encoding="utf-8")


class V139FeederBusTests(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        self.assertIn("V139_FEEDER_BUS <- 0;", GLOBALS)
        self.assertEqual(INFO.count('name = "v139_feeder_bus"'), 1)
        start = INFO.index('name = "v139_feeder_bus"')
        block = INFO[start:INFO.index("});", start)]
        for token in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(token, block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertEqual(SETTINGS.count('AIController.GetSetting("v139_feeder_bus")'), 1)
        self.assertIn('V139_FEEDER_BUS = AIController.GetSetting("v139_feeder_bus") != 0;', SETTINGS)
        self.assertIn('require("feeder_bus.nut");', MAIN)

    def test_zero_overhead_when_disabled(self):
        # When V139_FEEDER_BUS is false (0), generation must be strictly bypassed
        self.assertIn("if (V139_FEEDER_BUS) {", PROJECTS)
        self.assertIn("local feeders = OpexBuildFeederCandidates(catalog, lines);", PROJECTS)
        self.assertIn("if (V139_FEEDER_BUS) {", PROJECTS_GEN)
        self.assertIn("local feeders = OpexBuildFeederCandidates(catalog, lines);", PROJECTS_GEN)
        # In task_road, feeder dispatch must be gated by V139_FEEDER_BUS
        self.assertIn('if (V139_FEEDER_BUS && candidate != null && ("isFeeder" in candidate) && candidate.isFeeder)', TASK_ROAD)

    def test_feeder_bus_module_structure_and_helpers(self):
        # Verification of essential functions in feeder_bus.nut
        self.assertIn("function OpexV139LogSkip(airportId, reason)", FEEDER_BUS)
        self.assertIn("function OpexStationCoverageTiles(stationId)", FEEDER_BUS)
        self.assertIn("function OpexAirportIsTownCenterCovered(airportTile, airportType, townCenter)", FEEDER_BUS)
        self.assertIn("function OpexFindTownJoinedStop(airportStationId, airportTile, townId, townCenter)", FEEDER_BUS)
        self.assertIn("function OpexFindAirportFeederStopSite(airportStationId, airportTile, airportType)", FEEDER_BUS)
        self.assertIn("function OpexFindAirportFeederStopSites(airportStationId, airportTile, airportType, townCenter)", FEEDER_BUS)
        self.assertIn("function OpexFindTownFeederStopSite(townCenter, townId, catalog, airportTile", FEEDER_BUS)
        self.assertIn("function OpexTownConnectedRoads(startTile", FEEDER_BUS)
        self.assertIn("function OpexFindFeederDepot(siteTown, siteAirport", FEEDER_BUS)
        self.assertIn("function OpexPlanFeederRoute(siteTown, siteAirport", FEEDER_BUS)
        self.assertIn("function OpexBuildFeederCandidates(catalog, lines)", FEEDER_BUS)
        self.assertIn("function OpexAI::_buildFeederRoute(catalog, budget, candidate)", FEEDER_BUS)
        self.assertIn("function OpexAI::_tryBuildFeederProject(year, project, rank, passDiscards, anchor, yy)", FEEDER_BUS)

    def test_air_network_expansion_1972_guard(self):
        # Never before the end of primary air expansion (post-1972 / 1973+)
        self.assertIn("local currentYear = AIDate.GetYear(AIDate.GetCurrentDate());", FEEDER_BUS)
        self.assertIn("if (currentYear <= 1972) return [];", FEEDER_BUS)

    def test_catchment_check_uses_expanded_rect(self):
        # Catchment check using engine expanded rect
        self.assertIn("OpexAirB9TileInExpandedRect(townCenter, airportTile, w, h, r)", FEEDER_BUS)

    def test_transfer_orders_and_station_join(self):
        # Airport transfer orders must specify OF_TRANSFER | OF_NO_LOAD
        self.assertIn("AIOrder.OF_TRANSFER | AIOrder.OF_NO_LOAD", FEEDER_BUS)
        # Airport bus stop build must join airportStationId
        self.assertIn("AIRoad.BuildDriveThroughRoadStation(t, f, AIRoad.ROADVEHTYPE_BUS, airportStationId)", FEEDER_BUS)

    def test_unjoin_mechanism_and_persistence(self):
        # Decision 5: unjoining existing town stop (RemoveRoadStation + BuildDriveThroughRoadStation with STATION_NEW)
        self.assertIn("AIRoad.RemoveRoadStation(unjoinTile)", FEEDER_BUS)
        self.assertIn("AIRoad.BuildDriveThroughRoadStation(unjoinTile, unjoinFront,\n                                                          AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW)", FEEDER_BUS)
        self.assertIn('AILog.Info("V139_UNJOIN airport="', FEEDER_BUS)
        # Global declaration and persist.nut integration
        self.assertIn("V139_UNJOINED_STOPS <- {};", GLOBALS)
        PERSIST = (ROOT / "ai" / "OpexAI" / "persist.nut").read_text(encoding="utf-8")
        self.assertIn("function OpexV139SaveUnjoinedStops(target)", PERSIST)
        self.assertIn("function OpexV139LoadUnjoinedStops(data)", PERSIST)
        self.assertIn("if (V139_FEEDER_BUS) OpexV139SaveUnjoinedStops(saveObj);", PERSIST)
        self.assertIn("OpexV139LoadUnjoinedStops(data);", PERSIST)

    def test_bus_cap_per_airport(self):
        # Reasonable bus cap per airport (1 to 2, max 3)
        self.assertIn("local busCount = (pop >= 1000) ? 2 : 1;", FEEDER_BUS)
        self.assertIn("if (pop >= 3000) busCount = 3;", FEEDER_BUS)

    def test_logging_formats(self):
        # Logs V139_FEEDER and V139_SKIP
        self.assertIn('AILog.Info("V139_FEEDER airport="', FEEDER_BUS)
        self.assertIn('AILog.Info("V139_SKIP airport="', FEEDER_BUS)
        self.assertIn('AILog.Info("V139_UNJOIN airport="', FEEDER_BUS)

    def test_squirrel_reserved_words_forbidden(self):
        # Ensure no forbidden keywords used as variable names
        # Reserved: resume, clone, base, parent, yield, delete, static, enum, const
        for keyword in ("resume", "clone", "base", "parent", "yield", "delete", "static", "enum", "const"):
            matches = re.findall(rf"\b(local\s+{keyword}|function\s+{keyword}|\.{keyword}\b)", FEEDER_BUS)
            self.assertEqual(matches, [], f"Forbidden keyword '{keyword}' found in feeder_bus.nut")

    def test_balanced_braces(self):
        content = FEEDER_BUS
        # Strip comments and strings
        clean = []
        i = 0
        in_line_comment = False
        in_block_comment = False
        in_string = False
        while i < len(content):
            if in_line_comment:
                if content[i] == "\n":
                    in_line_comment = False
                i += 1
            elif in_block_comment:
                if content[i:i+2] == "*/":
                    in_block_comment = False
                    i += 2
                else:
                    i += 1
            elif in_string:
                if content[i] == "\\":
                    i += 2
                elif content[i] == '"':
                    in_string = False
                    i += 1
                else:
                    i += 1
            else:
                if content[i:i+2] == "//":
                    in_line_comment = True
                    i += 2
                elif content[i:i+2] == "/*":
                    in_block_comment = True
                    i += 2
                elif content[i] == '"':
                    in_string = True
                    i += 1
                else:
                    clean.append(content[i])
                    i += 1
        clean_str = "".join(clean)
        self.assertEqual(clean_str.count("{"), clean_str.count("}"), "Mismatched curly braces in feeder_bus.nut")
        self.assertEqual(clean_str.count("("), clean_str.count(")"), "Mismatched parentheses in feeder_bus.nut")
        self.assertEqual(clean_str.count("["), clean_str.count("]"), "Mismatched brackets in feeder_bus.nut")

    def test_feeder_project_fields_and_portfolio_rank_log_compatibility(self):
        RANK_LOG = (ROOT / "ai" / "OpexAI" / "projects_rank_log.nut").read_text(encoding="utf-8")
        # Ensure roadBerthCapacity safe check exists in projects_rank_log.nut
        self.assertIn('("roadBerthCapacity" in p.payload) ? p.payload.roadBerthCapacity : 2', RANK_LOG)
        # Ensure feeder candidate provides all expected portfolio and road fleet fields
        for field in ("roadBerthCapacity = 2", "vehiclesForVolume = busCount", "roadVehicleCap = busCount",
                      "carried =", "monthly =", "oneWayDays =", "effectiveSpeed =", "ratio =",
                      "isSubsidy = false", "isChain = false", "isRoadExtension = false",
                      "capitalIsActual = false", "originServed = false", "turnoverBonus = 100",
                      "immobilise = 0", "freightBonus = 100", "isTransformer = false", "chantierDays = 30",
                      "srcTown = townId", "dstTown = townId", "srcIndustry = -1", "dstIndustry = -1"):
            self.assertIn(field, FEEDER_BUS)

    def test_smoke3_fixes_candidate_still_valid_feeder(self):
        # OpexCandidateStillValid must explicitly handle isFeeder and not fall into freight
        self.assertIn('local isFeeder = (("kind" in p) && p.kind == "feeder") ||', PROJECTS_GEN)
        self.assertIn('if (!AIStation.IsValidStation(airportId)) return false;', PROJECTS_GEN)
        self.assertIn('("airportStationId" in line) && line.airportStationId == airportId', PROJECTS_GEN)

    def test_smoke3_fixes_persistent_special(self):
        # OpexProjectIsPersistentSpecial must retain feeder projects
        SELECTION = (ROOT / "ai" / "OpexAI" / "projects_selection.nut").read_text(encoding="utf-8")
        self.assertIn('if (("isFeeder" in project.payload) && project.payload.isFeeder) return true;', SELECTION)

    def test_smoke3_fixes_abandoned_pair_key(self):
        # OpexAbandonedPairKey must isolate feeder line failures by (airportStationId, townId)
        LINES = (ROOT / "ai" / "OpexAI" / "lines.nut").read_text(encoding="utf-8")
        self.assertIn('if (("isFeeder" in candidate) && candidate.isFeeder) {', LINES)
        self.assertIn('return "feeder|" + aId + "|" + tId;', LINES)

    def test_smoke3_fixes_incremental_update_injection(self):
        # OpexIncrementalUpdateProjects must inject fresh feeder candidates when airports are built
        UPDATE = (ROOT / "ai" / "OpexAI" / "projects_update.nut").read_text(encoding="utf-8")
        self.assertIn('if (V139_FEEDER_BUS && airBuilt) {', UPDATE)
        self.assertIn('local feeders = OpexBuildFeederCandidates(catalog, lines);', UPDATE)

    def test_smoke3_fixes_town_covered_and_revenue_logging(self):
        # Only town center covered by airport structure itself justifies skip
        FB = (ROOT / "ai" / "OpexAI" / "feeder_bus.nut").read_text(encoding="utf-8")
        self.assertIn('if (OpexAirportIsTownCenterCovered(airportTile, airportType, townCenter)) {', FB)
        self.assertIn('OpexV139LogSkip(stId, "town_covered");', FB)
        # Revenue and threshold logging
        self.assertIn('unprofitable (estim=" + netProfit + " threshold=" + minProfitThreshold', FB)
        self.assertIn('AILog.Info("V139_CANDIDATE airport="', FB)

    def test_smoke4_fixes_test_precheck_before_construction(self):
        # Feasibility check must run under AITestMode before any real construction/demolition
        FB = (ROOT / "ai" / "OpexAI" / "feeder_bus.nut").read_text(encoding="utf-8")
        self.assertIn("ETAPE 0 : PRE-VERIFICATION COMPLETE EN TEST MODE", FB)
        self.assertIn("local testMode = AITestMode();", FB)
        self.assertIn("precheckReason = \"test_airport_stub_failed\";", FB)
        self.assertIn("precheckReason = \"test_trace_failed\";", FB)
        self.assertIn("precheckReason = \"test_airport_stop_failed\";", FB)
        self.assertIn("precheckReason = \"test_depot_failed\";", FB)
        self.assertIn("precheckReason = \"test_unjoin_remove_failed\";", FB)

    def test_smoke4_fixes_order_of_operations_unjoin_last(self):
        # Real construction builds road trace, airport stop and depot FIRST; unjoin happens in last step
        FB = (ROOT / "ai" / "OpexAI" / "feeder_bus.nut").read_text(encoding="utf-8")
        trace_idx = FB.index("if (!OpexRoadBuildTrace(plan.trace, added))")
        depot_idx = FB.index("local depotOk = stubDepot && AIRoad.BuildRoadDepot(plan.depot.tile, plan.depot.front);")
        unjoin_idx = FB.index("AIRoad.RemoveRoadStation(unjoinTile);")
        self.assertLess(trace_idx, unjoin_idx, "Road trace must be built before unjoining town stop")
        self.assertLess(depot_idx, unjoin_idx, "Depot must be built before unjoining town stop")

    def test_smoke4_fixes_unjoined_stop_never_reunjoined(self):
        # Unjoined stops must never be re-unjoined (checked in find stop, candidate gen, and build)
        FB = (ROOT / "ai" / "OpexAI" / "feeder_bus.nut").read_text(encoding="utf-8")
        self.assertIn("if (t in V139_UNJOINED_STOPS) continue;", FB)
        self.assertIn("if (unjoinTile in V139_UNJOINED_STOPS) {", FB)
        self.assertIn("// Arret deja delie precedemment et persiste : ne JAMAIS re-delier !", FB)

    def test_smoke4_fixes_dist_air_cutoff_excludes_airport_perimeter(self):
        # Stops on airport perimeter (distAir <= 4) must strictly not be classified as town stops
        FB = (ROOT / "ai" / "OpexAI" / "feeder_bus.nut").read_text(encoding="utf-8")
        self.assertIn("local distAir = AIMap.DistanceManhattan(t, airportTile);", FB)
        self.assertIn("if (distAir <= 4) continue;", FB)

    def test_smoke4_fixes_abandoned_pair_on_build_failure(self):
        # Failed feeder builds must mark pair abandoned to prevent repeated attempts
        FB = (ROOT / "ai" / "OpexAI" / "feeder_bus.nut").read_text(encoding="utf-8")
        self.assertIn("this._markPairAbandoned(abandonedKey);", FB)
        self.assertIn("this._hadAbandonsThisPass = true;", FB)
        self.assertIn("if (ABANDON_GEN_FILTER && ABANDON_MEMORY && this._abandonedPairs != null && (abandonedKey in this._abandonedPairs))", FB)

    def test_smoke4_fixes_feeder_airports_index_opcode_optimization(self):
        # feederAirports lookup table indexed before airport loop to save opcodes
        FB = (ROOT / "ai" / "OpexAI" / "feeder_bus.nut").read_text(encoding="utf-8")
        self.assertIn("local feederAirports = {};", FB)
        self.assertIn("feederAirports.rawset(line.airportStationId, true);", FB)
        self.assertIn("if (stId in feederAirports) {", FB)


if __name__ == "__main__":
    unittest.main()


