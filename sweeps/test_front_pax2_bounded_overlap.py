"""FRONT-PAX-2 bounded passenger AIR overlap: offline arithmetic and contracts.

These host tests deliberately do not claim Squirrel compilation or profitability.
No Docker, path search or economic simulation is involved.
"""

import math
import re
import unittest
from pathlib import Path

from n75_mc_legacy import historical_bytes, historical_info


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def body(text, name):
    start = text.index("function " + name + "(")
    brace = text.index("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if not depth:
                return text[start:index + 1]
    raise AssertionError("unterminated: " + name)


def physical_boundary(rail_speed, plane_speed, wagon_capacity=40,
                      airport_width=6, airport_height=6, rail_min=7,
                      air_min=200, dwell_pct=100,
                      other_width=None, other_height=None):
    """Independent reference for candidate-time math; absent values fail closed."""
    if min(rail_speed, plane_speed, wagon_capacity) <= 0:
        return None
    tau_rail = 1 / (0.036 * rail_speed)
    tau_air = 1 / (0.036 * plane_speed)
    if tau_rail <= tau_air:
        return None
    taxi = min(plane_speed, 50)
    if other_width is None:
        other_width = airport_width
    if other_height is None:
        other_height = airport_height
    ground = (airport_width + airport_height + other_width + other_height) * (2 / 3)
    ground_days = ground * 4096 / (74 * 1.6 * taxi) + 300 / 74
    dwell = (2 * 40 * math.ceil(wagon_capacity / 5) / 74) * dwell_pct / 100
    threshold = max(rail_min, math.ceil(max(0, ground_days + 1 / 74 - dwell)
                                        / (tau_rail - tau_air)))
    return threshold if threshold < air_min else None


def physical_pair_wins(rail_speed, plane_speed, wagon_capacity, manhattan,
                       flight_distance, ground_days, dwell_pct=100):
    rail = manhattan / (0.036 * rail_speed)
    rail += 2 * 40 * math.ceil(wagon_capacity / 5) / 74 * dwell_pct / 100
    air = flight_distance / (0.036 * plane_speed) + ground_days + 1 / 74
    return air <= rail


class TestFrontPax2BoundedOverlap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = source("settings.nut")
        cls.info = source("info.nut")
        cls.globals = source("globals_pre.nut")
        cls.candidates = source("candidates.nut")
        cls.planning = source("air_planning.nut")
        cls.choose = source("projects_selection.nut")
        cls.task_air = source("task_air.nut")

    def test_setting_off_every_difficulty_and_only_one_getter(self):
        blocks = re.findall(
            r'AddSetting\(\{ name = "front_pax2_bounded_overlap",(.*?)\}\);',
            self.info, flags=re.S)
        self.assertEqual(len(blocks), 1)
        self.assertIn("min_value = 0, max_value = 2", blocks[0])
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(blocks[0], rf"{level}_value\s*=\s*0\b")
        self.assertIn("FRONT_PAX2_BOUNDED_OVERLAP <- 0;", self.globals)
        self.assertEqual(self.settings.count(
            'GetSetting("front_pax2_bounded_overlap")'), 1)
        self.assertIn("(fp2Overlap == 1 || fp2Overlap == 2)", self.settings)

    def test_legacy_byte_inventory_unchanged(self):
        self.assertEqual(historical_info(self.info).count("AddSetting("), 58)
        for filename in ("settings.nut", "info.nut"):
            stripped = historical_bytes(filename, (AI / filename).read_bytes())
            self.assertNotIn(b"front_pax2_bounded_overlap", stripped)

    def test_illustrative_time_crossing_and_ceiling(self):
        # Physique 6x6, wagon PASS 40, rail 115, avion API 570.
        self.assertEqual(physical_boundary(115, 570), 34)
        self.assertLess(33.0, physical_boundary(115, 570))
        self.assertIsNone(physical_boundary(115, 570, air_min=34))
        self.assertEqual(physical_boundary(115, 570, dwell_pct=0), 79)
        self.assertIsNone(physical_boundary(115, 570, rail_min=200))

    def test_nonpositive_denominator_or_missing_motor(self):
        for args in ((120, 120), (140, 80), (0, 570), (115, 0)):
            with self.subTest(args=args):
                self.assertIsNone(physical_boundary(*args))
        function = body(self.candidates, "OpexFP2PhysicalBoundary")
        self.assertIn("tauRail <= tauAir", function)
        self.assertIn("return -1", function)
        self.assertIn("first.tofloat() < crossing", function)

    def test_mixed_hub_airport_types_not_replaced_by_combo_type(self):
        large_both = physical_boundary(115, 570)
        mixed = physical_boundary(115, 570, other_width=4, other_height=3)
        self.assertLess(mixed, large_both)
        self.assertEqual(mixed, 22)
        boundary = body(self.candidates, "OpexFP2PhysicalBoundary")
        self.assertIn("GetAirportWidth(typeA)", boundary)
        self.assertIn("GetAirportHeight(typeB)", boundary)
        shortlist = body(self.planning, "OpexFP2Shortlist")
        self.assertIn("AIAirport.GetAirportType(siteA.anchor)", shortlist)
        self.assertIn("AIAirport.GetAirportType(siteB.anchor)", shortlist)
        self.assertIn("typeA + \"|\" + typeB", shortlist)
        self.assertIn("OpexC100AirManeuverDays(plane.id, typeA, typeB)", shortlist)
        self.assertIn("OpexFP2PhysicalBoundary(fp.bounds, plane.speed,", shortlist)

    def test_actual_flight_geometry_is_checked_as_second_filter(self):
        tau_rail = 1 / (0.036 * 115)
        tau_air = 1 / (0.036 * 570)
        ground_days = 16 * 4096 / (74 * 1.6 * 50) + 300 / 74
        self.assertGreater(tau_rail, tau_air)
        self.assertTrue(physical_pair_wins(115, 570, 40, 60, 60, ground_days))
        self.assertFalse(physical_pair_wins(115, 570, 40, 60, 450, ground_days))
        code = body(self.candidates, "OpexFP2PhysicalPairWins")
        self.assertIn("flightDistance.tofloat()", code)
        self.assertIn("manhattan.tofloat()", code)
        self.assertNotIn("GetAirportWidth", code)  # combo cached, no API per pair

    def test_shadow_shortlist_has_no_mutating_economics_or_site_checks(self):
        code = body(self.planning, "OpexFP2Shortlist")
        for forbidden in ("OpexC121CatalogChoice(", "AITestMode(", "OpexAirSiteStillBuildable(",
                          "OpexProjectFromAir(", "OpexAvailableCapital(",
                          "OpexAirFindSite(", "OpexAirStoreRoutePlan("):
            self.assertNotIn(forbidden, code)
        self.assertEqual(code.count("fp.slots[arm] ="), 1)
        self.assertIn("fp.eligible[arm]++", code)
        self.assertIn("previous.key == key", code)
        self.assertIn("score == previous.score && key < previous.key", code)

    def test_rejection_only_with_three_arms_and_no_new_scan(self):
        for marker, arm in (
            ("sites[a], sites[b]", "0"), ("hub, site", "1"), ("hub1, hub2", "2")
        ):
            self.assertRegex(self.planning, rf"if \(!OpexAirPairInBand\([\s\S]*?"
                             rf"OpexFP2Shortlist\(ctx, {arm}, {re.escape(marker)}")
        self.assertEqual(self.planning.count("if (ctx.fp2 != null) OpexFP2Shortlist(ctx,"), 3)
        init = body(self.planning, "OpexAirPlans")
        self.assertIn("if (FRONT_PAX2_BOUNDED_OVERLAP > 0 && paxBand == PAX_BAND_ALL", init)
        self.assertIn("catalog.bounds != null", init)
        self.assertIn("fp2 = null", init)
        self.assertNotIn("OpexFP2Shortlist(", init)  # only original three pair loops

    def test_on_is_bounded_three_c121_calls_and_real_finance(self):
        final = body(self.planning, "OpexFP2Finalize")
        self.assertIn("for (local arm = 2; arm >= 0; arm--)", final)
        self.assertEqual(final.count("OpexC121CatalogChoice("), 1)
        self.assertIn("FRONT_PAX2_BOUNDED_OVERLAP == 2", final)
        for required in ("OpexAirSiteStillBuildable(", "OpexProjectFromAir(",
                         "OpexProjectFinanceCapital(", "OpexAvailableCapital()",
                         "OpexAirStoreRoutePlan(", "candidate.pair in used"):
            self.assertIn(required, final)
        self.assertIn("economics.oneWayDays", final)
        self.assertIn("OpexAirReserveJoinedStops", final)
        self.assertIn('c83OwnSecondSlotA = !reuseA && ("c83OwnSecondSlot" in candidate.siteA)', final)
        self.assertIn('c83OwnSecondSlotB = !reuseB && ("c83OwnSecondSlot" in candidate.siteB)', final)
        self.assertEqual(final.count('OpexDecide("FRONT_PAX2_BOUNDED"'), 1)

    def test_selection_and_successful_construction_identified(self):
        self.assertIn('OpexDecide("FRONT_PAX2_TOPK"', self.choose)
        self.assertIn('realSelection && FRONT_PAX2_BOUNDED_OVERLAP == 2', self.choose)
        final = body(self.planning, "OpexFP2Finalize")
        self.assertIn("plan.frontPax2Id <- candidate.key;", final)
        self.assertIn("plan.frontPax2Scan <-", final)
        self.assertIn('" fp2=" + plan.frontPax2Id', self.task_air)
        self.assertIn('OpexDecide("PROJECT_CHOSEN"', self.task_air)
        self.assertIn('OpexDecide("AIR_BUILD"', self.task_air)
        self.assertIn('if (result.ok)', self.task_air)

    def test_resume_memory_and_save_load_do_not_replay_commits(self):
        driver = body(self.planning, "OpexAirPlans")
        final = body(self.planning, "OpexAirPlansFinalize")
        prepare = body(self.planning, "OpexAirPlansPrepare")
        self.assertLess(driver.index("if (!prepared)"), driver.index("OpexFP2NewShortlist("))
        self.assertIn('resumeState.frontPax2Bounded <- ctx.fp2;', driver)
        self.assertIn('resumeState.frontPax2Bounded;', driver)
        self.assertIn("if (resumeState.done)", prepare)
        self.assertIn("if (ctx.fp2 != null) OpexFP2Finalize(ctx);", final)
        self.assertIn("delete ctx.resumeState.frontPax2Bounded", final)
        self.assertNotIn("frontPax2Bounded", source("persist.nut"))

    def test_old_epoch_shortlist_cannot_activate_after_catalog_refresh(self):
        shortlist = body(self.planning, "OpexFP2Shortlist")
        final = body(self.planning, "OpexFP2Finalize")
        self.assertIn("if (ctx.catalog.bounds != fp.bounds) return;", shortlist)
        self.assertIn("AIDate.GetYear(AIDate.GetCurrentDate()) != fp.bounds.year", final)
        self.assertIn('result = "stale_scan";', final)
        self.assertIn("&& stale", final)

    def test_existing_rail_and_freight_filters_remain_exact(self):
        rail_band = body(self.candidates, "OpexRailPaxPairInBand")
        self.assertIn("distance <= bounds.railMax", rail_band)
        self.assertNotIn("FRONT_PAX2", rail_band)
        freight = body(self.candidates, "OpexFreightCandidates")
        self.assertNotIn("OpexFP2", freight)
        copies = source("po01c_generators.nut")
        self.assertNotIn("frontPax2Bounded",
                         body(copies, "OpexPO01CFreightCandidates"))
        self.assertIn("frontPax2Bounded", body(copies, "OpexPO01CAirPlans"))


if __name__ == "__main__":
    unittest.main()
