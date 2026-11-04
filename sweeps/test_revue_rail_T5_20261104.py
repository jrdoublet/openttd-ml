"""Revue rail T5 (plans de gare et de quai) — 04/11/2026.

Mesure seule, sans effet au défaut : sous decision_log, la ligne RAIL_BUILD
porte len_a/len_b et back_a/back_b (arrière de quai libre et plat à la pose,
critère exact du back_lead de RAIL-LOOP). Les contrats ci-dessous documentent
aussi les constats T5-01 à T5-03 sans changer le code de décision.
Tests de source uniquement : le Squirrel ne se compile pas ici.
"""

import re
import sys
import unittest
from pathlib import Path

SWEEPS = Path(__file__).resolve().parent
sys.path.insert(0, str(SWEEPS))

from revue_rail_t5_off import MARKERS, REPLACED, off_source  # noqa: E402
from test_rail_loop_20261104 import function_body, global_signatures, read, strip_squirrel  # noqa: E402


class RailBuildBackInstrumentation(unittest.TestCase):
    def setUp(self):
        self.body = function_body(read("task_rail.nut"), "OpexAI::_recordRailAttempt")

    def test_fields_only_inside_decision_log_and_success(self):
        guard = self.body.index("if (DECISION_LOG) {\n    local p2Trace = OpexP2RailTraceKey(candidate);")
        build = self.body.index('OpexDecide("RAIL_BUILD", "line="')
        back = self.body.index('" back_a=" + (OpexRailLoopBackPlan(result.platformA) != null ? 1 : 0)')
        fail = self.body.index('OpexDecide("RAIL_BUILD_FAIL"')
        self.assertLess(guard, build)
        self.assertLess(build, back)
        self.assertLess(back, fail)

    def test_platforms_are_guarded_before_use(self):
        hunk = REPLACED["task_rail.nut"][0][0]
        self.assertIn('(("platformA" in result) && result.platformA != null', hunk)
        self.assertIn('&& ("platformB" in result) && result.platformB != null)', hunk)
        self.assertLess(hunk.index('"platformB" in result'), hunk.index("result.platformB.length"))

    def test_back_criterion_is_the_rail_loop_one(self):
        sigs = global_signatures()
        self.assertIn((1, 1), sigs["OpexRailLoopBackPlan"])
        back = function_body(read("rail_loop.nut"), "OpexRailLoopBackPlan")
        self.assertIn("!AITile.IsBuildable(backLead)", back)
        self.assertIn("AITile.GetSlope(backLead) != AITile.SLOPE_FLAT", back)
        self.assertIn('if (reject == "" && backA == null) reject = "back_lead_A";', read("rail_loop.nut"))

    def test_p2_contract_kept(self):
        self.assertIn('" pred_revenue2=" + candidate.revenue2 : "") + p2Trace', self.body)

    def test_no_reserved_word_or_closure(self):
        hunk = strip_squirrel(REPLACED["task_rail.nut"][0][0])
        self.assertIsNone(re.search(r"\b(clone|base)\b", hunk))
        self.assertIsNone(re.search(r"function\s*\(", hunk))


class PlatformFindingsDocumented(unittest.TestCase):
    """Constats non corrigés : ils changeraient des choix de jeu (opt-in + portes)."""

    def test_t5_01_platform_follows_economic_wagons(self):
        catalog = read("catalog.nut")
        self.assertIn("const RAIL_PLATFORM_GROWTH_WAGONS = 2;", catalog)
        self.assertIn("return (wagons + 2) / 2;", catalog)
        economy = read("economy.nut")
        self.assertIn("const STATION_RATING_PCT = 50;", economy)
        self.assertIn("local wagons = OpexCeilDiv(calibrationOffered, wagon.capacity * referenceTrips);", economy)
        plans = function_body(read("builder_rail.nut"), "OpexRailPlatformPlans")
        self.assertIn("for (local length = wanted; length >= floor; length--) {", plans)

    def test_t5_02_station_plans_ignore_platform_rear(self):
        plans = function_body(read("builder_rail.nut"), "OpexStationPlans")
        self.assertIn("local lead = sign > 0 ? stationExit + step : stationExit - step;", plans)
        self.assertNotIn("back", strip_squirrel(plans).lower())

    def test_t5_03_rail_open_join_refusal_returns_site_reason(self):
        plans = function_body(read("builder_rail.nut"), "OpexRailPlatformPlans")
        skip = plans.index('"phase=skip_fallback reason=cash_or_profit"')
        self.assertIn("reason = OpexRailSiteReason(joinHasA, joinHasB),", plans[skip:skip + 600])
        record = function_body(read("task_rail.nut"), "OpexAI::_recordRailAttempt")
        self.assertIn('result.reason == "SITEA" || result.reason == "SITEB"', record)
        self.assertIn("this._markPairAbandoned(OpexAbandonedPairKey(candidate));", record)
        self.assertIn("Un refus n'est pas un abandon de la paire", read("builder_rail.nut"))


class RevueT5OffProjection(unittest.TestCase):
    def test_projection_restores_historic_log_and_is_idempotent(self):
        source = read("task_rail.nut")
        projected = off_source("task_rail.nut", source)
        new, old = REPLACED["task_rail.nut"][0]
        self.assertIn(old, projected)
        for marker in MARKERS:
            self.assertNotIn(marker, projected)
        self.assertEqual(off_source("task_rail.nut", projected), projected)

    def test_other_modules_unchanged(self):
        for name in ("builder_rail.nut", "rail_loop.nut", "economy.nut", "catalog.nut"):
            with self.subTest(name=name):
                self.assertEqual(off_source(name, read(name)), read(name))

    def test_partial_or_duplicated_hunk_fails_closed(self):
        source = read("task_rail.nut")
        with self.assertRaises(AssertionError):
            off_source("task_rail.nut", source.replace('" back_b=" + (', '" back_b=" + ((', 1))
        with self.assertRaises(AssertionError):
            off_source("task_rail.nut", source + REPLACED["task_rail.nut"][0][0])

    def test_chain_head_strips_t5_first(self):
        chain = (SWEEPS / "invest_stall_diagnostic_off.py").read_text(encoding="utf8")
        self.assertLess(chain.index("revue_rail_t5_off"), chain.index("rail_keep_off"))


if __name__ == "__main__":
    unittest.main()
