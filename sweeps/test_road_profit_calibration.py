from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ECONOMY = ROOT / "ai" / "OpexAI" / "economy.nut"
BUILDER = ROOT / "ai" / "OpexAI" / "builder_road.nut"
TASK_ROAD = ROOT / "ai" / "OpexAI" / "task_road.nut"
TASK_TOWN = ROOT / "ai" / "OpexAI" / "task_town.nut"
REPORT = ROOT / "ai" / "OpexAI" / "task_report.nut"
PROBES = ROOT / "ai" / "OpexAI" / "probes.nut"
CANDIDATES = ROOT / "ai" / "OpexAI" / "candidates.nut"
DIAG_C23 = ROOT / "sweeps" / "diag_c23_pax_road.py"


class TestRoadProfitCalibration(unittest.TestCase):
    def test_post_site_demand_uses_real_stop_production(self):
        src = BUILDER.read_text(encoding="utf-8")
        section = src[
            src.index("function OpexRoadTownProductionPerHouse"):
            src.index("function OpexRoadPlanFor")
        ]
        self.assertIn("local rawA = plan.stopA.value", section)
        self.assertIn("local rawB = plan.stopB.value", section)
        self.assertIn("AITown.GetLastMonthProduction(townId, cargo)", section)
        self.assertIn("AITown.GetHouseCount(townId)", section)
        self.assertIn("OpexRoadPaxOverlapProducerCount", section)
        self.assertIn("unionProducers = rawA + rawB - overlap", section)
        self.assertIn("OpexRoadPaxDemandFromStops", section)

    def test_post_site_demand_does_not_treat_producer_count_as_monthly_units(self):
        src = BUILDER.read_text(encoding="utf-8")
        section = src[
            src.index("function OpexRoadPlanPaxDemand"):
            src.index("function OpexRoadLivePaxEconomics")
        ]
        self.assertNotIn("local rawTotal = rawA + rawB", section)
        self.assertNotIn("OpexRoadPaxUniqueMonthly(rawA, rawB", section)
        self.assertIn("OpexRoadPaxDemandFromStops", section)

    def test_town_growth_overlap_uses_exact_inclusion_exclusion(self):
        src = BUILDER.read_text(encoding="utf-8")
        section = src[
            src.index("function OpexRoadPaxOverlapProducerCount"):
            src.index("function OpexRoadPlanPaxDemand")
        ]
        self.assertIn("x1 - x0 + 1, y1 - y0 + 1, 0", section)
        self.assertIn("local unionProducers = rawA + rawB - overlap", section)
        self.assertIn("local weightA = 2 * rawA - overlap", section)
        self.assertIn("local weightB = 2 * rawB - overlap", section)

    def test_road_economics_keeps_directional_pax_flows(self):
        src = ECONOMY.read_text(encoding="utf-8")
        section = src[
            src.index("function OpexRoadLineEconomics"):
            src.index("/* M3/G12")
        ]
        self.assertIn("monthlyA = null, monthlyB = null", section)
        self.assertIn("local waitingA = monthlyA.tofloat() * headwayDays / 30.0", section)
        self.assertIn("local waitingB = monthlyB.tofloat() * headwayDays / 30.0", section)
        self.assertIn("pickupA + pickupB", section)

    def test_normal_road_is_repriced_after_siting_with_exact_demand(self):
        src = TASK_ROAD.read_text(encoding="utf-8")
        self.assertIn("local siteDemand = OpexRoadPlanPaxDemand(plan, candidate)", src)
        self.assertIn("plan.routeDistance, pricedA, pricedB", src)
        self.assertIn("candidate.monthly = pricedMonthly", src)
        self.assertIn("buildDate = AIDate.GetCurrentDate()", src)
        self.assertIn("buildPredProfit = candidate.profitAnnual", src)
        self.assertIn("routeDistance = (plan.routeDistance != null", src)

    def test_live_prediction_uses_actual_vehicle_engine_and_capacity(self):
        src = BUILDER.read_text(encoding="utf-8")
        section = src[
            src.index("function OpexRoadLivePaxEconomics"):
            src.index("function OpexRoadPlanFor")
        ]
        self.assertIn("AIVehicle.GetEngineType(v)", section)
        self.assertIn("AIVehicle.GetCapacity(v, line.cargo)", section)
        self.assertIn("AITile.GetCargoProduction(line.stationA", section)
        self.assertIn("OpexRoadPaxDemandFromStops", section)
        self.assertIn("liveVehicles)", section)
        self.assertNotIn("roadEngineByCargo", section)

    def test_town_growth_has_real_one_bus_economics_but_keeps_its_purpose(self):
        src = TASK_TOWN.read_text(encoding="utf-8")
        self.assertIn("local siteDemand = OpexRoadPlanPaxDemand(plan, candidate)", src)
        self.assertIn("candidate.engine, candidate.kind, routeDist, pricedA, pricedB, 1)", src)
        self.assertIn("OpexApplyRoadEconomics(candidate, economics, actualDist)", src)
        self.assertIn("predicted = candidate.profitAnnual", src)
        self.assertIn("predRevenue = candidate.revenueAnnual", src)
        self.assertIn("buildPredRevenue = candidate.revenueAnnual", src)
        self.assertIn("routeDistance = routeDist", src)
        self.assertIn('purpose = "town_growth"', src)
        self.assertNotIn("predicted = 0, iterations = 0", src)

    def test_measurement_exposes_purpose_and_partial_year_days(self):
        probes = PROBES.read_text(encoding="utf-8")
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn('" purpose=" + purpose', probes)
        self.assertIn('" active_days=" + activeDays', probes)
        self.assertIn('local activeStart = line.buildDate > prevStart ? line.buildDate : prevStart', report)
        self.assertIn('" active_days=" + activeDays', report)
        self.assertIn('" year_days=" + yearDays', report)
        self.assertIn('" live_pred_rev=" + livePredRevenue', report)
        self.assertIn('("buildPredRevenue" in line) ? line.buildPredRevenue', report)
        self.assertIn('" live_pred_p=" + livePredProfit', probes)

    def test_extensions_do_not_overwrite_build_prediction(self):
        src = TASK_ROAD.read_text(encoding="utf-8")
        self.assertNotIn("buildPredRevenue +=", src)
        self.assertNotIn("buildPredProfit +=", src)

    def test_c23_pax_generation_uses_road_gen_max(self):
        src = CANDIDATES.read_text(encoding="utf-8")
        section = src[
            src.index("function OpexRoadPaxCandidates"):
            src.index("function OpexRoadLineTownStopCount")
        ]
        self.assertIn('local roadCell = ("roadGenMax" in roadBounds)', section)
        self.assertIn("distance > roadCell", section)
        self.assertNotIn("distance > roadBounds.roadMax", section)
        self.assertIn("road_pax_build est desactive par defaut", section)

    def test_c23_harness_explicitly_exposes_profit_pax_without_town_growth(self):
        src = DIAG_C23.read_text(encoding="utf-8")
        self.assertIn('("road_pax_build", 1)', src)
        self.assertIn('("town_growth", 0)', src)
        self.assertIn("def full_year", src)
        self.assertIn('"active_days"', src)


if __name__ == "__main__":
    unittest.main()
