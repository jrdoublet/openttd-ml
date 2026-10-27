"""Production integration and conserved spiral budgets, plus V3 cost semantics."""
import json
from pathlib import Path
import unittest

from test_air_site_funnel import body
from test_diag_air_site_probe import ReaderTests

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"


class RankedContracts(unittest.TestCase):
    def test_off_preserves_preexisting_settings_and_default(self):
        info = (AI / "info.nut").read_text()
        from campaign_freeze import effective_ai_settings
        settings = effective_ai_settings(AI / "info.nut", ())["effective"]
        self.assertEqual(settings["air_site_ranked"], 1)
        self.assertEqual(settings["air_site_funnel"], 1)
        deltas = json.loads((ROOT / "sweeps/fixtures/air_site_ranked_off_deltas.json").read_text())
        from air_site_ranked_legacy import off_source
        for name in deltas:
            text = (AI / name).read_text()
            self.assertNotIn(deltas[name]["marker"], off_source(name, text))
        block = info[info.index('name = "air_site_ranked"'):].split('});')[0]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{level}_value = 1", block)

    def test_real_generator_uses_same_dispatcher_only_when_on(self):
        code = (AI / "air_site_ranked.nut").read_text()
        install = body(code, "function OpexAirRankedInstall(")
        self.assertIn("::OpexAirFindSiteCatchmentListed <- OpexAirRankedListed", install)
        self.assertIn("::OpexPO01CAirFindSite <- OpexPO01CAirRankedFindSite", install)
        adapter = body(code, "function OpexPO01CAirRankedFindSite(")
        self.assertIn("yield null", adapter)
        self.assertIn("result.value = OpexAirFindSite(", adapter)
        settings = (AI / "settings.nut").read_text()
        self.assertEqual(settings.count('GetSetting("air_site_ranked")'), 1)
        self.assertIn('if (AIR_SITE_RANKED > 0) {\n    require("air_site_ranked.nut");', settings)
        for name in ("main.nut", "globals_post.nut", "persist.nut"):
            self.assertNotIn('require("air_site_ranked.nut")', (AI / name).read_text())

    def test_fallback_is_original_c96_with_only_budget_initialization_removed(self):
        original = body((AI / "air_sites.nut").read_text(), "function OpexAirFindSiteCatchmentListed(")
        expected = original[original.index('  local w = airport.width;'):]
        actual = body((AI / "air_site_ranked.nut").read_text(), "function OpexAirRankedSpiralRest(")
        self.assertEqual(actual[actual.index('  local w = airport.width;'):], expected)
        self.assertNotIn("townsLeft--", actual)
        self.assertNotIn("local execLevels", actual)
        self.assertNotIn("local used", actual)

    def test_ranked_search_keeps_native_predicate_and_shared_limits(self):
        code = (AI / "air_site_ranked.nut").read_text()
        search = body(code, "function OpexAirRankedListed(")
        self.assertIn("[[4, 14], [15, AIR_SITE_RADIUS]]", search)
        self.assertIn("OpexAirRankedCheapOk(anchor, airport)", search)
        self.assertIn("if (cap > 12) cap = 12", search)
        self.assertEqual(search.count("probes.townsLeft--"), 1)
        self.assertIn("useSiteCache, allowance, used, levels)", search)
        admission = body(code, "function OpexAirRankedProbe(")
        self.assertIn("execLevels < 3", admission)
        self.assertIn("OpexAirCanLevelFootprint(anchor, airport, town.id)", admission)
        self.assertNotIn("AIR_PROBE", code)

    def test_oracle_filters_dead_catchment_and_breaks_ties_on_cost(self):
        code = (AI / "air_site_probe.nut").read_text()
        oracle = body(code, "function OpexAirProbeOracle(")
        self.assertIn("result.admitted != 1 || result.catchment != 1", oracle)
        self.assertIn("score == bestScore", oracle)
        self.assertIn("result.total_quote < bestCost", oracle)
        measure = body(code, "function OpexAirProbeBuild(")
        self.assertLess(measure.index("AITestMode()"), measure.index("BuildAirport("))
        self.assertIn("AITile.LevelTiles(anchor, endTile)", measure)
        self.assertIn("AIAccounting()", measure)
        self.assertIn("quote_exact = 0", measure)

    def test_leveling_checks_every_changed_corner_and_shared_cache_path(self):
        code = (AI / "air_site_ranked.nut").read_text()
        check = body(code, "function OpexAirRankedCanLevelFootprint(")
        moving = body(code, "function OpexAirRankedMovingCorners(")
        boundary = body(code, "function OpexAirRankedBoundaryClear(")
        self.assertIn("(airport.width + 1) * (airport.height + 1)", moving)
        self.assertIn("corners.Valuate(AITile.GetCornerHeight, AITile.CORNER_N)", moving)
        self.assertIn("corners.RemoveValue(AITile.GetCornerHeight(anchor, AITile.CORNER_N))", moving)
        self.assertIn("abs(height - target) > 1", check)
        self.assertIn("AITile.RaiseTile(tile, AITile.SLOPE_N)", check)
        self.assertIn("AITile.LowerTile(tile, AITile.SLOPE_N)", check)
        self.assertIn("reason=changed_border", boundary)
        self.assertIn("rx < airport.width && ry < airport.height) continue", boundary)
        self.assertLess(check.index("AITestMode()"), check.index("AITile.RaiseTile"))
        self.assertLess(check.index("AIAccounting()"), check.index("AITile.RaiseTile"))
        self.assertIn("::OpexAirCanLevelFootprint <- OpexAirRankedCanLevelFootprint", code)
        # A failed atomic move must return false even if the aggregate succeeds.
        failure = check[check.index("if (ok) continue;"):]
        self.assertLess(failure.index("bulk_ok="), failure.index("return false;"))
        self.assertNotIn("return bulkOk", failure)
        probe = body((AI / "air_site_probe.nut").read_text(), "function OpexAirProbeMethod(")
        self.assertIn("::OpexAirCanLevelFootprint <- OpexAirRankedOriginalCanLevel", probe)

    def test_engine_partial_success_regression_model(self):
        # CmdLevelLand's had_success is ANY successful move, not ALL moves.
        for corner_results, expected in (([True, True], True), ([True, False], False),
                                         ([False, True], False), ([False], False)):
            bulk_success = any(corner_results)
            complete = all(corner_results)
            self.assertEqual(complete, expected)
            if corner_results in ([True, False], [False, True]):
                self.assertTrue(bulk_success)  # the original false positive


class LevelingReaderTests(ReaderTests):
    # The inherited fixtures also run every fail-closed comparison contract.
    def test_263_levelable_is_admitted_not_a_missing_site(self):
        stats = self.result()["valid"]["by_method"]["initial"]
        self.assertEqual(stats["constructible_share"], 0)
        self.assertEqual(stats["admitted_share"], 1)
        self.assertEqual(stats["feasible_ratio_median"], 1.5)
        self.assertEqual(stats["estimated_total_n"], 1)
        self.assertEqual(stats["total_quote_median"], 1100)

    def test_unknown_cost_stays_unknown(self):
        text = self.texts["initial"].replace("total_quote=1100", "total_quote=null")
        stats = self.result({**self.texts, "initial": text})["valid"]["by_method"]["initial"]
        self.assertIsNone(stats["total_quote_median"])
        self.assertEqual(stats["total_quote_n"], 0)

    def test_partial_bulk_leveling_is_visible_and_not_feasible(self):
        text = self.texts["initial"].replace("level_complete=1", "level_complete=0").replace("admitted=1", "admitted=0")
        stats = self.result({**self.texts, "initial": text})["valid"]["by_method"]["initial"]
        self.assertEqual(stats["partial_level_n"], 1)
        self.assertEqual(stats["admitted_share"], 0)
        self.assertEqual(stats["feasible_ratio_median"], 0)
        self.assertEqual(stats["unusable_with_oracle"], 1)
        self.assertEqual(stats["feasible_ratio_mean"], 0)
        self.assertEqual(stats["feasible_ratio_p10"], 0)

    def test_old_direct_build_oracle_cannot_mix_with_v3(self):
        self.assertFalse(self.result({**self.texts, "oracle": self.texts["oracle"].replace("v=4", "v=3")})["comparisons"][0]["valid"])


if __name__ == "__main__":
    unittest.main()
