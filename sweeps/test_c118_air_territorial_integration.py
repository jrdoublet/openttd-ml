#!/usr/bin/env python3
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
PROJECTS = (ROOT / "ai" / "OpexAI" / "projects.nut").read_text(encoding="utf-8")
TASK = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")


def function_block(source: str, name: str, next_name: str) -> str:
    start = source.index(f"function {name}")
    end = source.index(f"function {next_name}", start)
    return source[start:end]


class C118TerritorialIntegrationTests(unittest.TestCase):
    def test_c115_generation_remains_normal_policy(self):
        start = BUILDER.index("function OpexAirChooseRoutePlaneFull")
        c115 = BUILDER[BUILDER.index("if (C115_AIR_C100_CAPITAL_REPLAY", start) :]
        c115 = c115[: c115.index("return OpexC115ChooseRoutePlane") + 80]
        self.assertNotIn("!C118_AIR_TERRITORIAL_EXPANSION", c115)

    def test_territorial_chooser_uses_existing_c68_shadow(self):
        block = function_block(
            BUILDER, "OpexC118ChooseBuildPlan", "OpexAirChooseRoutePlaneFull"
        )
        self.assertIn('"c118C68Plane" in plan', block)
        self.assertIn('"c118C68Economics" in plan', block)

    def test_live_defensive_promotion_cannot_override_active_territorial_order(self):
        block = function_block(
            PROJECTS, "OpexPromoteLiveDefensiveAir", "OpexProjectAttemptKey"
        )
        self.assertIn("C118_AIR_PROJECT_SNAPSHOT.active", block)
        self.assertIn("return projects.best[0];", block)

    def test_last_territorial_project_still_gets_economic_tiebreak(self):
        block = function_block(
            BUILDER, "OpexC118ChooseBuildPlan", "OpexAirChooseRoutePlaneFull"
        )
        self.assertNotIn("if (nextCapital <= 0) return unchanged", block)
        self.assertIn("economics.profitAnnual > bestEconomics.profitAnnual", block)

    def test_unaffordable_c68_cannot_remain_selected(self):
        block = function_block(
            BUILDER, "OpexC118ChooseBuildPlan", "OpexAirChooseRoutePlaneFull"
        )
        self.assertIn("baselineAffordable", block)
        self.assertIn("finance > available", block)
        self.assertIn("if (bestPlane == null", block)

    def test_new_site_coverage_cache_depends_on_airport_type(self):
        self.assertIn('"c118AirportCoverageTowns_" + airportType', BUILDER)

    def test_instrumentation_reports_c68_and_chosen_engine(self):
        self.assertIn('"c118C68Plane" in plan', TASK)
        self.assertIn('"C118_DECISION date="', TASK)
        self.assertIn('"C118_COVERAGE date="', TASK)

    def test_c118_policy_and_probe_default_off(self):
        for setting in (
            "c118_air_territorial_expansion",
            "c118_air_coverage_probe",
        ):
            pos = INFO.index(f'name = "{setting}"')
            block = INFO[pos : pos + 500]
            self.assertIn("easy_value = 0, medium_value = 0, hard_value = 0", block)


if __name__ == "__main__":
    unittest.main()
