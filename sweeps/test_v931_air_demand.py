"""Contrat V93.1 : demande aerienne par production, defaut 0."""
from pathlib import Path
import re
import unittest
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air

ROOT = Path(__file__).resolve().parents[1]
BUILDER = read_builder_air()
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
TASK_AIR = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")


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
    raise AssertionError(signature)


class V931AirDemandTests(unittest.TestCase):
    def test_setting_defaults_off_and_cap_is_not_a_setting(self):
        self.assertIn("V93_AIR_DEMAND_PRODUCTION <- false;", GLOBALS)
        self.assertIn("V93_AIR_LINE_PAX_CAP <- 200;", GLOBALS)
        self.assertIn("V93_AIR_LINE_PAX_SMALL_POP <- 700;", GLOBALS)
        self.assertIn("V93_AIR_COMPETITOR_WEIGHT <- 70;", GLOBALS)
        self.assertIn("AIR_PAX_REVENUE_CALIBRATION_PCT <- 104;", GLOBALS)
        self.assertIn("C82_ENGINE_CALIBRATION <- false;", GLOBALS)
        self.assertEqual(INFO.count('name = "v93_air_demand_production"'), 1)
        start = INFO.index('name = "v93_air_demand_production"')
        block = INFO[start:INFO.index("});", start)]
        for token in (
            "min_value = 0",
            "max_value = 1",
            "easy_value = 0",
            "medium_value = 0",
            "hard_value = 0",
            "custom_value = 0",
        ):
            self.assertIn(token, block)
        self.assertNotIn("v93_air_line_pax", INFO)
        self.assertNotIn("v93_air_line_pax", SETTINGS)
        self.assertIn(
            'V93_AIR_DEMAND_PRODUCTION = AIController.GetSetting("v93_air_demand_production") != 0;',
            SETTINGS,
        )
        floor = INFO.index('name = "v93_airport_no_pop_floor"')
        self.assertLess(floor, start)

    def test_helper_covers_every_demand_site_under_the_flag(self):
        helper = function_body(BUILDER, "function OpexAirTownMonthlyPax(")
        self.assertIn("pax = pax / (ownLines + 1);", helper)
        self.assertIn("V93_AIR_COMPETITOR_WEIGHT", helper)
        self.assertIn("V93_AIR_LINE_PAX_CAP", helper)
        self.assertIn("V93_AIR_LINE_PAX_SMALL_POP", helper)
        self.assertIn("OpexAirDemandCatchment(", helper)
        self.assertNotIn("V93_AIRPORT_NO_POP_FLOOR", helper)
        self.assertNotIn("TOWN_CATCHMENT_SHARE_PCT", helper)

        sites = {
            "function OpexAirPlansNewPairs(": (
                "OpexAirTownMonthlyPax(sites[a].town, sites[a].anchor, airport, ctx.lines)",
                "OpexAirTownMonthlyPax(sites[b].town, sites[b].anchor, airport, ctx.lines)",
            ),
            "function OpexAirPlansHubToSite(": (
                "OpexAirTownMonthlyPax(hub.town, hub.anchor, airport, ctx.lines)",
                "OpexAirTownMonthlyPax(site.town, site.anchor, airport, ctx.lines)",
            ),
            "function OpexAirPlansHubToHub(": (
                "OpexAirTownMonthlyPax(hub1.town, hub1.anchor, airport, lines)",
                "OpexAirTownMonthlyPax(hub2.town, hub2.anchor, airport, lines)",
            ),
            "function OpexAirReconcileActualBuild(": (
                "OpexAirTownMonthlyPax(plan.siteA.town, anchorA, airport, lines)",
                "OpexAirTownMonthlyPax(plan.siteB.town, anchorB, airport, lines)",
            ),
        }
        for signature, calls in sites.items():
            body = function_body(BUILDER, signature)
            flag = body.index("if (V93_AIR_DEMAND_PRODUCTION)")
            for call in calls:
                self.assertGreater(body.index(call), flag, signature)
            self.assertEqual(body.count("OpexAirTownMonthlyPax("), 2, signature)

        pairs = function_body(BUILDER, "function OpexAirPlansNewPairs(")
        formula = pairs.index(
            "local monthlyPax = ((popA + popB) * TOWN_CATCHMENT_SHARE_PCT) / 100;"
        )
        self.assertLess(formula, pairs.index("if (V93_AIR_DEMAND_PRODUCTION)"))
        self.assertIn("if (monthlyPax < 10) monthlyPax = 10;", pairs)

        reconcile = function_body(BUILDER, "function OpexAirReconcileActualBuild(")
        floor = reconcile.index("if (monthlyPax < 10) monthlyPax = 10;")
        flag = reconcile.index("if (V93_AIR_DEMAND_PRODUCTION)")
        self.assertLess(floor, flag)
        self.assertIn(
            'local joinedMonthly = OPEX_AIR_PLAN_PAD && ("joinedMonthlyPax" in result)',
            reconcile,
        )
        self.assertIn("monthlyPax = demandA + demandB + joinedMonthly;", reconcile)

        build = function_body(BUILDER, "function OpexBuildAirRoute(")
        gated = build.index(
            "if (V93_AIR_DEMAND_PRODUCTION) OpexAirReconcileActualBuild(catalog, plan, result, lines);"
        )
        plain = build.index("else OpexAirReconcileActualBuild(catalog, plan, result);")
        self.assertLess(gated, plain)
        gated_calls = re.findall(
            r"V93_AIR_DEMAND_PRODUCTION\s*\?\s*OpexBuildAirRoute\(this\._catalog, this\._budget, (\w+), this\._lines\)"
            r"\s*:\s*OpexBuildAirRoute\(this\._catalog, this\._budget, (\w+)\);",
            TASK_AIR,
        )
        self.assertEqual(len(gated_calls), 2)
        for with_lines, plain_call in gated_calls:
            self.assertEqual(with_lines, plain_call)
        self.assertEqual(len(re.findall(r"OpexBuildAirRoute\(this\._catalog", TASK_AIR)), 4)

    def test_monthly_memo_and_catalog_cargo(self):
        touch = function_body(BUILDER, "function OpexAirDemandTouchMemo(")
        self.assertIn("AIR_MEMO_MONTH", touch)
        self.assertIn("AIR_ECONOMICS_MEMO = {};", touch)
        self.assertIn("AIR_TRIP_MEMO = {};", touch)
        self.assertIn("AIR_DEMAND_MEMO_DATE", touch)

        town = function_body(BUILDER, "function OpexAirDemandTownRecord(")
        self.assertIn('local key = "v93t|" + townId;', town)
        self.assertIn("AITown.GetLastMonthProduction(townId, paxCargo)", town)
        self.assertIn("AITown.GetLastMonthTransportedPercentage(townId, paxCargo)", town)
        self.assertIn("produced = pop / 8", town)
        self.assertIn("AIR_ECONOMICS_MEMO.rawset(key, record);", town)
        self.assertNotIn("GetLastMonthProduction(townId, 0)", town)

        catchment = function_body(BUILDER, "function OpexAirDemandCatchment(")
        self.assertIn('"v93c|"', catchment)
        self.assertIn("OpexAirAirportCatchmentProduction(", catchment)
        self.assertIn("AIR_ECONOMICS_MEMO.rawset(key, sum);", catchment)

        lines = function_body(BUILDER, "function OpexAirDemandOwnLines(")
        self.assertIn("originA", lines)
        self.assertIn("originB", lines)
        self.assertIn("stationA", lines)
        self.assertIn("stationB", lines)
        self.assertIn("AIR_DEMAND_LINE_MEMO_LEN", lines)
        self.assertIn('line.mode != "air"', lines)

        cargo = function_body(BUILDER, "function OpexAirDemandPaxCargo(")
        self.assertIn("AIR_DEMAND_PAX_CARGO", cargo)
        self.assertIn("AICargo.CC_PASSENGERS", cargo)

        prepare = function_body(BUILDER, "function OpexAirPlansPrepare(")
        self.assertIn(
            "if (V93_AIR_DEMAND_PRODUCTION) AIR_DEMAND_PAX_CARGO = catalog.paxCargo;",
            prepare,
        )
        reconcile = function_body(BUILDER, "function OpexAirReconcileActualBuild(")
        self.assertIn("AIR_DEMAND_PAX_CARGO = catalog.paxCargo;", reconcile)

    def test_admitted_probe_compares_both_models_only_when_enabled(self):
        self.assertEqual(BUILDER.count("paxNew="), 3)
        self.assertEqual(BUILDER.count("paxOld="), 3)
        for signature, arm in (
            ("function OpexAirPlansNewPairs(", "arm=newpair"),
            ("function OpexAirPlansHubToSite(", "arm=hubsite"),
            ("function OpexAirPlansHubToHub(", "arm=hub combo"),
        ):
            body = function_body(BUILDER, signature)
            probe = body.index("paxNew=")
            window = body[max(0, probe - 1200):probe]
            self.assertIn("if (V93_AIR_DEMAND_PRODUCTION)", window, signature)
            self.assertIn(arm, window, signature)
            self.assertIn("paxOld=", body[probe:probe + 40])
            plain = body.index(
                'outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital);',
                probe,
            )
            self.assertNotIn("paxNew", body[plain:plain + 120])


if __name__ == "__main__":
    unittest.main()
