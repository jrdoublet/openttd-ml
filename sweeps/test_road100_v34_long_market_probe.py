"""ROAD100-34 pretrace market shadow: source and OFF contracts.

These do not replace an OpenTTD Squirrel runtime smoke.
"""
import re
import unittest
from pathlib import Path

from road100_off_projection import off_source, ROOT


AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class LongMarketProbeContracts(unittest.TestCase):
    def test_default_off_at_four_difficulties_and_strict_road_only(self):
        info = source("info.nut")
        found = re.search(r'name = "road100_long_market_probe",(.*?)\n\s*\}\);',
                          info, re.S)
        self.assertIsNotNone(found)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertRegex(found.group(1), rf"\b{diff}_value\s*=\s*0\b")
        self.assertIn("AICONFIG_BOOLEAN", found.group(1))
        self.assertIn("ROAD100_LONG_MARKET_PROBE <- false;", source("globals_pre.nut"))
        setting = source("settings.nut").split(
            "ROAD100_LONG_MARKET_PROBE =", 1)[1].split(";", 1)[0]
        for guard in ('GetSetting("road100_long_market_probe") == 1',
                      "ROAD100_LONG_BUILD", "MODE_ROAD", "!MODE_AIR",
                      "!MODE_RAIL", "!MODE_WATER"):
            self.assertIn(guard, setting)

    def test_pretrace_shadow_uses_real_monthly_unit_conversion(self):
        builder = source("builder_road.nut")
        construct = builder[builder.index("function OpexRoad100LongConstructPlan("):]
        start = construct.index("if (ROAD100_LONG_MARKET_PROBE && shortlist.len() > 0)")
        end = construct.index('reason = "NO_PAIR";', start)
        block = construct[start:end]
        self.assertLess(start, construct.index("foreach (pair in shortlist)"))
        for requirement in (
            "OpexRoad100PaxSiteMonthly(candidate.srcTown",
            "OpexRoad100PaxSiteMonthly(candidate.dstTown",
            "rootA.siteProducers", "rootB.siteProducers",
            "rootA.townProducers", "rootB.townProducers",
            "rootA.townMonthly", "rootB.townMonthly",
            "rootA.monthly", "rootB.monthly",
            'OpexDecide("ROAD100_LONG_MARKET"',
        ):
            self.assertIn(requirement, block)
        for forbidden in (
            "GetCargoWaiting(", "GetProfit", "route.profit",
            "AIRoad.BuildRoad(", "BuildDriveThroughRoadStation(",
            "AIVehicle.Build", "OpexApplyRoadEconomics(",
            "shortlist.insert", "selectedPlan =", "road100LongCashNeed",
        ):
            self.assertNotIn(forbidden, block)

    def test_shadows_at_most_three_pairs_and_six_root_measurements(self):
        builder = source("builder_road.nut")
        self.assertIn("if (at >= 3) continue;", builder)
        self.assertIn("if (shortlist.len() > 3) shortlist.pop();", builder)
        self.assertIn("marketRank < shortlist.len()", builder)
        self.assertIn("marketPair.a.tile in marketCacheA", builder)
        self.assertIn("marketPair.b.tile in marketCacheB", builder)
        self.assertIn("marketCacheA.rawset(marketPair.a.tile, rootA)", builder)
        self.assertIn("marketCacheB.rawset(marketPair.b.tile, rootB)", builder)
        self.assertIn("OpexOpsMeasureEnd(mark) >= limitOps - 100000", builder)
        self.assertIn("reason=OPCAP", builder)

    def test_exact_off_projection_and_idempotence(self):
        for name in ("builder_road.nut", "settings.nut", "info.nut",
                     "globals_pre.nut"):
            with self.subTest(name=name):
                current = source(name)
                off = off_source(name, current)
                self.assertNotEqual(current, off)
                self.assertEqual(off_source(name, off), off)


if __name__ == "__main__":
    unittest.main()
