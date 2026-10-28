"""ROAD100-32: opt-in segmented LONG PAX corridor source contracts.

These tests do not replace the compulsory OpenTTD engine smoke: AITest
per-edge does not prove an entire route can actually be built.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def function(name, filename="builder_road.nut"):
    text = source(filename)
    start = text.index("function " + name + "(")
    end = text.find("\nfunction ", start + 10)
    return text[start:end if end >= 0 else len(text)]


class Road100SegmentedCorridor(unittest.TestCase):
    def test_explicit_optin_all_difficulties_and_road_only(self):
        info = source("info.nut")
        setting = re.search(
            r'name = "road100_segmented_corridor",(.*?)\n\s*\}\);',
            info, re.S,
        )
        self.assertIsNotNone(setting)
        for field in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(setting.group(1), rf"\b{field}\s*=\s*0\b")
        self.assertIn("AICONFIG_BOOLEAN", setting.group(1))
        self.assertIn("ROAD100_SEGMENTED_CORRIDOR <- false;", source("globals_pre.nut"))
        settings = source("settings.nut")
        block = settings.split("ROAD100_SEGMENTED_CORRIDOR =", 1)[1].split(";", 1)[0]
        for fragment in (
            'GetSetting("road100_segmented_corridor") == 1',
            "ROAD100_LONG_BUILD", "MODE_ROAD", "!MODE_AIR",
            "!MODE_RAIL", "!MODE_WATER",
        ):
            self.assertIn(fragment, block)

    def test_local_gaps_are_bounded_and_never_build(self):
        gap = function("OpexRoad100SegmentedGap")
        chain = function("OpexRoad100LongSegmentedTrace")
        self.assertIn("expansion < 80", gap)
        self.assertIn("score = newCost + 5 * AIMap.DistanceManhattan(next, target)", gap)
        self.assertIn("OpexOpsMeasureEnd(mark) >= limitOps - 55000", gap)
        self.assertIn("AreRoadTilesConnected", gap)
        self.assertIn("AITile.IsBuildable", gap)
        self.assertIn("next in occupied", gap)
        self.assertIn("gaps > 12", chain)
        self.assertIn("path.len() - 1 < 80 || path.len() - 1 > 190", chain)
        self.assertIn("OpexRoadOnDtAxis", chain)
        self.assertIn("out.trace = trace;", chain)
        for forbidden in ("AIRoad.BuildRoad(", "BuildRoadStation(", "BuildRoadDepot(",
                          "AIVehicle.Build", "GetCargoWaiting(", "Pathfinder."):
            self.assertNotIn(forbidden, gap + chain)

    def test_preflight_and_live_physically_funded_revalidation(self):
        build = function("OpexRoad100LongConstructPlan")
        self.assertIn("ROAD100_SEGMENTED_CORRIDOR ? -1 : 0", build)
        self.assertIn("OpexRoad100LongSegmentedTrace(pair.a, pair.b", build)
        self.assertIn("OpexRoad100LongVerifyTrace(trace, pair.a, pair.b", build)
        self.assertIn("OpexRoad100LongDepotPreflight(trace, pair.a, pair.b", build)
        self.assertIn("missing * catalog.costRoadPerTile * 3", build)
        self.assertIn("quoteTotal = capital + capital / 4 + 50000", build)
        self.assertIn("road100Segmented = shape == -1", build)
        self.assertIn('OpexDecide("ROAD100_SEGMENTED"', build)
        exact = source("opcode_exact.nut")
        self.assertIn('reason = "SEGMENT_DRIFT"', exact)
        self.assertIn("OpexRoad100LongTraceHash(longPlan.trace)", exact)
        self.assertIn("longPlan.roadQuoteCost > candidate.road100GenRoadQuote", exact)
        executor = function("OpexBuildRoadRoute")
        self.assertIn("OpexRoadBuildTrace(plan.trace, added)", executor)
        self.assertIn("OpexRoadRollback", executor)

    def test_demand_is_monthly_pax_not_producer_count(self):
        candidates = function("OpexRoad100LongBuildCandidate", "candidates.nut")
        self.assertIn("ROAD100_SEGMENTED_CORRIDOR", candidates)
        self.assertIn("OpexRoad100PaxSiteMonthly(preliminary.srcTown", candidates)
        self.assertIn("OpexRoad100PaxSiteMonthly(preliminary.dstTown", candidates)
        self.assertIn("monthly = unitsA.monthly + unitsB.monthly", candidates)
        self.assertIn("candidate.road100SegmentedUnits <- true", candidates)
        work = source("task_road.nut")
        self.assertIn("candidate.road100SegmentedUnits && ROAD100_SEGMENTED_CORRIDOR", work)
        self.assertIn("siteDemand = aUnits.monthly + bUnits.monthly", work)
        self.assertIn("siteDemand <= 0", work)
        self.assertIn("OpexRoad100LongQuotedEconomics(this._catalog, economics, plan)", work)
        estimator = function("OpexRoad100PaxSiteMonthly", "economy.nut")
        self.assertIn("out.townMonthly * usable", estimator)
        self.assertIn("out.townProducers", estimator)
        self.assertNotIn("GetCargoWaiting(", estimator)

    def test_po01c_and_synchronous_share_bounded_generator(self):
        candidate = source("candidates.nut")
        for fragment in (
            "function OpexRoad100SiteFirstGenerator(",
            "yield null;",
            "OpexRoad100LongConstructPlan(catalog, preliminaryLong,",
            "attemptLimit = 180000",
        ):
            self.assertIn(fragment, candidate)
        self.assertIn("OpexRoad100SiteFirstGenerator", source("po01c_regen.nut"))
        self.assertIn("OpexRoad100SiteFirstGenerator", candidate)


if __name__ == "__main__":
    unittest.main()
