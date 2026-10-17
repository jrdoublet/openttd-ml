"""Contrat de retrait V93.1 — v93_air_demand_production (defaut 0, refute).

Au defaut, V93_AIR_DEMAND_PRODUCTION etait false : la demande mensuelle
reste le proxy de population, et la reconciliation n'ajoute pas la
production des lignes. v93_airport_no_pop_floor (defaut 1) et le cargo
passagers du catchment de site restent en place.
"""
from pathlib import Path
import unittest

from sweeps.campaign_freeze import parse_ai_settings
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"

REMOVED = (
    "v93_air_demand_production",
    "V93_AIR_DEMAND_PRODUCTION",
    "V93_AIR_LINE_PAX_CAP",
    "V93_AIR_LINE_PAX_SMALL_POP",
    "V93_AIR_COMPETITOR_WEIGHT",
    "AIR_DEMAND_MEMO_DATE",
    "AIR_DEMAND_LINE_MEMO",
    "AIR_DEMAND_LINE_MEMO_LEN",
    "OpexAirDemandTouchMemo",
    "OpexAirDemandTownRecord",
    "OpexAirDemandOwnLines",
    "OpexAirDemandAirportType",
    "OpexAirDemandCatchment",
    "OpexAirTownMonthlyPax",
    "paxNew=",
    "paxOld=",
)


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start:pos + 1]
    raise AssertionError(f"corps non ferme: {signature}")


class V931AirDemandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = source("info.nut")
        cls.globals = source("globals_pre.nut")
        cls.settings = source("settings.nut")
        cls.builder = read_builder_air()
        cls.task_air = source("task_air.nut")

    def test_production_setting_is_gone_and_floor_stays(self):
        defaults = parse_ai_settings(AI / "info.nut")
        self.assertNotIn("v93_air_demand_production", defaults)
        self.assertNotIn('name = "v93_air_demand_production"', self.info)
        self.assertNotIn("V93_AIR_DEMAND_PRODUCTION", self.globals)
        self.assertNotIn('GetSetting("v93_air_demand_production")', self.settings)
        self.assertEqual(defaults["v93_airport_no_pop_floor"], 1)
        self.assertIn("V93_AIRPORT_NO_POP_FLOOR <- true;", self.globals)
        self.assertIn("V93_AIRPORT_MIN_POP <- 100;", self.globals)
        self.assertIn(
            'V93_AIRPORT_NO_POP_FLOOR = AIController.GetSetting("v93_airport_no_pop_floor") != 0;',
            self.settings,
        )
        self.assertIn("AIR_PAX_REVENUE_CALIBRATION_PCT <- 104;", self.globals)
        self.assertNotIn("C82_ENGINE_CALIBRATION", self.globals)
        self.assertNotIn("v93_air_line_pax", self.info)
        for path in AI.glob("*.nut"):
            text = path.read_text(encoding="utf-8")
            for token in REMOVED:
                self.assertNotIn(token, text, f"{path.name}:{token}")

    def test_population_proxy_and_three_arg_build_stay(self):
        pairs = function_body(self.builder, "function OpexAirPlansNewPairs(")
        self.assertIn(
            "local monthlyPax = ((popA + popB) * TOWN_CATCHMENT_SHARE_PCT) / 100;",
            pairs,
        )
        self.assertIn("if (monthlyPax < 10) monthlyPax = 10;", pairs)
        hubsite = function_body(self.builder, "function OpexAirPlansHubToSite(")
        self.assertIn("local monthlyPax = hubMonthly + newMonthly;", hubsite)
        self.assertIn("if (monthlyPax < 10) monthlyPax = 10;", hubsite)
        hubhub = function_body(self.builder, "function OpexAirPlansHubToHub(")
        self.assertIn("local monthlyPax = monthly1 + monthly2;", hubhub)
        self.assertIn("if (monthlyPax < 10) monthlyPax = 10;", hubhub)
        for body in (pairs, hubsite, hubhub):
            self.assertNotIn("OpexAirTownMonthlyPax", body)
            self.assertNotIn("paxNew=", body)

        reconcile = function_body(self.builder, "function OpexAirReconcileActualBuild(")
        self.assertIn('local baseMonthly = ("monthlyPax" in plan) ? plan.monthlyPax : 0;', reconcile)
        self.assertIn("local joinedMonthly = 0;", reconcile)
        self.assertIn("local monthlyPax = baseMonthly + joinedMonthly;", reconcile)
        self.assertIn("if (monthlyPax < 10) monthlyPax = 10;", reconcile)
        self.assertNotIn("demandA + demandB", reconcile)
        build = function_body(self.builder, "function OpexBuildAirRoute(")
        self.assertIn("function OpexBuildAirRoute(catalog, budget, plan)", build)
        self.assertIn("OpexAirReconcileActualBuild(catalog, plan, result);", build)
        self.assertNotIn("OpexAirReconcileActualBuild(catalog, plan, result, lines)", build)
        self.assertEqual(self.task_air.count("OpexBuildAirRoute(this._catalog, this._budget, plan)"), 1)
        self.assertEqual(self.task_air.count("OpexBuildAirRoute(this._catalog, this._budget, buildPlan)"), 1)
        self.assertNotIn("V93_AIR_DEMAND_PRODUCTION", self.task_air)

    def test_site_catchment_cargo_stays_without_monthly_memo(self):
        cargo = function_body(self.builder, "function OpexAirDemandPaxCargo(")
        self.assertIn("AIR_DEMAND_PAX_CARGO", cargo)
        self.assertIn("AICargo.CC_PASSENGERS", cargo)
        self.assertIn("AIR_DEMAND_PAX_CARGO <- -1;", self.globals)
        prepare = function_body(self.builder, "function OpexAirPlansPrepare(")
        self.assertIn("local lines = ctx.lines;", prepare)
        self.assertNotIn("AIR_DEMAND_PAX_CARGO = catalog.paxCargo", prepare)
        self.assertNotIn("function OpexAirTownMonthlyPax(", self.builder)
        self.assertNotIn("function OpexAirDemandTouchMemo(", self.builder)
        self.assertIn("function OpexAirAirportCatchmentProduction(", self.builder)
        sites = source("air_sites.nut")
        self.assertIn("OpexAirDemandPaxCargo(", sites)
        self.assertIn("OpexAirAirportCatchmentProduction(", sites)


if __name__ == "__main__":
    unittest.main()
