"""ROAD100-30a: source contracts for dimensionally valid BUS site-first."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent / "ai" / "OpexAI"


def body(source, name):
    match = re.search(r"function\s+" + re.escape(name) + r"\s*\(", source)
    if not match:
        raise AssertionError(f"missing {name}")
    begin = source.index("{", match.end())
    level = 0
    for i in range(begin, len(source)):
        if source[i] == "{":
            level += 1
        elif source[i] == "}":
            level -= 1
            if level == 0:
                return source[begin : i + 1]
    raise AssertionError(f"unterminated {name}")


def site_monthly(town_monthly, site_producers, town_producers):
    """Python reference for the bounded fraction; NOT an engine measurement."""
    if town_monthly <= 0 or site_producers <= 0 or town_producers <= 0:
        return 0
    return town_monthly * min(site_producers, town_producers) // town_producers


class Road100PaxProducerUnits(unittest.TestCase):
    def test_reference_model_units_and_bounds(self):
        self.assertEqual(site_monthly(355, 18, 50), 127)
        self.assertEqual(site_monthly(327, 17, 52), 106)
        self.assertEqual(site_monthly(355, 500, 50), 355)
        self.assertEqual(site_monthly(355, 0, 50), 0)
        self.assertEqual(site_monthly(355, 50, 0), 0)
        self.assertEqual(site_monthly(0, 50, 50), 0)

    def test_optin_default_zero_roadonly_and_no_historical_baseline(self):
        info = (ROOT / "info.nut").read_text(encoding="utf8")
        setting = info.split('name = "road100_pax_producer_units"', 1)[1].split("});", 1)[0]
        self.assertIn("easy_value = 0, medium_value = 0, hard_value = 0", setting)
        self.assertIn("custom_value = 0", setting)
        settings = (ROOT / "settings.nut").read_text(encoding="utf8")
        line = settings.split("ROAD100_PAX_PRODUCER_UNITS =", 1)[1].split(";", 1)[0]
        for term in (
            'GetSetting("road100_pax_producer_units") == 1',
            "ROAD100_SITE_FIRST",
            "!ROAD100_MULTICATCHMENT",
            "!ROAD100_LONG_BUILD",
            "MODE_ROAD",
            "!MODE_AIR",
            "!MODE_RAIL",
            "!MODE_WATER",
        ):
            self.assertIn(term, line)
        globals_source = (ROOT / "globals_pre.nut").read_text(encoding="utf8")
        self.assertIn("ROAD100_PAX_PRODUCER_UNITS <- false;", globals_source)

    def test_town_share_not_direct_producer_as_passengers(self):
        economy = (ROOT / "economy.nut").read_text(encoding="utf8")
        helper = body(economy, "OpexRoad100PaxSiteMonthly")
        for term in (
            "AITown.GetLastMonthProduction",
            "AITown.GetLocation",
            "AITile.GetCargoProduction(center, cargo, 1, 1, radius)",
            "producing.Valuate(AITile.GetCargoProduction, cargo, 1, 1, 0)",
            "fromTown.Valuate(AITile.GetClosestTown)",
            "fromTown.KeepValue(townId)",
            "if (usable > out.townProducers)",
            "out.monthly = (out.townMonthly * usable) / out.townProducers",
        ):
            self.assertIn(term, helper)
        self.assertNotIn("AIStation.GetCargoWaiting", helper)
        self.assertNotIn("AIIndustry.GetLastMonthProduction", helper)

    def test_same_site_model_at_preflight_generate_and_live(self):
        builder = (ROOT / "builder_road.nut").read_text(encoding="utf8")
        plan = body(builder, "OpexRoadPlanPaxVoirie")
        self.assertIn("if (ROAD100_PAX_PRODUCER_UNITS && candidate.kind == \"pax\")", plan)
        self.assertIn("OpexRoad100PaxSiteMonthly(", plan)
        self.assertIn("bestSitePlan.road100PaxUnitsMonthly <- monthly", plan)
        generator = body((ROOT / "candidates.nut").read_text(encoding="utf8"),
                         "OpexRoad100SiteFirstGenerator")
        self.assertIn("siteMonthly = plan.road100PaxUnitsMonthly", generator)
        self.assertIn("ROAD100_PAX_UNITS", generator)
        self.assertIn("candidate.road100PaxProducerUnits <- true", generator)
        task = (ROOT / "task_road.nut").read_text(encoding="utf8")
        self.assertIn('("road100PaxUnitsMonthly" in plan)', task)
        self.assertIn("? plan.road100PaxUnitsMonthly : -1", task)
        self.assertIn("phase=live", task)
        self.assertIn("ROAD100_PAX_UNITS", task)


if __name__ == "__main__":
    unittest.main()
