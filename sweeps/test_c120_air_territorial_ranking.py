from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROJECTS = (ROOT / "ai" / "OpexAI" / "projects.nut").read_text(encoding="utf-8")
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
TASK_AIR = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")
TASK_PROJECTS = (ROOT / "ai" / "OpexAI" / "task_projects.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")


def body(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


class TestC120AirTerritorialRanking(unittest.TestCase):
    def test_toggle_default_off_and_independent_from_c118(self):
        self.assertIn("C120_AIR_TERRITORIAL_RANKING <- false;", GLOBALS)
        self.assertIn(
            'C120_AIR_TERRITORIAL_RANKING = AIController.GetSetting("c120_air_territorial_ranking") != 0;',
            SETTINGS,
        )
        pos = INFO.index('name = "c120_air_territorial_ranking"')
        block = INFO[pos : pos + 650]
        for field in (
            "easy_value = 0",
            "medium_value = 0",
            "hard_value = 0",
            "custom_value = 0",
        ):
            self.assertIn(field, block)
        self.assertNotIn("c118_air_territorial_expansion", block)

    def test_new_towns_is_primary_lexicographic_key(self):
        reorder = body(
            PROJECTS,
            "function OpexC120ReorderAffordableAir",
            "function OpexC120TracePass",
        )
        self.assertIn("currentNew", reorder)
        self.assertIn("priorNew", reorder)
        self.assertIn("if (priorNew >= currentNew) break;", reorder)
        select = body(
            PROJECTS,
            "function OpexProjectSelectAffordable",
            "function OpexProjectSelectionScore",
        )
        self.assertIn("OpexC120ReorderAffordableAir(affordable);", select)
        self.assertLess(
            select.index("OpexC120ReorderAffordableAir(affordable);"),
            select.index("OpexC120FinalizeSelection(affordable, capitalBudget);"),
        )

    def test_equal_new_towns_falls_through_to_existing_c115_order(self):
        reorder = body(
            PROJECTS,
            "function OpexC120ReorderAffordableAir",
            "function OpexC120TracePass",
        )
        for forbidden in ("fundScore", "projectScore", "revenueAnnual", "roi", "profitAnnual"):
            self.assertNotIn(forbidden, reorder)
        self.assertIn("if (priorNew >= currentNew) break;", reorder)
        insert = body(
            PROJECTS,
            "function OpexProjectInsertDefensive",
            "function OpexPromoteLiveDefensiveAir",
        )
        self.assertNotIn("C120_AIR_TERRITORIAL_RANKING", insert)
        self.assertIn("local priorScore =", insert)
        self.assertIn("priorScore > projectScore", insert)
        self.assertIn("priorScore == projectScore && prior.revenueAnnual >= project.revenueAnnual", insert)

    def test_no_new_town_preserves_c115_fallback(self):
        reorder = body(
            PROJECTS,
            "function OpexC120ReorderAffordableAir",
            "function OpexC120TracePass",
        )
        self.assertIn("if (priorNew >= currentNew) break;", reorder)
        self.assertNotIn("fundScore", reorder)
        promote = body(
            PROJECTS,
            "function OpexPromoteLiveDefensiveAir",
            "function OpexProjectAttemptKey",
        )
        self.assertIn('("c120NewTowns" in projects.best[0]) && projects.best[0].c120NewTowns > 0', promote)

    def test_c120_keeps_normal_finance_and_profit_floor(self):
        prep = body(
            PROJECTS,
            "function OpexC120PrepareSelection",
            "function OpexC120FinalizeSelection",
        )
        self.assertIn("OpexProjectFinanceCapital(project)", prep)
        self.assertNotIn("c118MinFinance", prep)
        self.assertNotIn("OpexC116RouteFinanceCapital", prep)
        select = body(
            PROJECTS,
            "function OpexProjectSelectAffordable",
            "function OpexProjectSelectionScore",
        )
        self.assertNotIn("c120NewTowns > 0", select[select.index("local floorProfit") : select.index("local affordable")])
        self.assertNotIn("C120_AIR_TERRITORIAL_RANKING && project.mode", select)

    def test_engine_choice_path_is_exactly_existing_c115_c118_c116_path(self):
        build = body(
            TASK_AIR,
            "function OpexAI::_tryBuildAirProject",
            "function OpexAirFleetRefusal",
        )
        choice = build[build.index("local buildChoice") : build.index("local buildPlan")]
        self.assertIn("C118_AIR_TERRITORIAL_EXPANSION", choice)
        self.assertIn("OpexC118ChooseBuildPlan", choice)
        self.assertIn("OpexC116ChooseBuildPlan(this._catalog, plan)", choice)
        self.assertNotIn("C120", choice)

    def test_no_extra_engine_route_or_site_scan(self):
        prep = body(
            PROJECTS,
            "function OpexC120PrepareSelection",
            "function OpexC120FinalizeSelection",
        )
        annotation = body(PROJECTS, "function OpexProjectFromAir", "function OpexProjectFromWater")
        combined = prep + annotation
        for forbidden in (
            "airPlaneChoicesByAirport",
            "AIEngineList",
            "c118EngineChoices",
            "OpexAirPlans(",
            "OpexAirFindSite",
            "OpexAirSortedTowns",
            "AITownList",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertIn("OpexC118PlanCoverageTowns(project.payload, cargo)", prep)
        self.assertNotIn("c120TownIds", annotation)

    def test_real_catchment_defines_c120_new_towns(self):
        prep = body(
            PROJECTS,
            "function OpexC120PrepareSelection",
            "function OpexC120FinalizeSelection",
        )
        catchment = body(
            AIR,
            "function OpexC118StationCoverageTowns",
            "function OpexC118EngineFitsPlan",
        )
        self.assertIn("OpexC118OwnCoveredTownSet(cargo)", prep)
        self.assertIn("OpexC118PlanCoverageTowns(project.payload, cargo)", prep)
        self.assertIn("C120_AIR_TERRITORIAL_RANKING", catchment)
        self.assertIn("AITileList_StationCoverage", catchment)
        self.assertIn("AITile.GetCargoProduction", catchment)
        self.assertIn("AITile.GetClosestTown", catchment)
        self.assertNotIn("AITownList", catchment)

    def test_c120_never_promotes_air_over_other_modes_by_new_towns(self):
        insert = body(
            PROJECTS,
            "function OpexProjectInsertDefensive",
            "function OpexPromoteLiveDefensiveAir",
        )
        self.assertNotIn("C120_AIR_TERRITORIAL_RANKING", insert)
        reorder = body(
            PROJECTS,
            "function OpexC120ReorderAffordableAir",
            "function OpexC120TracePass",
        )
        self.assertIn("slots.append(i);", reorder)
        self.assertIn("airs.append(project);", reorder)
        self.assertIn("affordable[slots[i]] = airs[i];", reorder)
        self.assertIn('project.mode != "air"', reorder)
        self.assertNotIn("fundScore", reorder)
        self.assertIn("local priorScore =", insert)

    def test_coverage_cache_follows_persistent_site_cache_lifetime(self):
        reset = body(AIR, "function OpexAirResetSiteCache", "function OpexAirInvalidateCachedSite")
        invalidate = body(AIR, "function OpexAirInvalidateCachedSite", "function OpexFlightDistance")
        prepare = body(AIR, "function OpexAirPlansPrepare", "function OpexAirPlansFindSites")
        self.assertIn("AIR_TERRITORIAL_COVERAGE_CACHE.clear()", reset)
        self.assertIn("OpexAirResetTerritorialCoverageCache()", invalidate)
        self.assertNotIn("OpexAirResetTerritorialCoverageCache()", prepare)
        self.assertIn("OpexAirResetStationCoverageTownCache()", prepare)
        self.assertIn("stationCoverageTownCacheInit", prepare)

    def test_c120_telemetry_reuses_existing_revalidation_and_build_reasons(self):
        filt = body(
            PROJECTS,
            "function OpexFilterAirAlternativesStillValid",
            "function OpexProjectAttemptKey",
        )
        trace = body(
            PROJECTS,
            "function OpexC120TracePass",
            "function OpexProjectVehicleCount",
        )
        self.assertIn("C120_AIR_FILTER_SNAPSHOT", filt)
        self.assertIn("C120_SELECT date=", trace)
        for token in (
            "cash=",
            "available=",
            "airCandidates=",
            "territorial=",
            "bestNewTowns=",
            "bestCost=",
            "selectedNewTowns=",
            "selectedScore=",
            "stopReason=",
        ):
            self.assertIn(token, trace)
        for reason in (
            "batch_plan_dead",
            "siteA_unbuildable",
            "siteB_unbuildable",
            "insufficient_cash",
            "build_failed",
        ):
            self.assertIn(reason, TASK_AIR)
        self.assertIn("c75StopReason", TASK_PROJECTS)


if __name__ == "__main__":
    unittest.main()
