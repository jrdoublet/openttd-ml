"""Contrats source de road1y_mail_net (lignes MAIL routieres autonomes).

A 0 le pas retourne avant tout appel API. Aucune partie : compilation,
caisse reelle, depot et ordres servis restent hors de cette suite.
"""
import re
import unittest

from test_v261_forum_behaviours import body, source, uncomment


NEW_FUNCS = (
    "OpexRoad1yMailActivePairs",
    "OpexRoad1yMailNetLog",
    "OpexRoad1yFindMailNetSite",
    "OpexRoad1yMailNetTrace",
    "OpexRoad1yBuildMailNet",
    "OpexRoad1yRefleetMailNet",
    "OpexRoad1yMailNetStep",
)

# Appels reels du module neuf, avec le nombre d'arguments ecrits.
CALLS = (
    ("OpexRoadBfsPath", 5),
    ("OpexRoadTrace", 3),
    ("OpexRoadTraceBuildable", 1),
    ("OpexRoadBuildTrace", 2),
    ("OpexRoadFindDepot", 4),
    ("OpexRoadRollback", 5),
    ("OpexRoadRefitCapacity", 3),
    ("OpexRoadRefleet", 4),
    ("OpexRoad100CatchmentOverlaps", 3),
    ("OpexBusDistrictAxis", 1),
    ("OpexVehicleSlotAvailable", 2),
    ("OpexLineVehicleIds", 2),
    ("OpexDecide", 2),
    ("OpexRoad1yOurTruckTiles", 2),
    ("OpexAir0310InvalidateSiteValidity", 0),
)


def _region():
    text = source("bus_districts.nut")
    start = text.index("ROAD1Y_MAIL_NET : lignes MAIL routieres autonomes")
    return text[start:]


def _arity(name):
    match = re.search(
        r"function\s+" + re.escape(name) + r"\s*\(([^)]*)\)",
        source("builder_road.nut") + "\n" + source("bus_districts.nut")
        + "\n" + source("builder_rail.nut") + "\n" + source("lines.nut")
        + "\n" + source("probes.nut") + "\n" + source("air_coverage.nut")
        + "\n" + source("orchestrator.nut"),
    )
    if match is None:
        return None
    raw = match.group(1).strip()
    if not raw:
        return 0
    return len([part for part in raw.split(",") if part.strip()])


class TestRoad1yMailNet(unittest.TestCase):
    def test_setting_default_zero_four_difficulties(self):
        info = source("info.nut")
        self.assertEqual(info.count('name = "road1y_mail_net"'), 1)
        self.assertIn("function GetVersion()     { return 8; }", info)
        block = info.split('name = "road1y_mail_net",')[1].split("});")[0]
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 12", block)
        self.assertIn("flags = 0", block)
        self.assertNotIn("AICONFIG_BOOLEAN", block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", block)
        gap = info.index('name = "road1y_gap"')
        net = info.index('name = "road1y_mail_net"')
        pax = info.index('name = "road1y_mail_on_pax"')
        self.assertLess(gap, net)
        self.assertLess(net, pax)

    def test_global_and_both_loaders_gate_road_only(self):
        self.assertIn("ROAD1Y_MAIL_NET <- 0;", source("globals_pre.nut"))
        settings = source("settings.nut")
        self.assertEqual(settings.count('GetSetting("road1y_mail_net")'), 2)
        for filename in ("info.nut", "globals_pre.nut", "bus_districts.nut",
                         "bus_districts_overrides.nut", "builder_road.nut"):
            self.assertNotIn('GetSetting("road1y_mail_net")', source(filename))
        for loader_name in ("OpexLoadSettings", "OpexLoadBusDistrictSettings"):
            loader = body("settings.nut", loader_name)
            read_at = loader.index('GetSetting("road1y_mail_net")')
            self.assertIn(
                "if (ROAD1Y_MAIL_NET < 0 || ROAD1Y_MAIL_NET > 12) ROAD1Y_MAIL_NET = 0;",
                loader,
            )
            gate = "if (!road1yRoadOnly) ROAD1Y_MAIL_NET = 0;"
            self.assertIn(gate, loader)
            self.assertLess(read_at, loader.index(gate))
        bus = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertLess(
            bus.index('GetSetting("road1y_mail_net")'),
            bus.index('require("bus_districts_overrides.nut")'),
        )

    def test_zero_returns_before_any_api_and_keeps_child_step(self):
        step = uncomment(body("bus_districts.nut", "OpexRoad1yMailNetStep"))
        guard = "if (ROAD1Y_MAIL_NET <= 0) return;"
        self.assertIn(guard, step)
        self.assertLess(step.index(guard), step.find("AI"))
        overrides = uncomment(source("bus_districts_overrides.nut"))
        self.assertIn(
            "if (ROAD1Y_MAIL_ON_PAX) OpexRoad1yMailStep(this, year);\n"
            "  if (ROAD1Y_MAIL_NET > 0) OpexRoad1yMailNetStep(this, year);",
            overrides,
        )
        self.assertNotIn("else if (ROAD1Y_MAIL_ON_PAX) OpexRoad1yMailStep", overrides)
        self.assertIn(
            "if (ROAD1Y_EXTRA_STOPS > 0 || ROAD1Y_MAIL_ON_PAX || ROAD1Y_MAIL_NET > 0) "
            "OpexAI._refleetRoadLines <- OpexRoad1yRefleetSaved;",
            overrides,
        )
        mail_step = body("bus_districts.nut", "OpexRoad1yMailStep")
        self.assertNotIn("ROAD1Y_MAIL_NET", mail_step)
        child = body("bus_districts.nut", "OpexRoad1yRefleetMailLine")
        self.assertIn("OpexRoad1yParentAlive", child)
        self.assertIn("local mailCap = 2 * stops;", child)
        self.assertIn("if (ROAD1Y_GAP > mailCap) mailCap = ROAD1Y_GAP;", child)
        self.assertNotIn("mail_net", child)

    def test_refleet_and_orders_keep_mail_pax_and_full_load_mail_net(self):
        loop = uncomment(body("bus_districts_overrides.nut", "OpexRoad1yRefleetSaved"))
        net_at = loop.index('line.kind == "mail_net"')
        pax_at = loop.index('line.kind == "mail_pax"')
        self.assertLess(net_at, pax_at)
        self.assertIn("ROAD1Y_MAIL_NET > 0", loop[max(0, net_at - 80):net_at])
        self.assertIn("OpexRoad1yRefleetMailNet(this, line, year);", loop)
        orders = uncomment(body("builder_road.nut", "OpexRoadRefleet"))
        pax_flags = orders.index('line.kind == "mail_pax"')
        net_flags = orders.index('line.kind == "mail_net"')
        self.assertLess(pax_flags, net_flags)
        self.assertIn("ROAD1Y_MAIL_ON_PAX", orders[max(0, pax_flags - 80):pax_flags])
        self.assertIn("ROAD1Y_MAIL_NET > 0", orders[max(0, net_flags - 80):net_flags])
        net_block = orders[net_flags:net_flags + 280]
        self.assertEqual(net_block.count("AIOrder.OF_FULL_LOAD_ANY | nonstopFlag"), 2)
        pax_block = orders[pax_flags:pax_flags + 180]
        self.assertEqual(pax_block.count("AIOrder.OF_NONE | nonstopFlag"), 2)

    def test_pair_site_trace_cash_and_line_table(self):
        region = uncomment(_region())
        for needle in (
            "AITownList()",
            "pop < 400",
            "GetLastMonthProduction(townId, mailCargo)",
            "prod < 27",
            "centerDist < 40 || centerDist > 130",
            "pop / 10000 + 1",
            "prodMin * 1000 - absDist",
            "local rad = 6;",
            "if (prod <= 0) continue;",
            "if (acc < 8) continue;",
            "AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW",
            "OpexRoadBfsPath(siteA.tile, siteB.tile, ROAD_MAX_TRACE_TILES, siteA.front, siteB.front)",
            "OpexRoadTrace(siteA.tile, siteB.tile, firstH)",
            "for (local k = 0; k < 2; k++)",
            "OpexRoad1yAStarTrace(siteA, siteB, ROAD_MAX_TRACE_TILES + 64)",
            "OpexRoadFindDepot(trace, siteA, siteB, true)",
            "cashReserve + estimated",
            "year == 1970 && cashReserve < 25000",
            "GetYear(AIDate.GetCurrentDate()) == 1970 && cashReserve < 25000",
            "AIRoad.BuildRoad(depotPlan.front, depotPlan.tile)",
            "AIRoad.BuildRoadDepot(depotPlan.tile, depotPlan.front)",
            "AIVehicle.CloneVehicle(depotTile, first, true)",
            "AIOrder.OF_FULL_LOAD_ANY | AIOrder.OF_NON_STOP_INTERMEDIATE",
            "siteDist < 40 || siteDist > 160",
            "stIdA != 65535 && stIdB != 65535",
            "stationA == 65535 || stationB == 65535",
            "have < 10 ? 30 : 100",
            "minWait < capacity",
            "movingCount <= 0",
            "capacity < 50 ? capacity : 50",
            "if (want > 4) want = 4;",
            "(ROAD1Y_FLEET_UNLOCK & 2) != 0 ? 10000 : (ROAD1Y_PAX_REFLEET ? 15000 : 25000)",
            "2 * catalog.costRoadTruckStop",
            "catalog.costRoadDepot",
            "2 * engine.price",
            'kind = "mail_net"',
            "road1yMailNetMonth = -1",
            "srcIndustry = -1",
            "dstIndustry = -1",
            "nStopsA = 1",
            "nStopsB = 1",
            'OpexDecide("ROAD1Y_MAIL_NET", fields)',
            "action=open",
            "action=refleet",
            "action=fail",
            "ROAD1Y_MAIL_NET_OPEN_YM",
        ):
            self.assertIn(needle, region, needle)
        self.assertNotIn("parentLineId", region)
        self.assertNotIn("OpexRoadSites(", region)
        self.assertNotIn("OpexBuildRoadRoute(", region)
        self.assertNotIn("OpexRoad1yFindMailSite(", region)
        self.assertNotIn("frontA", region)
        self.assertIn("OpexRoad1yMailActivePairs(ai)", body("bus_districts.nut", "OpexRoad1yMailStep"))
        self.assertIn("OpexRoad1yMailActivePairs(ai)", body("bus_districts.nut", "OpexRoad1yMailNetStep"))
        build = uncomment(body("bus_districts.nut", "OpexRoad1yBuildMailNet"))
        self.assertNotIn("OpexRoadRollback", build[:build.index("OpexRoadBuildTrace")])
        self.assertLess(build.index("OpexRoadBuildTrace"), build.index("BuildDriveThroughRoadStation"))
        self.assertIn("reason=NO_DEPOT", build)
        self.assertIn("reason=RESERVE", build)

    def test_save_keeps_the_month_and_report_ignores_mail_net(self):
        persist = source("persist.nut")
        skip_start = persist.index("OPEX_SAVE_LINE_SKIP <- {")
        skip_end = persist.index("};", skip_start)
        self.assertNotIn("road1yMailNetMonth", persist[skip_start:skip_end])
        self.assertNotIn("mail_net", source("task_report.nut"))
        self.assertIn("local serializableLine = clone line;", body("persist.nut", "OpexSaveProjectLine"))

    def test_called_functions_exist_and_new_code_has_no_squirrel_hazards(self):
        region = uncomment(_region())
        for name, nargs in CALLS:
            declared = _arity(name)
            self.assertIsNotNone(declared, name)
            self.assertGreaterEqual(declared, nargs, name)
            self.assertIn(name + "(", region)
        for name in NEW_FUNCS:
            self.assertIn("function " + name + "(", source("bus_districts.nut"))
        for word in ("clone", "base", "par", "parent", "static"):
            self.assertNotRegex(region, r"\blocal\s+" + word + r"\b")
        self.assertNotIn("function(", region)
        self.assertNotIn(".find(", region)
        self.assertNotIn("yield", region)
        self.assertNotRegex(region, r"\btry\s*\{")


if __name__ == "__main__":
    unittest.main()
