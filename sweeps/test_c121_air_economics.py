"""Contrats statiques C121 : shadow economique AIR unifie, passif."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from campaign_freeze import parse_ai_settings
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air
from opex_projects_source import read_projects_source

INFO = ROOT / "ai" / "OpexAI" / "info.nut"
GLOBALS = ROOT / "ai" / "OpexAI" / "globals_pre.nut"
SETTINGS = ROOT / "ai" / "OpexAI" / "settings.nut"
AIR = ROOT / "ai" / "OpexAI" / "builder_air.nut"
TASK_AIR = ROOT / "ai" / "OpexAI" / "task_air.nut"
TASK_PROJECTS = ROOT / "ai" / "OpexAI" / "task_projects.nut"
TASK_REPORT = ROOT / "ai" / "OpexAI" / "task_report.nut"
PROJECTS = ROOT / "ai" / "OpexAI" / "projects.nut"
PERSIST = ROOT / "ai" / "OpexAI" / "persist.nut"
PROBES = ROOT / "ai" / "OpexAI" / "probes.nut"
MAIN = ROOT / "ai" / "OpexAI" / "main.nut"

def body(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i:text.index(end, i)]

class TestC121AirEconomics(unittest.TestCase):
    def test_adaptive_realization_applies_in_all_regimes(self):
        defaults = parse_ai_settings(INFO)
        factor = body(self.projects, 'function OpexC121RealizationFactor(plan)',
                      'function OpexC121RealizationSums()')
        self.assertEqual(defaults['c121_air_project_realization_adaptive'], 1)
        self.assertNotIn('C121_AIR_PROJECT_REALIZATION_REGIME != 1', factor)
        self.assertIn('arm != "hubsite" && arm != "hubhub"', factor)
        self.assertIn('if (learned < 0.0 || learned >= 1.0) return 1.0;', factor)
        self.assertIn('return 0.75 + 0.25 * learned;', factor)

    @classmethod
    def setUpClass(cls):
        cls.air = read_builder_air()
        cls.task = TASK_AIR.read_text(encoding="utf-8")
        cls.task_projects = TASK_PROJECTS.read_text(encoding="utf-8")
        cls.task_report = TASK_REPORT.read_text(encoding="utf-8")
        cls.projects = read_projects_source()
        cls.persist = PERSIST.read_text(encoding="utf-8")
        cls.probes = PROBES.read_text(encoding="utf-8")

    def test_realization_toggles_are_scoped(self):
        project_factor = body(
            self.projects,
            "function OpexC121RealizationFactor",
            "function OpexC121RealizationSums",
        )
        self.assertIn("C121_AIR_PROJECT_REALIZATION_ADAPTIVE", project_factor)
        self.assertNotIn("OpexC121PressureAdvanceYear();", project_factor)
        self.assertNotIn("C121_AIR_PROJECT_REALIZATION_REGIME != 1", project_factor)
        self.assertIn('arm != "hubsite" && arm != "hubhub"', project_factor)
        self.assertIn("return 0.75 + 0.25 * learned;", project_factor)
        self.assertIn("learned < 0.0 || learned >= 1.0", project_factor)

        econ = body(self.air, "function OpexC121AirEconomics", "function OpexC121EngineEconomics")
        self.assertIn("OpexC121RealizationFactor(plan)", econ)

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
        self.assertIn("capacityPerVisit * OpexEstimMonthDays(30.4) * 255.0", rating)
        self.assertIn("OpexEstimMonthDays(30.4)", rating)
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

    def test_r15_score_and_profit_snapshots_share_one_schema(self):
        """R15 : les snapshots complets meilleur score / meilleur profit
        doivent garder les memes champs et valeurs ; seul `score` les distingue.
        Le tuple compact decisionOnly reste volontairement plus petit."""
        import re
        econ = body(self.air, "function OpexC121AirEconomics", "function OpexC121EngineEconomics")

        def fields(block):
            flat = " ".join(block.split())
            pairs = re.findall(r"(\w+) = (.+?)(?:, (?=\w+ = )|,\s*$)", flat)
            return dict(pairs)

        score_full = econ.split("} else {\n        scoreBest = {", 1)[1].split("};", 1)[0]
        profit = econ.split("\n      best = {", 1)[1].split("};", 1)[0]
        a, b = fields(score_full), fields(profit)
        self.assertGreater(len(b), 80)
        self.assertEqual(a.pop("score"), "decisionScore")
        self.assertEqual(a, b)
        for key in ("c121RealizationApplied", "realizationFactor", "cannibalLossAnnual",
                    "fleetScanCap", "requestedPickupRate", "stationRating"):
            self.assertIn(key, b)

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
        self.assertIn("local departuresPerDirectionMonth = OpexEstimMonthDays(30.4) * candidatePickupRate;", econ)
        self.assertNotIn("30.4 * planes.tofloat() / trip.roundTripDays", econ)

    def test_pass_and_mail_are_directional_and_paid_separately(self):
        econ = body(self.air, "function OpexC121AirEconomics", "function OpexC121MeasureBuiltEconomics")
        self.assertIn("AICargo.GetCargoIncome(catalog.paxCargo", econ)
        self.assertIn("AICargo.GetCargoIncome(catalog.mailCargo", econ)
        self.assertIn("AIMap.DistanceManhattan(plan.siteA.anchor, plan.siteB.anchor)", econ)
        self.assertIn("OpexC121PhysicalPaymentDays(trip)", econ)
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

    def test_causal_generation_wires_all_three_real_air_arms(self):
        self.assertNotIn(": OpexC121ChooseRoutePlane(catalog, plan, ctx.lines)", self.air)
        self.assertNotIn(": OpexC121ChooseRoutePlane(catalog, plan, lines)", self.air)
        self.assertGreaterEqual(self.air.count("plan.targetPlanes <- routeChoice.targetPlanes;"), 3)
        self.assertNotIn("AIR_HUBHUB_MARGINAL", self.air)

    def test_causal_plan_economics_flows_into_project_and_fund_score(self):
        project = body(self.projects, "function OpexProjectFromAir", "function OpexProjectFromWater")
        for token in (
            "local decisionEconomics = ((\"decisionEconomics\" in plan)",
            "capital = economics.capital",
            "decisionFinanceCapital = decisionBudgetCapital",
            "profitAnnual = decisionEconomics.profitAnnual",
            "revenueAnnual = decisionEconomics.revenueAnnual, roi = decisionEconomics.roi",
            "budgetScore = OpexProjectScore(decisionEconomics.revenueAnnual, decisionBudgetCapital)",
        ):
            self.assertIn(token, project)
        self.assertIn("project.fundScore <- OpexProjectScore(OpexProjectFundProfit(project),", self.projects)
        self.assertNotIn("OpexRailCalFundScore", self.projects)
        self.assertIn("function OpexProjectFundProfit", self.projects)
        self.assertIn("OpexProjectFundProfit(project)", self.projects)
        self.assertIn("scoreDecisionFinanceCapital", self.projects)
        self.assertNotIn('if (!C121_AIR_ECONOMICS)', self.air)
        self.assertIn('if (project.mode == "air" && ("decisionFinanceCapital" in project)', self.projects)

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
        self.assertNotIn('C121_AIR_ECONOMICS', reconcile)
        self.assertIn("OpexC121EngineEconomics(catalog, plan, plan.plane, actualPlanes)", reconcile)
        self.assertIn("plan.economics = economics", reconcile)


    def test_causal_generation_wires_three_real_arms_and_keeps_legacy_fallback(self):
        self.assertNotIn(": OpexC121ChooseRoutePlane(catalog, plan,", self.air)
        self.assertEqual(self.air.count(": OpexAirChooseRoutePlane(catalog, airport, plane,"), 0)
        for arm in ('arm = "newpair"', 'arm = "hubsite"', 'arm = "hubhub"'):
            self.assertIn(arm, self.air)
        self.assertGreaterEqual(self.air.count("plan.targetPlanes <- routeChoice.targetPlanes;"), 3)
        self.assertGreaterEqual(self.air.count("plan.planes = economics.planes;"), 3)
        self.assertGreaterEqual(self.air.count("plan.capital = economics.capital;"), 3)
        self.assertGreaterEqual(self.air.count("plan.economics = economics;"), 3)
        self.assertNotIn("C84_AIR_TARGET_FLEET || C121_AIR_ECONOMICS", self.task)

    def test_c121_target_fleet_relaxes_health_but_keeps_legacy_marginal_out(self):
        self.assertIn("local c121BelowTarget = (\"targetAirPlanes\" in line)", self.task)
        self.assertNotIn("C84_AIR_TARGET_FLEET", self.task)
        self.assertNotIn("c84BelowTarget", self.task)
        self.assertNotIn("OpexAirExistingLineMarginalEconomics", self.task)
        self.assertIn("if (!c121BelowTarget && (\"lastProfit\" in line) && line.lastProfit < 0)", self.task)
        self.assertIn("if (c121BelowTarget) {", self.task)
        # Sous cible C121, un seul renfort par passe.
        self.assertIn("maxAddedPerPass = 1;", self.task)
        self.assertIn('builtLine.targetAirPlanes <- ("c121TargetPlanes" in builtLine)', self.task)
        self.assertIn('local c121Age = ("year" in line) ? year - line.year : -1;', self.task)
        self.assertIn('c121Age < 2 || !("lastProfit" in line) || line.lastProfit <= 0', self.task)
        self.assertIn('(year - line.lastAirFleetYear) < 2', self.task)
        fleet_project = body(self.projects, "function OpexProjectFromFleet", "function OpexAirRequiredMargin")
        self.assertIn("entry.v161BaseVehicles != have", fleet_project)
        self.assertIn("local profit = entry.v161Profit;", fleet_project)
        self.assertNotIn("line.lastProfit / have - amortPerPlane", fleet_project)
        self.assertIn("local revenue = entry.v161DeltaR;", fleet_project)
        self.assertNotIn("line.lastRevenue / have", fleet_project)
        self.assertIn("observedProfit -= line.c121VehicleAmortPerPlane * addedObserved", self.task_report)
        self.assertIn("observedProfit /= addedObserved", self.task_report)
        self.assertIn("observedRevenue /= addedObserved", self.task_report)
        self.assertIn("line.c121MarginalProfit * samples + observedProfit", self.task_report)
        self.assertIn("line.c121MarginalRevenue * samples + observedRevenue", self.task_report)
        self.assertIn("line.c121LastMarginalProfit <- observedProfit", self.task_report)
        self.assertIn("line.c121LastMarginalRevenue <- observedRevenue", self.task_report)
        marginal = (ROOT / "ai" / "OpexAI" / "air_fleet.nut").read_text(encoding="utf-8")
        self.assertIn('"c121LastMarginalProfit" in line', marginal)
        self.assertIn("line.c121LastMarginalProfit <= 0", marginal)
        self.assertIn("line.c121MarginalObserveYear <- year + 2", self.task_projects)

    def test_c121_fleet_projects_do_not_bypass_kdec(self):
        self.assertIn('local fleetExemptDecision = project.mode == "fleet"', self.projects)
        self.assertIn('&& !OpexC121ProjectHasRealization(project)', self.projects)
        self.assertIn('&& !(("v161NetMarginalModeled" in project) && project.v161NetMarginalModeled);',
                      self.projects)
        self.assertGreaterEqual(self.projects.count("&& !fleetExemptDecision)"), 2)
        self.assertGreaterEqual(self.projects.count("? kDec : scoreDecisionFinanceCapital"), 1)

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
        self.assertIn("local decisionEconomics = ((\"decisionEconomics\" in plan)", project)
        self.assertIn("capital = economics.capital", project)
        self.assertIn("decisionFinanceCapital = decisionBudgetCapital", project)
        self.assertIn("profitAnnual = decisionEconomics.profitAnnual", project)
        self.assertIn("revenueAnnual = decisionEconomics.revenueAnnual, roi = decisionEconomics.roi", project)
        self.assertIn("project.fundScore <- OpexProjectScore(OpexProjectFundProfit(project),", self.projects)

        reconcile = body(self.air, "function OpexAirReconcileActualBuild", "function OpexAirReserveJoinedStops")
        self.assertNotIn('C121_AIR_ECONOMICS', reconcile)
        self.assertIn("OpexC121EngineEconomics(catalog, plan, plan.plane, actualPlanes)", reconcile)


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
        self.assertIn("OPEX_SAVE_LINE_SKIP <- {", self.persist)
        for token in (
            "c121PaxCapacity = true",
            "c121DemandOps = true",
            "c121ActualProfitAnnual = true",
            "c121TargetProfitAnnual = true",
            "c121TargetPlanes = true",
            "if (key in OPEX_SAVE_LINE_SKIP) {",
        ):
            self.assertIn(token, self.persist)
        for token in (
            "c121MarginalProfit", "c121MarginalRevenue", "c121MarginalSamples",
            "c121RawRevenueAnnual", "c121VehicleAmortPerPlane", "c121Arm",
        ):
            self.assertNotIn(token + " = true", self.persist)
        self.assertIn("local serializableLine = clone line;", self.persist)
        self.assertIn("delete serializableLine[key];", self.persist)

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

    def test_fleet_depth_keeps_local_roi_for_engine_scan_and_portfolio_floor_is_gated(self):
        econ = body(self.air, "function OpexC121AirEconomics", "function OpexC121MeasureBuiltEconomics")
        self.assertIn("local decisionKDec = engineStatic != null ? engineStatic.decisionKDec : OpexC69CachedKDec();", econ)
        self.assertIn("local decisionCapital = totalCapital;", econ)
        self.assertIn("best.decisionKDec <- decisionKDec;", econ)

    def test_exact_built_mail_subcapacity_is_observed(self):
        measure = body(self.air, "function OpexC121MeasureBuiltEconomics", "function OpexC121AttachLineShadow")
        self.assertIn("AIVehicle.GetCapacity(result.vehicle, catalog.paxCargo)", measure)
        self.assertIn("AIVehicle.GetCapacity(result.vehicle, catalog.mailCargo)", measure)
        self.assertIn("AIController.GetOpsTillSuspend()", measure)
        self.assertIn("c121EvalOps", measure)
        self.assertIn("OpexAirCalcDeltaOps(tick0, ops0)", measure)
        self.assertIn("local target = OpexC121EngineEconomics(catalog, plan, plan.plane, 0);", measure)
        self.assertIn("local engineId = AIVehicle.GetEngineType(result.vehicle);", measure)
        self.assertIn("local newlyObserved = !(engineId in C121_AIR_ENGINE_CAPACITY_OBS);", measure)
        self.assertIn("C121_AIR_ENGINE_CAPACITY_OBS.rawset(engineId, { pax = paxCapacity, mail = mailCapacity });", measure)
        self.assertNotIn("GetBuildWithRefitCapacity", measure)


class TestC121FirstLiveGrowth(unittest.TestCase):
    def test_first_live_growth_defaults_on_and_requires_c121(self):
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('c121_air_first_live_growth',))

    def test_first_live_growth_phase_defaults_four_years_and_falls_back_to_standard(self):
        info = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
        # V236 : la duree de phase est la constante 4
        self.assertNotIn('name = "c121_air_first_live_growth_phase_years"', info)
        settings = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
        self.assertIn('C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS = 4;', settings)
        task = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")
        self.assertIn("C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS <= 0", task)
        self.assertIn("year - OPEX_START_YEAR < C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS", task)
        live_i = task.index("c121BelowTarget && (")
        standard_i = task.index("} else if (c121BelowTarget) {", live_i)
        self.assertGreater(standard_i, live_i)
    def test_first_live_growth_changes_only_first_one_to_two_admission(self):
        task = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")
        self.assertIn('c121BelowTarget && (', task)
        self.assertIn('have == 1 && !("lastAirFleetYear" in line)', task)
        self.assertIn("local firstLiveOk = OpexC121FirstLiveBalanced90(line);", task)
        self.assertIn("if (!firstLiveOk) {", task)
        self.assertIn('local c121Age = ("year" in line) ? year - line.year : -1;', task)
        self.assertIn('if (c121Age < 2 || !("lastProfit" in line) || line.lastProfit <= 0)', task)
        self.assertIn('"c121_first_live_not_ready"', task)
        self.assertIn('(year - line.lastAirFleetYear) < 2', task)
        self.assertIn("maxAddedPerPass = 1;", task)

    def test_first_live_growth_is_early_override_not_a_late_gate(self):
        task = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")
        start = task.index("c121BelowTarget && (")
        end = task.index("} else if (c121BelowTarget) {", start)
        block = task[start:end]
        self.assertIn("local firstLiveOk = OpexC121FirstLiveBalanced90(line);", block)
        self.assertIn("if (!firstLiveOk) {", block)
        self.assertIn("c121Age < 2", block)
        self.assertIn("line.lastProfit <= 0", block)
        self.assertNotIn("c121_first_live_not_ready\", 1);\n        continue;\n      }\n    }", block)

    def test_first_live_growth_reuses_same_shadow_evidence_state(self):
        probes = (ROOT / "ai" / "OpexAI" / "probes.nut").read_text(encoding="utf-8")
        self.assertNotIn("&& !C121_AIR_FIRST_LIVE_GROWTH)", probes)
        self.assertIn("function OpexC121FirstLiveBalanced90(line)", probes)
        self.assertIn('("balanced90" in holder) && holder.balanced90', probes)

    def test_first_live_growth_tags_only_its_fleet_entry(self):
        task = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")
        self.assertIn("local c121FirstLiveEntry = false;", task)
        self.assertIn("c121FirstLiveEntry = true;", task)
        self.assertIn("if (c121FirstLiveEntry) fleetEntry.c121FirstLive <- true;", task)

if __name__ == "__main__":
    unittest.main()
