"""Contrats statiques ciblés B7/10.1, B7/10.2 et B7/10.3."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LIB = (ROOT / "ai" / "OpexAI" / "lib_water.nut").read_text(encoding="utf-8")
BUILDER = (ROOT / "ai" / "OpexAI" / "builder_water.nut").read_text(encoding="utf-8")


def body(source: str, signature: str, next_signature: str) -> str:
    start = source.index(signature)
    end = source.index(next_signature, start)
    return source[start:end]


class B7WaterGuardsTest(unittest.TestCase):
    def test_lakes_budget_reaches_findpath_helpers(self):
        find_path = body(
            LIB,
            "function _MinchinWeb_Lakes_::FindPath(iterations)",
            "function _MinchinWeb_Lakes_::GetPathLength()",
        )
        all_groups = body(
            LIB,
            "function _MinchinWeb_Lakes_::_AllGroups(StartGroupArray)",
            "function _MinchinWeb_Lakes_::_AddNeighbour(NextTile)",
        )
        add_neighbour = body(
            LIB,
            "function _MinchinWeb_Lakes_::_AddNeighbour(NextTile)",
            "/* == Marine",
        )
        self.assertIn(
            "this._opsMark = WATER_LAKES_OPS_BUDGET ? OpexOpsMeasureBegin() : null",
            find_path,
        )
        self.assertGreaterEqual(find_path.count("this._OpsBudgetExceeded()"), 4)
        self.assertIn("this._OpsBudgetExceeded()", all_groups)
        self.assertIn("return null", all_groups)
        self.assertGreaterEqual(add_neighbour.count("this._OpsBudgetExceeded()"), 3)
        self.assertIn("if (ConnectedGroups == null) return null", add_neighbour)
        self.assertIn("if (AddedNeighbours == null)", find_path)
        self.assertIn("_BudgetedMinDistance", find_path)

    def test_lakes_bfs_preflight_is_before_first_real_dock(self):
        build = body(
            BUILDER,
            "function OpexBuildWaterRoute(catalog, budget, plan)",
            "/* Une ligne eau ne porte qu'un navire.",
        )
        first_build = build.index("AIMarine.BuildDock(plan.siteA.dock")
        preflight = build.index("OpexWaterFindConnection(preflightA, preflightB)")
        self.assertLess(preflight, first_build)
        post_real = build.index("OpexWaterFindConnection(realA, realB)")
        legacy_guard = build.rfind("!WATER_LAKES_CONNECTIVITY", 0, post_real)
        self.assertGreater(legacy_guard, first_build)
        prefix = build[:first_build]
        self.assertIn('result.reason = "NOWATER"', prefix)
        self.assertNotIn("OpexWaterRollback", prefix)

    def test_lakes_unknown_distance_is_rejected_before_economics(self):
        fallback = BUILDER.index("if (navigableDistance < 0) {")
        economics = BUILDER.index("OpexWaterEconomics(", fallback)
        block = BUILDER[fallback:economics]
        self.assertIn("profile.lakes_fallback_navigable++", block)
        self.assertIn("continue;", block)
        self.assertNotIn("navigableDistance = tariffDistance", block)

    def test_lakes_distance_fallback_fails_closed(self):
        plans = body(
            BUILDER,
            "function OpexWaterPlans(catalog, lines = null, projects = null, profile = null,",
            "function OpexBuildWaterRoute(catalog, budget, plan)",
        )
        fallback = plans.index("if (navigableDistance < 0) {")
        economics = plans.index("OpexWaterEconomics(", fallback)
        block = plans[fallback:economics]
        self.assertIn("profile.lakes_fallback_navigable++", block)
        self.assertIn("continue;", block)
        self.assertNotIn("navigableDistance = tariffDistance", block)


if __name__ == "__main__":
    unittest.main()
