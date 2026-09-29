from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROJECTS = (ROOT / "ai" / "OpexAI" / "projects.nut").read_text(encoding="utf-8")
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
TASK = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
BENCH = (ROOT / "sweeps" / "bench_1v1_5y_20seeds.py").read_text(encoding="utf-8")


def body(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


class TestC118AirTerritorialExpansion(unittest.TestCase):
    def test_settings_default_off(self):
        self.assertIn("C118_AIR_TERRITORIAL_EXPANSION <- false;", GLOBALS)
        self.assertIn("C118_AIR_COVERAGE_PROBE <- false;", GLOBALS)
        start = INFO.index('name = "c118_air_territorial_expansion"')
        snippet = INFO[start:start + 600]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)

    def test_coverage_uses_real_catchment_without_townlist(self):
        station = body(AIR, "function OpexC118StationCoverageTowns", "function OpexC118EndpointCoverageTowns")
        endpoint = body(AIR, "function OpexC118EndpointCoverageTowns", "function OpexC118PlanCoverageTowns")
        coverage = station + endpoint
        self.assertIn("AITileList_StationCoverage", station)
        self.assertIn("OpexC118StationCoverageTowns", endpoint)
        self.assertIn("AITile.GetClosestTown", coverage)
        self.assertIn("AITile.GetCargoProduction", coverage)
        self.assertNotIn("AITownList", coverage)
        self.assertNotIn("AITownList()", coverage)

    def test_annotation_is_air_only_not_fleet_or_c111(self):
        fleet = body(PROJECTS, "function OpexProjectFromFleet", "function OpexC111ProjectFromAir")
        c111 = body(PROJECTS, "function OpexC111ProjectFromAir", "function OpexProjectFromAir")
        air = body(PROJECTS, "function OpexProjectFromAir", "function OpexProjectFromWater")
        self.assertNotIn("c118TownIds", fleet)
        self.assertNotIn("c118TownIds", c111)
        self.assertIn("c118TownIds", air)
        self.assertIn("OpexC118PlanCoverageTowns", air)

    def test_portfolio_and_engine_share_time_to_next(self):
        prep = body(PROJECTS, "function OpexC118PrepareSelection", "function OpexProjectVehicleCount")
        choose = body(AIR, "function OpexC118ChooseBuildPlan", "function OpexAirChooseRoutePlaneFull")
        self.assertIn("c118MinFinance", prep)
        self.assertIn("c118EngineChoices", prep)
        self.assertIn("OpexC118TimeToNextDays", prep)
        self.assertIn("c118EngineChoices", choose)
        self.assertIn("OpexC118TimeToNextDays", choose)
        self.assertIn("OpexC118EconomicsSpendCapital", choose)
        self.assertIn('!("c118NewTowns" in project) || project.c118NewTowns <= 0', choose)
        self.assertNotIn("foreach (plane in catalog.airPlaneChoicesByAirport[plan.airport.type])", choose)

    def test_c115_remains_generation_baseline_and_exports_c68_scan(self):
        c115 = body(AIR, "function OpexC115ChooseRoutePlane", "function OpexC116RouteFinanceCapital")
        full = body(AIR, "function OpexAirChooseRoutePlaneFull", "function OpexM3ProbeAirEquipment")
        self.assertIn("C118_AIR_TERRITORIAL_EXPANSION", c115)
        self.assertIn("c118C68Plane", c115)
        self.assertIn("c118C68Economics", c115)
        self.assertIn("c118EngineChoices", c115)
        c115_branch = full[full.index("if (C115_AIR_C100_CAPITAL_REPLAY"):]
        c115_branch = c115_branch[:c115_branch.index("if (C82_ENGINE_CALIBRATION")]
        self.assertNotIn("!C118_AIR_TERRITORIAL_EXPANSION", c115_branch)

    def test_lexicographic_project_order_and_diagnostics(self):
        insert = body(PROJECTS, "function OpexProjectInsertDefensive", "function OpexPromoteLiveDefensiveAir")
        self.assertLess(insert.index("c118NewTowns"), insert.index("c118NextDays"))
        self.assertLess(insert.index("c118NextDays"), insert.index("c118C68Profit"))
        self.assertLess(insert.index("c118C68Profit"), insert.index("c118C68Roi"))
        for token in ("C118_DECISION", "new_towns=", "next_capital=", "base_cash_after=", "base_flow_after=", "base_days="):
            self.assertIn(token, TASK)
        self.assertIn("C118_COVERAGE", TASK)

    def test_durable_sign_probe_is_parsed_by_harness(self):
        self.assertIn("C118_AIR_DECISION_SEQ <- 0;", GLOBALS)
        for prefix in ("C8D|", "C8R|", "C8E|", "C8C|", "C8F|", "C8T|", "C8V|"):
            self.assertIn(prefix, TASK)
            self.assertIn(prefix, BENCH)
        self.assertIn("def c118_sign_metrics(chunks):", BENCH)
        self.assertIn("structural.update(c118_sign_metrics(chunks))", BENCH)
        for field in ("c118_coverage_events", "c118_decisions", "c118_decision_count"):
            self.assertIn(field, BENCH)


if __name__ == "__main__":
    unittest.main()
