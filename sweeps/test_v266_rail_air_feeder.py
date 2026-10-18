"""V266 source contracts; no OpenTTD execution or Squirrel compilation implied."""
from pathlib import Path
import re
import unittest

from test_c45_subsidy_persistence import function_body

AI = Path(__file__).resolve().parents[1] / "ai/OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def body(name, signature):
    return function_body(source(name), "function " + signature)


class FeederContracts(unittest.TestCase):
    def test_single_setting_off_at_every_level_and_loaded_once(self):
        info = source("info.nut")
        names = re.findall(r'name\s*=\s*"(v266_[^"]+)"', info)
        self.assertEqual(names, ["v266_rail_air_feeder"])
        setting = info.split('name = "v266_rail_air_feeder"')[1].split('});')[0]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{level}_value = 0", setting)
        self.assertEqual(source("settings.nut").count('GetSetting("v266_rail_air_feeder")'), 1)
        self.assertIn("V266_RAIL_AIR_FEEDER <- false;", source("globals_pre.nut"))

    def test_off_gate_precedes_any_observation_or_generation(self):
        scheduler = source("scheduler.nut")
        self.assertIn("if (V266_RAIL_AIR_FEEDER) {\n    local mark = DECISION_LOG", scheduler)
        self.assertIn("this._v266Observe();", scheduler)
        projects = body("task_projects.nut", "OpexAI::_tryBuildProjects(")
        tail = projects.rsplit("if (V266_RAIL_AIR_FEEDER)", 1)[1]
        self.assertIn("this._v266AfterPass();", tail)
        self.assertTrue(tail.rstrip().endswith("return false;"))
        for filename in ("projects.nut", "projects_models.nut", "projects_selection.nut"):
            self.assertNotIn("V266", source(filename))

    def test_departures_use_real_load_and_two_cycles_not_station_waiting(self):
        observe = body("rail_air_v266.nut", "OpexAI::_v266Observe(")
        for token in ("AIVehicle.VS_RUNNING", "AIOrder.IsGotoStationOrder",
                      "AIVehicle.GetCapacity(v, cargo)", "AIVehicle.GetCargoLoad(v, cargo)",
                      "flight.target == target", "airport in flight.departures",
                      "today - previous.date", "previous.cap == cap", "previous.empty"):
            self.assertIn(token, observe)
        self.assertNotIn("GetCargoWaiting", observe)
        self.assertNotIn("AITownList", observe)

    def test_capacity_is_not_sold_twice_and_expires_at_observed_cycle(self):
        live = body("rail_air_v266.nut", "OpexV266OfferLive(")
        for token in ("offer.seats <= 0", "offer.cycle", "offer.aircraft",
                      "offer.finalStation", "OpexV266AirportFree", "AICompany.IsMine",
                      "AIStation.HasStationType", "found &&"):
            self.assertIn(token, live)
        free = body("rail_air_v266.nut", "OpexV266AirportFree(")
        self.assertIn("line.v266Airport == airport", free)

    def test_reserve_covers_live_air_and_fleet_without_stale_score(self):
        reserve = body("rail_air_v266.nut", "OpexAI::_v266Reserve(")
        for token in ("candidateGroups", "OpexC121AutopsyIsAirRelated(p)",
                      "OpexProjectFinanceCapital(p)", "cost > available", "p.payload.line",
                      "OpexIncrementalCandidateStillValid", "local scored = clone p",
                      "OpexProjectFundProfit(p)", "OpexC69ComputeKDec().K_dec"):
            self.assertIn(token, reserve)
        self.assertNotIn('OpexProjectSelectionScore(p, "fundScore")', reserve)
        finish = body("rail_air_v266.nut", "OpexAI::_v266Finish(")
        self.assertLess(finish.index("this._v266Reserve()"), finish.index("local result = OpexBuildLine("))
        self.assertIn("candidate, 0, reserve, HARD_ITERATION_CAP", finish)

    def test_complete_fare_is_marginal_and_never_portfolio_income(self):
        value = body("rail_air_v266.nut", "OpexV266Value(")
        for token in ("v266Offer.annual", "sellable > throughput", "sellable > supply",
                      "v266Offer.finalStation", "AICargo.GetCargoIncome", "fillDays",
                      "candidate.runningAnnual - candidate.amortAnnual", "candidate.roi = 0",
                      "candidate.trains = 1"):
            self.assertIn(token, value)
        self.assertNotIn("feeder_payment_share /", value)
        self.assertNotIn("OpexProjectFromCandidate", source("rail_air_v266.nut"))
        apply = body("economy.nut", "OpexApplyRailEconomics(")
        self.assertIn("V266_RAIL_AIR_FEEDER && OpexV266IsFeeder(candidate)", apply)
        record = body("task_rail.nut", "OpexAI::_recordRailAttempt(")
        self.assertIn("feeder.predicted = 0;", record)
        self.assertIn("feeder.predRevenue = 0;", record)

    def test_join_is_mandatory_and_order_transfers_without_reloading(self):
        platforms = body("rail_air_v266.nut", "OpexV266Platforms(")
        self.assertIn("length, candidate.v266Airport)", platforms)
        self.assertIn("p.stationId <- candidate.v266Airport", platforms)
        self.assertIn("OpexRailSiteReason(a.len() > 0, b.len() > 0)", platforms)
        trains = body("builder_rail.nut", "OpexBuildTrains(")
        self.assertIn('V266_RAIL_AIR_FEEDER && kind == "feeder"', trains)
        self.assertIn("flagsB = nonstopFlag | AIOrder.OF_TRANSFER | AIOrder.OF_NO_LOAD;", trains)
        self.assertLess(trains.index("AIOrder.OF_TRANSFER"), trains.index("AIOrder.AppendOrder"))
        spend = body("builder_rail.nut", "OpexExecuteRailPlan(")
        self.assertLess(spend.index("result.money < need"), spend.index("local costs = AIAccounting()"))
        self.assertLess(spend.index("V266_VALUE_OR_JOIN"), spend.index("AITile.DemolishTile"))

    def test_ready_search_waits_for_normal_pass_and_never_enters_kpass(self):
        consume = body("task_projects.nut", "OpexAI::_consumeResumableRailAtPassStart(")
        branch = consume.split("if (V266_RAIL_AIR_FEEDER", 1)[1].split("if (V233_GOODS_GRAFT", 1)[0]
        self.assertIn("this._v266.ready =", branch)
        self.assertIn("this._railSearch = null;", branch)
        self.assertIn("return false;", branch)
        self.assertNotIn("OpexBuildLine", branch)

    def test_reload_keeps_identity_but_discards_measurements(self):
        self.assertIn("this._v266 = null;", source("persist.nut"))
        self.assertIn("local serializableLine = clone line;", source("persist.nut"))
        record = body("task_rail.nut", "OpexAI::_recordRailAttempt(")
        self.assertIn("feeder.v266AirLine <- candidate.v266AirLine", record)
        self.assertIn("feeder.v266Airport <- candidate.v266Airport", record)

    def test_lifecycle_uses_parent_service_not_train_book_profit(self):
        observe = body("rail_air_v266.nut", "OpexAI::_v266Observe(")
        self.assertIn('this._triggerScrapLine(line, "v266_air_removed")', observe)
        self.assertNotIn("GetProfitLastYear", source("rail_air_v266.nut"))
        expand = body("task_rail.nut", "OpexAI::_expandRailLines(")
        self.assertIn("V266_RAIL_AIR_FEEDER && OpexV266IsFeeder(line)", expand)

    def test_no_unsourced_distance_cash_year_or_cargodist_assumption(self):
        src = source("rail_air_v266.nut")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", src, flags=re.S)
        self.assertNotRegex(code, r"\b(?:80|150000|60|90|1972)\b")
        self.assertNotRegex(code, r"\b(?:local|function)\s+(?:clone|base|parent)\b")
        self.assertNotIn("function(", code)  # no closures with implicit capture
        self.assertIn("AICargo.GetDistributionType(cargo) != AICargo.DT_MANUAL", code)


if __name__ == "__main__":
    unittest.main()
