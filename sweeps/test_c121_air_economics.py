"""Contrats statiques C121 : shadow economique AIR unifie, passif."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from campaign_freeze import parse_ai_settings

INFO = ROOT / "ai" / "OpexAI" / "info.nut"
GLOBALS = ROOT / "ai" / "OpexAI" / "globals_pre.nut"
SETTINGS = ROOT / "ai" / "OpexAI" / "settings.nut"
AIR = ROOT / "ai" / "OpexAI" / "builder_air.nut"
TASK_AIR = ROOT / "ai" / "OpexAI" / "task_air.nut"
TASK_PROJECTS = ROOT / "ai" / "OpexAI" / "task_projects.nut"
TASK_REPORT = ROOT / "ai" / "OpexAI" / "task_report.nut"
PROJECTS = ROOT / "ai" / "OpexAI" / "projects.nut"
RUNNER = ROOT / "sweeps" / "run_c121_air_economics_shadow.py"
PERSIST = ROOT / "ai" / "OpexAI" / "persist.nut"
PROBES = ROOT / "ai" / "OpexAI" / "probes.nut"
MAIN = ROOT / "ai" / "OpexAI" / "main.nut"

def body(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i:text.index(end, i)]

class TestC121AirEconomics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.air = AIR.read_text(encoding="utf-8")
        cls.task = TASK_AIR.read_text(encoding="utf-8")
        cls.task_projects = TASK_PROJECTS.read_text(encoding="utf-8")
        cls.task_report = TASK_REPORT.read_text(encoding="utf-8")
        cls.projects = PROJECTS.read_text(encoding="utf-8")
        cls.persist = PERSIST.read_text(encoding="utf-8")
        cls.probes = PROBES.read_text(encoding="utf-8")

    def test_flags_default_off_and_loaded(self):
        defaults = parse_ai_settings(INFO)
        self.assertEqual(defaults["c121_air_economics_shadow"], 0)
        self.assertEqual(defaults["c121_air_economics"], 0)
        self.assertEqual(defaults["c121_air_engine_realization"], 0)
        self.assertEqual(defaults["c121_air_project_realization_adaptive"], 0)
        self.assertEqual(defaults["c121_air_pressure_probe"], 0)
        self.assertEqual(defaults["c121_air_defensive_floor"], 0)
        self.assertEqual(defaults["c121_air_engine_replay_shadow"], 0)
        globals_src = GLOBALS.read_text(encoding="utf-8")
        self.assertIn("C121_AIR_ECONOMICS_SHADOW <- false;", globals_src)
        self.assertIn("C121_AIR_ECONOMICS <- false;", globals_src)
        self.assertIn("C121_AIR_ENGINE_REALIZATION <- false;", globals_src)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_ADAPTIVE <- false;", globals_src)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_MAX_OPEN_PERMILLE <- 200;", globals_src)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_MIN_CONTESTABLE_PERMILLE <- 650;", globals_src)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_MIN_PRESSURED <- 3;", globals_src)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_CLASSIFY_YEARS <- 2;", globals_src)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_YEARS_OBSERVED <- 0;", globals_src)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_REGIME <- -1;", globals_src)
        self.assertIn("C121_AIR_PRESSURE_PROBE <- false;", globals_src)
        settings = SETTINGS.read_text(encoding="utf-8")
        self.assertIn('AIController.GetSetting("c121_air_economics_shadow")', settings)
        self.assertIn('AIController.GetSetting("c121_air_economics")', settings)
        self.assertIn('AIController.GetSetting("c121_air_engine_realization")', settings)
        self.assertIn('AIController.GetSetting("c121_air_project_realization")', settings)
        self.assertIn('AIController.GetSetting("c121_air_project_realization_adaptive")', settings)
        self.assertIn('AIController.GetSetting("c121_air_pressure_probe")', settings)
        self.assertIn('AIController.GetSetting("c121_air_defensive_floor")', settings)
        self.assertIn('AIController.GetSetting("c121_air_initial_project_economics")', settings)
        self.assertIn('AIController.GetSetting("c121_air_engine_replay_shadow")', settings)

    def test_realization_toggles_are_scoped(self):
        project_factor = body(
            self.projects,
            "function OpexC121RealizationFactor",
            "function OpexC121RealizationSums",
        )
        self.assertIn("C121_AIR_PROJECT_REALIZATION", project_factor)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_ADAPTIVE", project_factor)
        self.assertNotIn("OpexC121PressureAdvanceYear();", project_factor)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_REGIME != 1", project_factor)
        self.assertIn('arm != "hubsite" && arm != "hubhub"', project_factor)
        self.assertIn("return 0.75 + 0.25 * learned;", project_factor)
        self.assertIn("0.5 + 0.5 * learned", project_factor)
        self.assertIn("function OpexC121EngineDecisionRealizationFactor", project_factor)
        self.assertIn("C121_AIR_REALIZATION_FACTOR[plan.arm]", project_factor)
        self.assertIn("return 0.5 + 0.5 * learned;", project_factor)
        self.assertIn("learned < 0.0 || learned >= 1.0", project_factor)

        engine = body(
            self.air,
            "function OpexC121EngineEconomics",
            "function OpexC121InitialEngineUpperScore",
        )
        self.assertIn("decisionOnly && C121_AIR_ENGINE_REALIZATION", engine)
        self.assertIn("OpexC121EngineDecisionRealizationFactor(plan)", engine)
        self.assertIn("economics.decisionScore = adjustedScore", engine)
        self.assertIn("economics.engineDecisionRealizationFactor <- factor", engine)

        upper = body(
            self.air,
            "function OpexC121InitialEngineUpperScore",
            "function OpexC121ChooseRoutePlane",
        )
        self.assertIn("OpexC121EngineDecisionRealizationFactor(plan)", upper)
        econ = body(self.air, "function OpexC121AirEconomics", "function OpexC121EngineEconomics")
        self.assertIn("OpexC121RealizationFactor(plan)", econ)
        self.assertNotIn("OpexC121EngineDecisionRealizationFactor(plan)", econ)

    def test_pressure_probe_reuses_c83_slot_cache_and_is_passive(self):
        pressure = body(
            self.projects,
            "function OpexC121PressureNewAccum",
            "/* C78 / course defensive",
        )
        self.assertIn("C121_AIR_PRESSURE_PROBE", pressure)
        self.assertIn("function OpexC121PressureAdvanceYear", pressure)
        self.assertIn("towns = {}", pressure)
        self.assertIn("foreach (townId, remaining in C121_AIR_PRESSURE_ACCUM.towns)", pressure)
        self.assertIn("C121_AIR_PRESSURE_ACCUM.towns.rawset(townId, remaining)", pressure)
        self.assertIn("remaining < C121_AIR_PRESSURE_ACCUM.towns[townId]", pressure)
        self.assertIn("contestablePermille", pressure)
        self.assertIn("openPermille", pressure)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_YEARS_OBSERVED++", pressure)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_CLASSIFY_YEARS", pressure)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_REGIME = efficiency ? 1 : 0", pressure)
        self.assertIn('AILog.Info("C121_STRATEGY_LOCK source_year="', pressure)
        self.assertIn('AILog.Info("C121_STRATEGY source_year="', pressure)
        self.assertIn("state.slotRemaining", pressure)
        self.assertNotIn("GetAllowedNoise", pressure)
        self.assertIn('AILog.Info("C121_PRESSURE year="', pressure)
        select = body(
            self.projects,
            "function OpexProjectSelectAffordable",
            "function OpexProjectSelectionScore",
        )
        self.assertIn("OpexC121RecordPressureSnapshot(defensiveSlotState);", select)
        self.assertIn('AILog.Info("C121_PHASE year="', self.task_report)
        self.assertIn('l.c121Arm == "newpair"', self.task_report)
        self.assertIn('l.c121Arm == "hubsite"', self.task_report)
        self.assertIn('l.c121Arm == "hubhub"', self.task_report)

    def test_b9_is_cargo_generic_and_mail_reuses_passenger_stop_geometry(self):
        block = body(self.air, "function OpexAirB9DemandShadowEndpointCargo", "function OpexAirB9DemandShadowEndpoint(")
        self.assertIn("cargo, stops, stationId", block)
        self.assertIn("stopTiles == null", block)
        demand = body(self.air, "function OpexAirB9DemandShadow(", "function OpexAirCatchmentProbeEndpoint")
        self.assertIn("catalog.mailCargo", demand)
        self.assertIn("a.stopTiles", demand)
        self.assertIn("b.stopTiles", demand)
        for token in ("paxA", "paxB", "mailA", "mailB", "routeDivA", "routeDivB"):
            self.assertIn(token, demand)
        self.assertIn("OpexC121ExistingStationRating", demand)
        self.assertIn("currentPaxRatingA", demand)
        self.assertIn("currentMailRatingB", demand)

    def test_cycle_uses_direct_speed_and_both_endpoint_airports(self):
        physical = body(self.air, "function OpexC121PhysicalOneWayDays", "function OpexC121HubStationId")
        trip = body(self.air, "function OpexC121AirTripModel", "function OpexC121AirportRunwayServiceDays")
        self.assertIn("AIEngine.GetMaxSpeed(engineId)", physical)
        self.assertIn("ground * OpexDaysPerTile(taxiSpeed, tpd) + 300.0 / tpd", physical)
        self.assertIn("AIAirport.GetAirportWidth(typeA)", physical)
        self.assertIn("AIAirport.GetAirportHeight(typeB)", physical)
        self.assertIn("OpexC121EndpointAirportType(plan, 0)", trip)
        self.assertIn("OpexC121EndpointAirportType(plan, 1)", trip)
        self.assertIn("OpexC121PhysicalOneWayDaysFromSpeed(plan.distance, speed, typeA, typeB", trip)
        self.assertIn("engineStatic.maneuverGroundTiles, engineStatic.ticksPerDay", trip)
        self.assertIn("2.0 * physical.oneWayDays + hubDelayA + hubDelayB", trip)
        self.assertIn("local oneWayDays = roundTripDays / 2.0", trip)
        self.assertNotIn("hubDelayA *", trip)
        self.assertNotIn("hubDelayB *", trip)

    def test_hub_delay_is_recent_station_residual_without_empirical_alpha(self):
        globals_src = GLOBALS.read_text(encoding="utf-8")
        self.assertIn("C121_AIR_HUB_DELAY_STATE <- {};", globals_src)
        self.assertIn("C121_AIR_HUB_DELAY_WINDOW_DAYS <- 91;", globals_src)
        self.assertIn("C121_AIR_HUB_DELAY_MIN_OBS <- 2;", globals_src)
        observer = body(self.probes, "function OpexC121HubDelayObserveBatch", "function OpexC121HubDelayFlushLine")
        self.assertIn("state.windowSum += residualSum", observer)
        self.assertIn("state.windowSq += residualSq", observer)
        self.assertIn("state.windowN += residualN", observer)
        self.assertIn("now - state.windowStart >= C121_AIR_HUB_DELAY_WINDOW_DAYS", observer)
        self.assertIn("n >= C121_AIR_HUB_DELAY_MIN_OBS", observer)
        self.assertIn("state.days = mean > 0.0 ? mean : 0.0", observer)
        self.assertNotIn("alpha", observer.lower())

        step = body(self.probes, "function OpexC117AirThroughputStep", "function OpexC39Log")
        self.assertIn("c121PhysicalOneWay = c121PhysicalOneWay", step)
        self.assertIn("state.hubResidualASum += residual", step)
        self.assertIn("state.hubResidualBSum += residual", step)
        self.assertNotIn("OpexC121PhysicalOneWayDays(distance, engine", step)
        flush = body(self.probes, "function OpexC117FlushLine", "function OpexC117AirThroughputStep")
        self.assertIn("OpexC121HubDelayFlushLine(line, state)", flush)
        self.assertIn("c121_adapted_oneway_days", flush)
        main_src = MAIN.read_text(encoding="utf-8")
        self.assertIn("C117_AIR_THROUGHPUT_PROBE || C121_AIR_ECONOMICS_SHADOW || C121_AIR_ECONOMICS", main_src)

    def test_rating_and_fleet_scan_do_not_reuse_legacy_or_aaa_proxies(self):
        rating = body(self.air, "function OpexC121PickupRatingPoints", "function OpexC121AirEconomics")
        self.assertIn("function OpexC121RatingTarget", rating)
        self.assertIn("function OpexC121AirFleetScanCap", rating)
        self.assertIn("local area = 7.5 * 130.0;", rating)
        self.assertIn("(h - 7.5) * 95.0", rating)
        self.assertIn("(h - 15.0) * 50.0", rating)
        self.assertIn("(h - 30.0) * 25.0", rating)
        self.assertIn("return area / h;", rating)
        self.assertIn("AITown.HasStatue", rating)
        self.assertIn("AIEngine.GetMaxSpeed(plane.id).tofloat()", rating)
        self.assertIn("OpexPlaneSpeedDivisor() * 10.0 / 128.0", rating)
        self.assertNotIn("OpexStationRatingForHeadway", rating)
        self.assertNotIn("STATION_RATING_PCT", rating)
        self.assertNotIn("OpexAirportStationDateSpan", rating)
        self.assertNotIn("AIR_MAX_PLANES_PER_ROUTE", rating)
        self.assertIn("ratingWaiting = waitingUpper / 2.0", rating)
        self.assertIn("capacityPerVisit * 30.4 * 255.0", rating)
        self.assertIn("capturableMonthly * headwayDays", rating)

    def test_reused_hub_rating_uses_station_wide_existing_service(self):
        service = body(self.air, "function OpexC121ExistingStationService", "function OpexC121PickupRatingPoints")
        self.assertIn("pickupRate", service)
        self.assertIn("paxRate", service)
        self.assertIn("mailRate", service)
        self.assertIn("AIVehicle.GetCapacity(v, catalog.paxCargo)", service)
        self.assertIn("AIVehicle.GetCapacity(v, catalog.mailCargo)", service)
        self.assertIn("OpexC121HubDelayDays(sidA)", service)
        self.assertIn("OpexC121HubDelayDays(sidB)", service)
        self.assertIn("2.0 * physical.oneWayDays + hubDelayA + hubDelayB", service)
        econ = body(self.air, "function OpexC121AirEconomics", "function OpexC121MeasureBuiltEconomics")
        self.assertIn("serviceA.pickupRate + requestedCandidatePickupRate", econ)
        self.assertIn("serviceB.pickupRate + requestedCandidatePickupRate", econ)
        self.assertIn("serviceA.pickupRate * runwayScaleA", econ)
        self.assertIn("serviceB.pickupRate * runwayScaleB", econ)
        self.assertIn("candidateRunwayScale", econ)
        self.assertIn("paxRawA", econ)
        self.assertIn("mailRawA", econ)
        self.assertIn("OpexC121StationAllocatedMonthly", econ)
        self.assertIn("local offeredPaxA = stationPaxA * routeSharePaxA", econ)
        self.assertIn("local offeredMailA = stationMailA * routeShareMailA", econ)

    def test_station_generation_share_follows_openttd_move_goods(self):
        alloc = body(
            self.air,
            "function OpexC121RatingPercentToByteMid",
            "function OpexAirB9TownUnionMonthly",
        )
        self.assertIn("AITileList_StationCoverage(stationId)", alloc)
        self.assertIn("AIStationList(AIStation.STATION_ANY)", alloc)
        self.assertIn("AIStation.HasCargoRating(st, cargo)", alloc)
        self.assertIn("AIStation.GetCargoRating(st, cargo)", alloc)
        self.assertIn("(pct * 256 + 100) / 101", alloc)
        self.assertIn("local best = rating > bucket.maxRating ? rating : bucket.maxRating", alloc)
        self.assertIn("(best + 1).tofloat() / 256.0", alloc)
        self.assertIn("rating.tofloat() / denom.tofloat()", alloc)
        self.assertNotIn("0.34", alloc)

    def test_large_airport_runway_capacity_is_source_derived(self):
        runway = body(
            self.air,
            "function OpexC121AirportRunwayServiceDays",
            "function OpexC121ExistingStationService",
        )
        self.assertIn("airportType != AIAirport.AT_LARGE", runway)
        self.assertIn("local taxiSpeed = 50;", runway)
        self.assertIn("OpexTicksPerDay(null)", runway)
        self.assertIn("(taxiSpeed * 3) / 4", runway)
        self.assertIn("260.0 / axialPixelsPerDay", runway)
        self.assertIn("30.0 / diagonalPixelsPerDay", runway)
        self.assertNotIn("10.0", runway)
        econ = body(self.air, "function OpexC121AirEconomics", "function OpexC121MeasureBuiltEconomics")
        self.assertIn("OpexC121AirportRunwayServiceDays(trip.airportTypeA)", econ)
        self.assertIn("OpexC121AirportRunwayServiceDays(trip.airportTypeB)", econ)
        self.assertIn("runwayRateA / requestedStationPickupRateA", econ)
        self.assertIn("runwayRateB / requestedStationPickupRateB", econ)
        self.assertIn("requestedCandidatePickupRate * candidateRunwayScale", econ)
        self.assertIn("local departuresPerDirectionMonth = 30.4 * candidatePickupRate;", econ)
        self.assertNotIn("30.4 * planes.tofloat() / trip.roundTripDays", econ)

    def test_pass_and_mail_are_directional_and_paid_separately(self):
        econ = body(self.air, "function OpexC121AirEconomics", "function OpexC121MeasureBuiltEconomics")
        self.assertIn("AICargo.GetCargoIncome(catalog.paxCargo", econ)
        self.assertIn("AICargo.GetCargoIncome(catalog.mailCargo", econ)
        self.assertIn("AIMap.DistanceManhattan(plan.siteA.anchor, plan.siteB.anchor)", econ)
        self.assertIn("OpexC119AirIncomeDays(plane, plan.distance)", econ)
        for token in ("carriedPaxA", "carriedPaxB", "carriedMailA", "carriedMailB", "revenuePaxAnnual", "revenueMailAnnual"):
            self.assertIn(token, econ)
        for forbidden in ("0.34", "0.15", "AIR_MAIL_CAP", "OpexAirFarePerPax"):
            self.assertNotIn(forbidden, econ)
        self.assertNotIn("? plane.ageYears : 20", econ)
        self.assertNotIn("OpexStationRatingForHeadway", econ)
        self.assertIn('local useMail = mailCapacity > 0', econ)
        self.assertIn('local mailDirectionCapacity = useMail ?', econ)
        self.assertIn('local stationMailA = useMail ?', econ)
        self.assertIn('mailKnown = useMail', econ)

    def test_unknown_engine_has_explicit_pass_only_cold_start(self):
        helper = body(self.air, "function OpexC121EngineEconomics", "function OpexC121ChooseRoutePlane")
        self.assertIn("local paxCapacity = plane.capacity;", helper)
        self.assertIn("local mailCapacity = 0;", helper)
        self.assertIn("if (plane.id in C121_AIR_ENGINE_CAPACITY_OBS)", helper)
        self.assertIn("mailCapacity = caps.mail;", helper)
        self.assertIn("economics.engineMailKnown <- mailKnown;", helper)
        for forbidden in ("0.15", "0.34", "run_c121_air_capacity_catalog", "OpenGFX"):
            self.assertNotIn(forbidden, helper)

    def test_causal_chooser_scans_only_catalog_candidates_and_uses_c121(self):
        chooser = body(self.air, "function OpexC121ChooseRoutePlane", "function OpexC121ReplayEngineChoice")
        for token in (
            "catalog.airPlaneChoicesByAirport[plan.airport.type]",
            "AIEngine.IsValidEngine(plane.id)",
            "AIEngine.IsBuildable(plane.id)",
            "OpexAirPlaneInRange(plane, plan.distance)",
            "OpexC121PrepareDemandShadow(catalog, plan, lines)",
            "OpexC121InitialEngineUpperScore(catalog, plan, plane)",
            "candidates.sort(function(a, b)",
            "candidate.upperScore < best.economics.decisionScore",
            "OpexC121EngineEconomics(catalog, plan, plane, C121_AAA_LINE ? 2 : 1, true, null)",
            "economics.decisionScore",
            "OpexC121EngineEconomics(catalog, plan, best.plane, C121_AAA_LINE ? 2 : 1, false)",
            "targetPlanes = initialEconomics.planes",
            "c121EngineScanOps",
            "c121EngineEvalCount",
            "c121ChosenMailKnown",
        ):
            self.assertIn(token, chooser)
        self.assertNotIn("OpexAirEconomics(", chooser)
        self.assertNotIn("GetBuildWithRefitCapacity", chooser)
        self.assertIn("OpexC121EngineEconomics(catalog, plan, best.plane, 0, false)", chooser)
        self.assertIn("decisionEconomics = decisionEconomics", chooser)
        measured = body(self.air, "function OpexC121MeasureBuiltEconomics", "function OpexC121AttachLineShadow")
        self.assertIn("? OpexC121EngineEconomics(catalog, plan, plan.plane, 0)", measured)
        econ = body(self.air, "function OpexC121AirEconomics", "function OpexC121EngineEconomics")
        self.assertIn("decisionScoreFloor", econ)
        self.assertIn("upperScoreOne < decisionScoreFloor", econ)

    def test_causal_generation_wires_all_three_real_air_arms(self):
        self.assertEqual(self.air.count(": OpexC121ChooseRoutePlane(catalog, plan, ctx.lines)"), 2)
        self.assertEqual(self.air.count(": OpexC121ChooseRoutePlane(catalog, plan, lines)"), 1)
        self.assertGreaterEqual(self.air.count("plan.targetPlanes <- routeChoice.targetPlanes;"), 3)
        self.assertIn("AIR_HUBHUB_MARGINAL && !C121_AIR_ECONOMICS", self.air)

    def test_causal_plan_economics_flows_into_project_and_fund_score(self):
        project = body(self.projects, "function OpexProjectFromAir", "function OpexProjectFromWater")
        for token in (
            "local decisionEconomics = (C121_AIR_ECONOMICS",
            "capital = economics.capital",
            "C121_AIR_INITIAL_PROJECT_ECONOMICS",
            "projectEconomics = useInitialProjectEconomics ? economics : decisionEconomics",
            "projectDecisionBudgetCapital = useInitialProjectEconomics ? budgetCapital : decisionBudgetCapital",
            "decisionFinanceCapital = projectDecisionBudgetCapital",
            "profitAnnual = projectEconomics.profitAnnual",
            "revenueAnnual = projectEconomics.revenueAnnual, roi = projectEconomics.roi",
            "budgetScore = OpexProjectScore(projectEconomics.revenueAnnual, projectDecisionBudgetCapital)",
        ):
            self.assertIn(token, project)
        self.assertIn("project.fundScore <- OpexProjectScore", self.projects)
        self.assertIn('if (!C111_AIR_C100_DECISION_SHADOW && !C121_AIR_ECONOMICS)', self.air)
        self.assertIn('if (project.mode == "air" && ("decisionFinanceCapital" in project)', self.projects)

    def test_c121_fleet_growth_uses_true_marginal_and_observed_learning(self):
        measure = body(self.air, "function OpexC121MeasureBuiltEconomics", "function OpexC121AttachLineShadow")
        self.assertIn("actualN + 1", measure)
        self.assertIn("result.c121MarginalProfit", measure)
        self.assertIn("result.c121MarginalRevenue", measure)
        attach = self.air[self.air.index("function OpexC121AttachLineShadow"):]
        self.assertIn("line.c121MarginalProfit", attach)
        self.assertIn("line.c121MarginalSamples <- 0", attach)
        self.assertIn("line.c121EngineId <- plan.plane.id", attach)
        fleet = body(self.projects, "function OpexProjectFromFleet", "function OpexC111ProjectFromAir")
        c121 = fleet[fleet.index("if (c121BelowTarget)"):fleet.index("else if (c84BelowTarget)")]
        self.assertIn("line.c121MarginalProfit", c121)
        self.assertIn("line.c121MarginalRevenue", c121)
        self.assertIn("learnedFactor", c121)
        self.assertIn("builtFactor", c121)
        self.assertIn("C121_AIR_REALIZATION_FACTOR", c121)
        self.assertNotIn("lastProfit / have", c121)
        self.assertIn("c121MarginalBaselineProfit", self.task_projects)
        self.assertIn("c121MarginalObserveYear <- year + 2", self.task_projects)
        self.assertIn("C121_FLEET_MARGINAL", self.task_report)
        self.assertIn("line.c121MarginalProfit * samples + observedProfit", self.task_report)
        self.assertIn("C121_ENGINE_REALIZATION line=", self.task_report)
        self.assertIn("vehCount == c121N0", self.task_report)
        self.assertIn("(year - line.lastAirFleetYear) < 2", self.task)

    def test_c121_reused_endpoints_charge_existing_service_externality(self):
        service = body(
            self.air,
            "function OpexC121ExistingStationService",
            "function OpexC121ExistingMonthlyBefore",
        )
        for token in (
            "paxIncomeWeighted",
            "mailIncomeWeighted",
            "out.paxIncome = paxIncomeWeighted / paxIncomeWeight",
            "out.mailIncome = mailIncomeWeighted / mailIncomeWeight",
        ):
            self.assertIn(token, service)

        static = body(
            self.air,
            "function OpexC121PrepareEngineStatic",
            "function OpexC121AirTripModel",
        )
        for token in (
            "reuseA ? OpexC121ExistingMonthlyBefore",
            "reuseB ? OpexC121ExistingMonthlyBefore",
            "existingPaxBeforeA = existingPaxBeforeA",
            "existingMailBeforeB = existingMailBeforeB",
            "existingPaxIncomeA = serviceA.paxIncome",
            "existingMailIncomeB = serviceB.mailIncome",
        ):
            self.assertIn(token, static)

        econ = body(
            self.air,
            "function OpexC121AirEconomics",
            "function OpexC121InitialEngineUpperScore",
        )
        for token in (
            "local lostPaxA =",
            "local lostPaxB =",
            "local lostMailA =",
            "local lostMailB =",
            "local cannibalLossAnnual =",
            "revenuePaxAnnual + revenueMailAnnual - cannibalLossAnnual",
        ):
            self.assertIn(token, econ)
        self.assertNotIn("AIR_HUBHUB_MARGINAL", econ)

    def test_causal_reconcile_does_not_overwrite_plan_with_legacy_economics(self):
        reconcile = body(self.air, "function OpexAirReconcileActualBuild", "function OpexAirReserveJoinedStops")
        self.assertIn('C121_AIR_ECONOMICS && ("c121Demand" in plan)', reconcile)
        self.assertIn("OpexC121EngineEconomics(catalog, plan, plan.plane, actualPlanes)", reconcile)
        self.assertIn("plan.economics = economics", reconcile)


    def test_causal_chooser_uses_c121_and_normal_engine_filters(self):
        chooser = body(self.air, "function OpexC121ChooseRoutePlane", "function OpexC121ReplayEngineChoice")
        self.assertIn("OpexC121PrepareDemandShadow(catalog, plan, lines)", chooser)
        self.assertIn("AIEngine.IsValidEngine(plane.id)", chooser)
        self.assertIn("AIEngine.IsBuildable(plane.id)", chooser)
        self.assertIn("OpexC118EngineFitsPlan(plan, plane)", chooser)
        self.assertIn("OpexAirPlaneInRange(plane, plan.distance)", chooser)
        self.assertIn("OpexC121InitialEngineUpperScore(catalog, plan, plane)", chooser)
        self.assertIn("OpexC121EngineEconomics(catalog, plan, plane, C121_AAA_LINE ? 2 : 1, true, null)", chooser)
        upper = body(self.air, "function OpexC121InitialEngineUpperScore", "function OpexC121ChooseRoutePlane")
        self.assertIn("OpexC121AirTripModel(plan, plane)", upper)
        self.assertIn("paxCapacity.tofloat() * departuresPerDirectionMonth", upper)
        self.assertIn("mailCapacity.tofloat() * departuresPerDirectionMonth", upper)
        self.assertIn("st.paxRawA.tofloat() < paxDirectionCapacity", upper)
        econ = body(self.air, "function OpexC121AirEconomics", "function OpexC121EngineEconomics")
        self.assertIn("decisionOnly", econ)
        self.assertIn("maxRevenueUpper", econ)
        self.assertIn("upperScore <= scoreBest.score", econ)
        self.assertIn("economics.decisionScore > best.economics.decisionScore", chooser)
        self.assertIn("economics.decisionProfitAnnual > best.economics.decisionProfitAnnual", chooser)
        self.assertNotIn("OpexAirEconomics(", chooser)
        self.assertNotIn("GetBuildWithRefitCapacity", chooser)

    def test_causal_generation_wires_three_real_arms_and_keeps_legacy_fallback(self):
        self.assertEqual(self.air.count(": OpexC121ChooseRoutePlane(catalog, plan,"), 3)
        self.assertGreaterEqual(self.air.count(": OpexAirChooseRoutePlane(catalog, airport, plane,"), 3)
        for arm in ('arm = "newpair"', 'arm = "hubsite"', 'arm = "hubhub"'):
            self.assertIn(arm, self.air)
        self.assertGreaterEqual(self.air.count("plan.targetPlanes <- routeChoice.targetPlanes;"), 3)
        self.assertGreaterEqual(self.air.count("plan.planes = economics.planes;"), 3)
        self.assertGreaterEqual(self.air.count("plan.capital = economics.capital;"), 3)
        self.assertGreaterEqual(self.air.count("plan.economics = economics;"), 3)
        self.assertGreaterEqual(self.task.count("C84_AIR_TARGET_FLEET || C121_AIR_ECONOMICS"), 4)

    def test_c121_target_fleet_relaxes_health_but_keeps_legacy_marginal_out(self):
        self.assertIn("local c121BelowTarget = C121_AIR_ECONOMICS", self.task)
        self.assertIn("local belowTarget = c84BelowTarget || c121BelowTarget;", self.task)
        self.assertIn("if (!belowTarget && (\"lastProfit\" in line) && line.lastProfit < 0)", self.task)
        self.assertIn("if (c121BelowTarget) {", self.task)
        # Hors c121_fleet_stock_growth, un seul renfort par passe (c121StockGrowth vaut 0).
        self.assertIn("maxAddedPerPass = c121StockGrowth > 0 ? (c121StockGrowth < 4 ? c121StockGrowth : 4) : 1;", self.task)
        self.assertIn('C121_AIR_ECONOMICS && ("c121TargetPlanes" in builtLine)', self.task)
        self.assertIn('local c121Age = ("year" in line) ? year - line.year : -1;', self.task)
        self.assertIn('c121Age < 2 || !("lastProfit" in line) || line.lastProfit <= 0', self.task)
        self.assertIn('(year - line.lastAirFleetYear) < 2', self.task)
        self.assertIn("if (c84BelowTarget) {", self.task)
        self.assertIn("OpexAirExistingLineMarginalEconomics", self.task)
        fleet_project = body(self.projects, "function OpexProjectFromFleet", "function OpexC111ProjectFromAir")
        self.assertIn("local c121BelowTarget = C121_AIR_ECONOMICS", fleet_project)
        self.assertIn("perPlaneProfit * entry.want", fleet_project)
        self.assertNotIn("line.lastProfit / have - amortPerPlane", fleet_project)
        self.assertIn("perPlaneRevenue * entry.want", fleet_project)
        self.assertNotIn("line.lastRevenue / have", fleet_project)
        self.assertIn("observedProfit -= line.c121VehicleAmortPerPlane * addedObserved", self.task_report)
        self.assertIn("observedProfit /= addedObserved", self.task_report)
        self.assertIn("observedRevenue /= addedObserved", self.task_report)
        self.assertIn("line.c121MarginalProfit * samples + observedProfit", self.task_report)
        self.assertIn("line.c121MarginalRevenue * samples + observedRevenue", self.task_report)
        self.assertIn("line.c121MarginalObserveYear <- year + 2", self.task_projects)

    def test_c121_fleet_projects_do_not_bypass_kdec(self):
        self.assertIn('local fleetExemptDecision = C69_FLEET_EXEMPT && project.mode == "fleet"', self.projects)
        self.assertIn("&& !OpexC121ProjectHasRealization(project);", self.projects)
        self.assertGreaterEqual(self.projects.count("&& !fleetExemptDecision) ? kDec : decisionFinanceCapital"), 2)

    def test_causal_endpoint_demand_is_cached_per_planning_pass(self):
        endpoint = body(self.air, "function OpexAirB9DemandShadowEndpointCargo", "function OpexAirB9DemandShadowEndpoint(catalog")
        self.assertIn("C121_AIR_ENDPOINT_CACHE", endpoint)
        self.assertIn("cacheKey in C121_AIR_ENDPOINT_CACHE", endpoint)
        self.assertIn("C121_AIR_ENDPOINT_CACHE.rawset(cacheKey, result)", endpoint)
        self.assertIn("c121EndpointCache", self.air)
        self.assertIn("c121_endpoint_hits=", self.air)
        self.assertIn("c121_endpoint_misses=", self.air)

    def test_causal_plan_economics_feed_project_and_cannot_be_rewritten_at_build(self):
        project = body(self.projects, "function OpexProjectFromAir", "function OpexProjectFromWater")
        self.assertIn("local economics = plan.economics;", project)
        self.assertIn("local decisionEconomics = (C121_AIR_ECONOMICS", project)
        self.assertIn("capital = economics.capital", project)
        self.assertIn("decisionFinanceCapital = projectDecisionBudgetCapital", project)
        self.assertIn("profitAnnual = projectEconomics.profitAnnual", project)
        self.assertIn("revenueAnnual = projectEconomics.revenueAnnual, roi = projectEconomics.roi", project)
        self.assertIn("project.fundScore <- OpexProjectScore", self.projects)

        reconcile = body(self.air, "function OpexAirReconcileActualBuild", "function OpexAirReserveJoinedStops")
        self.assertIn('C121_AIR_ECONOMICS && ("c121Demand" in plan)', reconcile)
        self.assertIn("OpexC121EngineEconomics(catalog, plan, plan.plane, actualPlanes)", reconcile)

        c116 = body(self.air, "function OpexC116ChooseBuildPlan", "function OpexC118ChooseBuildPlan")
        self.assertIn("if (C121_AIR_ECONOMICS) return unchanged;", c116)
        c118 = body(self.air, "function OpexC118ChooseBuildPlan", "function OpexAirChooseRoutePlaneFull")
        self.assertIn("if (C121_AIR_ECONOMICS) return unchanged;", c118)

    def test_causal_realization_learning_stays_shadow_and_keeps_air_calibration(self):
        globals_src = GLOBALS.read_text(encoding="utf-8")
        settings = SETTINGS.read_text(encoding="utf-8")
        persist = PERSIST.read_text(encoding="utf-8")
        econ = body(self.air, "function OpexC121AirEconomics", "function OpexC121EngineEconomics")
        c70 = body(self.projects, "function OpexC70Profit", "/* C82")
        own = body(self.projects, "function OpexC121ProjectHasRealization", "function OpexC70Profit")

        self.assertIn("C121_AIR_REALIZATION_FACTOR <- { newpair = 1.0, hubsite = 1.0, hubhub = 1.0 }", globals_src)
        self.assertIn("C121_AIR_REALIZATION_MIN_LINES <- 2;", globals_src)
        self.assertIn("local realizationFactor = OpexC121RealizationFactor(plan);", econ)
        self.assertIn("local rawRevenueAnnual = rawRevenuePaxAnnual + rawRevenueMailAnnual;", econ)
        self.assertIn("rawRevenueAnnual = rawRevenueAnnual", econ)
        self.assertIn("c121RealizationApplied = C121_AIR_ECONOMICS", econ)
        self.assertIn("line.c121Arm <-", self.air)
        self.assertIn("line.c121RawRevenueAnnual <-", self.air)
        self.assertIn("line.c121RealizationPmAtBuild <-", self.air)
        self.assertIn("local keepLineDiagnostics = C121_AIR_ECONOMICS_SHADOW || C121_AIR_ENGINE_REPLAY_SHADOW;", self.air)
        self.assertIn("if (keepLineDiagnostics) {", self.air)
        self.assertIn("vehCount > 0", self.task_report)
        self.assertIn("normalizedRevenue * 1000.0 / line.c121RawRevenueAnnual.tofloat()", self.task_report)
        self.assertIn("c121N0.tofloat() / vehCount.tofloat()", self.task_report)
        self.assertIn("OpexC121ApplyRealizationSums(c121RealizationSums, year, \"annual\")", self.task_report)
        recompute = body(self.projects, "function OpexC121RecomputeRealizationFactors", "function OpexC121ProjectHasRealization")
        self.assertNotIn("vehCount != c121N0", recompute)
        realization = body(self.projects, "function OpexC121RealizationFactor", "function OpexC121RealizationSums")
        self.assertIn("C121_AIR_PROJECT_REALIZATION", realization)
        self.assertIn('arm != "hubsite" && arm != "hubhub"', realization)
        self.assertIn("C121_AIR_REALIZATION_FACTOR[arm]", realization)
        self.assertIn("0.5 + 0.5 * learned", realization)
        self.assertIn("project.mode == \"fleet\"", own)
        self.assertIn("c121MarginalProfit", own)
        self.assertIn('project.mode == "fleet"', c70)
        self.assertIn("&& OpexC121ProjectHasRealization(project)) return project.profitAnnual;", c70)
        self.assertIn("return project.profitAnnual * OpexC70Factor(project);", c70)
        self.assertIn("OpexC121RecomputeRealizationFactors(this._lines)", persist)
        self.assertIn("C121_AIR_REALIZATION_FACTOR.newpair = 1.0;", settings)
        self.assertNotIn("0.733", econ)

    def test_causal_cold_start_becomes_exact_mail_after_first_build(self):
        helper = body(self.air, "function OpexC121EngineEconomics", "function OpexC121ChooseRoutePlane")
        self.assertIn("local mailCapacity = 0;", helper)
        self.assertIn("if (plane.id in C121_AIR_ENGINE_CAPACITY_OBS)", helper)

        measured = body(self.air, "function OpexC121MeasureBuiltEconomics", "function OpexC121AttachLineShadow")
        self.assertIn("AIVehicle.GetCapacity(result.vehicle, catalog.paxCargo)", measured)
        self.assertIn("AIVehicle.GetCapacity(result.vehicle, catalog.mailCargo)", measured)
        self.assertIn("C121_AIR_ENGINE_CAPACITY_OBS.rawset(engineId", measured)
        self.assertIn("OpexC121EngineEconomics(catalog, plan, plan.plane, 0)", measured)
        self.assertIn("causal_choice_mail_known=", self.air)
        self.assertIn("postbuild_mail_known=", self.air)

    def test_c121_save_drops_probe_only_line_state_but_keeps_decision_state(self):
        self.assertIn("local c121SaveSkip = {", self.persist)
        for token in (
            "c121PaxCapacity = true",
            "c121DemandOps = true",
            "c121ActualProfitAnnual = true",
            "c121TargetProfitAnnual = true",
            "c121TargetPlanes = true",
            "if (key in c121SaveSkip) {",
        ):
            self.assertIn(token, self.persist)
        for token in (
            "c121MarginalProfit", "c121MarginalRevenue", "c121MarginalSamples",
            "c121RawRevenueAnnual", "c121VehicleAmortPerPlane", "c121Arm",
        ):
            self.assertNotIn(token + " = true", self.persist)
        self.assertIn("local serializableLine = clone line;", self.persist)
        self.assertIn("delete serializableLine[key];", self.persist)

    def test_causal_reuses_prepared_project_state_and_exposes_scan_cost(self):
        prepare = body(self.air, "function OpexC121PrepareDemandShadow", "function OpexAirCatchmentProbeEndpoint")
        self.assertIn('C121_AIR_ECONOMICS && ("c121Demand" in plan)', prepare)
        self.assertIn('("c121ServiceA" in plan) && ("c121ServiceB" in plan)', prepare)
        chooser = body(self.air, "function OpexC121ChooseRoutePlane", "function OpexC121ReplayEngineChoice")
        for token in (
            "OpexC121PrepareEngineStatic(catalog, plan)",
            "c121EngineStaticOps", "c121EngineStaticTicks",
            "c121EngineScanOps", "c121EngineScanTicks", "c121EngineEvalCount",
            "c121EngineKnownCount", "c121EngineEvalOpsSameTick",
            "c121EngineEvalSameTickCount",
        ):
            self.assertIn(token, chooser)

    def test_causal_engine_static_precomputes_only_project_invariants(self):
        static = body(self.air, "function OpexC121PrepareEngineStatic", "/* C121 : cycle physique")
        self.assertIn("c121EngineStatic", static)
        self.assertIn("OpexC121EndpointAirportType(plan, 0)", static)
        self.assertIn("OpexC121HubDelayState(stationA)", static)
        self.assertIn("AIMap.DistanceManhattan(plan.siteA.anchor, plan.siteB.anchor)", static)
        self.assertIn('AIGameSettings.GetValue("economy.infrastructure_maintenance")', static)
        self.assertIn("OpexC121StatueRatingPoints(plan.siteA.town)", static)
        self.assertIn("OpexC121AirportRunwayServiceDays(typeA)", static)
        self.assertNotIn("AIEngine.GetMaxSpeed", static)
        econ = body(self.air, "function OpexC121AirEconomics", "function OpexC121MeasureBuiltEconomics")
        self.assertIn('local engineStatic = ("c121EngineStatic" in plan)', econ)
        self.assertIn("local speedRating = OpexC121SpeedRatingPoints(plane);", econ)

    def test_c115_remains_available_as_historical_baseline(self):
        self.assertIn("function OpexC115ChooseRoutePlane", self.air)
        full = body(self.air, "function OpexAirChooseRoutePlaneFull", "function OpexAirPlans")
        self.assertIn("C115_AIR_C100_CAPITAL_REPLAY", full)

    def test_fleet_depth_uses_project_roi_not_portfolio_kdec_floor(self):
        econ = body(self.air, "function OpexC121AirEconomics", "function OpexC121MeasureBuiltEconomics")
        self.assertIn("local decisionKDec = engineStatic != null ? engineStatic.decisionKDec : OpexC69CachedKDec();", econ)
        self.assertIn("local decisionScore = totalCapital > 0", econ)
        self.assertIn("best.decisionKDec <- decisionKDec;", econ)
        self.assertNotIn("local decisionDenom", econ)
        self.assertNotIn("capital > decisionKDec ? capital : decisionKDec", econ)

    def test_exact_built_mail_subcapacity_is_observed(self):
        measure = body(self.air, "function OpexC121MeasureBuiltEconomics", "function OpexC121AttachLineShadow")
        self.assertIn("AIVehicle.GetCapacity(result.vehicle, catalog.paxCargo)", measure)
        self.assertIn("AIVehicle.GetCapacity(result.vehicle, catalog.mailCargo)", measure)
        self.assertIn("AIController.GetOpsTillSuspend()", measure)
        self.assertIn("c121EvalOps", measure)
        self.assertIn("OpexAirCalcDeltaOps(tick0, ops0)", measure)
        self.assertIn("local target = C121_AIR_ECONOMICS", measure)
        self.assertIn("local engineId = AIVehicle.GetEngineType(result.vehicle);", measure)
        self.assertIn("local newlyObserved = !(engineId in C121_AIR_ENGINE_CAPACITY_OBS);", measure)
        self.assertIn("C121_AIR_ENGINE_CAPACITY_OBS.rawset(engineId, { pax = paxCapacity, mail = mailCapacity });", measure)
        self.assertNotIn("GetBuildWithRefitCapacity", measure)

    def test_engine_replay_is_optional_passive_and_uses_only_observed_capacity_pairs(self):
        replay = body(self.air, "function OpexC121ReplayEngineChoice", "function OpexC121MeasureBuiltEconomics")
        self.assertIn("C121_AIR_ENGINE_REPLAY_SHADOW", replay)
        self.assertIn("!newlyObserved", replay)
        self.assertIn("!AIEngine.IsBuildable(plane.id)", replay)
        self.assertIn("if (!(plane.id in C121_AIR_ENGINE_CAPACITY_OBS)) continue;", replay)
        self.assertIn("OpexC121AirEconomics(catalog, plan, plane, caps.pax, 0, 0)", replay)
        self.assertIn("OpexC121EngineEconomics(catalog, plan, plane, 0)", replay)
        self.assertIn("changed = bestPass != null && bestMail != null", replay)
        self.assertIn("OpexAirCalcDeltaOps(tick0, ops0)", replay)
        self.assertIn("complete = known == total", replay)
        self.assertNotIn("GetBuildWithRefitCapacity", replay)
        self.assertNotIn("OpexC121SeedEngineReplayCapacityCatalog", self.air)
        self.assertNotIn("run_c121_air_capacity_catalog.py", self.air)
        runner = RUNNER.read_text(encoding="utf-8")
        self.assertIn('("c121_air_engine_replay_shadow", 1 if args.engine_replay else 0)', runner)
        self.assertIn('parser.add_argument(', runner)
        self.assertIn('"--engine-replay"', runner)
        self.assertNotIn("--engine-capacity-catalog", runner)
        self.assertNotIn("C121_AIR_ENGINE_CAPACITY_OBS.rawset", runner)

    def test_shadow_and_causal_state_are_wired_to_both_build_paths(self):
        self.assertGreaterEqual(self.task.count("C121_AIR_ECONOMICS_SHADOW || C121_AIR_ECONOMICS"), 4)
        self.assertEqual(self.task.count("OpexC121PrepareDemandShadow(this._catalog,"), 2)
        self.assertEqual(self.task.count("OpexC121AttachLineShadow("), 2)
        demand = body(self.air, "function OpexC121PrepareDemandShadow", "function OpexAirCatchmentProbeEndpoint")
        self.assertIn("AIController.GetOpsTillSuspend()", demand)
        self.assertIn("c121DemandOps", demand)
        self.assertIn("OpexAirCalcDeltaOps(tick0, ops0)", demand)
        self.assertIn("OpexC121ExistingStationService", demand)
        self.assertIn('C121_AIR_ECONOMICS && ("c121Demand" in plan)', demand)
        self.assertEqual(self.task.count("OpexC121PrepareDemandShadow(this._catalog,"), 2)
        self.assertIn("this._lines", self.task)
        self.assertIn("OpexC121MeasureBuiltEconomics(catalog, plan, result);", self.air)
        start = self.air.index("function OpexAirChooseRoutePlaneFull")
        chooser = self.air[start:start + 18000]
        # C121 utilise un chooser dedie ; le chooser legacy garde C115 baseline.
        self.assertNotIn("C121_AIR_ECONOMICS", chooser)
        self.assertIn("C115_AIR_C100_CAPITAL_REPLAY", chooser)

    def test_shadow_runner_keeps_c115_and_c121_passive(self):
        runner = RUNNER.read_text(encoding="utf-8")
        self.assertIn('("save_full_state", 0)', runner)
        self.assertIn('("c115_air_c100_capital_replay", 1)', runner)
        self.assertIn('("c117_air_throughput_probe", 1)', runner)
        self.assertIn('("c121_air_economics_shadow", 1)', runner)
        self.assertIn('("c121_air_economics", 0)', runner)
        self.assertIn('("c121_air_engine_replay_shadow", 1 if args.engine_replay else 0)', runner)
        self.assertNotIn("engine-capacity-catalog", runner)
        self.assertIn("C121_BUILD", runner)
        self.assertIn("C121_HUB_DELAY", runner)
        self.assertIn('"hub_delay_updates"', runner)

    def test_line_state_is_flat_and_full_save_serializable(self):
        attach = body(self.air, "function OpexC121AttachLineShadow", "function OpexAir")
        self.assertIn("if (C121_AIR_ECONOMICS) {", attach)
        self.assertNotIn("line.c121Demand <- plan.c121Demand;", attach)
        self.assertNotIn("line.c121TargetEconomics <-", attach)
        self.assertNotIn("line.c121ActualEconomics <-", attach)
        self.assertIn("line.c121ActualProfitAnnual <- actual.profitAnnual;", attach)
        self.assertIn("line.c121VehicleAmortPerPlane <-", attach)
        self.assertIn("line.c121TargetProfitAnnual <- target.profitAnnual;", attach)
        self.assertNotIn("C121_AIR_ECONOMICS_SHADOW", PERSIST.read_text(encoding="utf-8"))

class TestC121FleetStockGrowth(unittest.TestCase):
    def test_setting_defaults_off_and_requires_c121(self):
        info = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
        i = info.index('name = "c121_fleet_stock_growth"')
        self.assertIn("custom_value = 0", info[i:i + 400])
        settings = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
        self.assertIn('C121_FLEET_STOCK_GROWTH = C121_AIR_ECONOMICS\n      && AIController.GetSetting("c121_fleet_stock_growth") != 0;', settings)

    def test_stock_rule_replaces_observation_rules_only_under_flag(self):
        task = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")
        self.assertIn("if (c121BelowTarget && C121_FLEET_STOCK_GROWTH) {", task)
        self.assertIn("} else if (c121BelowTarget) {", task)
        self.assertIn("AIDate.GetCurrentDate() - line.lastAirFleetDate < 60", task)
        self.assertIn("function OpexC121FleetStockEvidence(line)", task)



class TestC121TerritoryFirst(unittest.TestCase):
    def test_setting_defaults_off_and_requires_c121(self):
        info = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
        i = info.index('name = "c121_territory_first"')
        self.assertIn("custom_value = 0", info[i:i + 400])
        settings = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
        self.assertIn('C121_TERRITORY_FIRST = C121_AIR_ECONOMICS\n      && AIController.GetSetting("c121_territory_first") != 0;', settings)

    def test_reserve_only_under_flag(self):
        task = (ROOT / "ai" / "OpexAI" / "task_projects.nut").read_text(encoding="utf-8")
        self.assertIn("local c121Served = C121_TERRITORY_FIRST ? OpexC121ServedAirTowns() : null;", task)
        self.assertIn('reason = "c121_territory_reserve"', task)



class TestC121AaaLine(unittest.TestCase):
    def test_setting_defaults_off_and_requires_c121(self):
        info = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
        i = info.index('name = "c121_aaa_line"')
        self.assertIn("custom_value = 0", info[i:i + 400])
        settings = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
        self.assertIn('C121_AAA_LINE = C121_AIR_ECONOMICS\n      && AIController.GetSetting("c121_aaa_line") != 0;', settings)
        self.assertIn("if (C121_AAA_LINE) AIR_FULL_LOAD = 1;", settings)
        self.assertLess(settings.index('C121_AAA_LINE = C121_AIR_ECONOMICS'),
                        settings.index("if (C121_AAA_LINE) AIR_FULL_LOAD = 1;"))

    def test_two_planes_and_second_from_airport_b(self):
        air = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
        self.assertEqual(air.count("C121_AAA_LINE ? 2 : 1"), 2)
        self.assertIn("AIAirport.GetHangarOfAirport(airportB)", air)
        self.assertIn("AIOrder.SkipToOrder(extra, 1)", air)


if __name__ == "__main__":
    unittest.main()
