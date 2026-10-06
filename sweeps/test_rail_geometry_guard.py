#!/usr/bin/env python3
"""Contrats du garde geometrique des poses rail persistantes."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1:pos]
    raise AssertionError(f"corps non ferme: {signature}")


class TestRailGeometryGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = source("builder_rail.nut")
        cls.task = source("task_rail.nut")
        cls.info = source("info.nut")
        cls.settings = source("settings.nut")
        cls.globals = source("globals_pre.nut")
        cls.persist = source("persist.nut")

    def test_setting_is_dedicated_and_off_by_default(self):
        start = self.info.index('name = "rail_geometry_guard"')
        block = self.info[start:self.info.index("});", start)]
        for name in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, rf"{name}\s*=\s*0")
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("RAIL_GEOMETRY_GUARD <- false;", self.globals)
        self.assertIn(
            'RAIL_GEOMETRY_GUARD = AIController.GetSetting("rail_geometry_guard") != 0;',
            self.settings,
        )
        self.assertIn("RAIL_GEOMETRY_PREFILTER <- true;", self.globals)
        self.assertIn("RAIL_GEOMETRY_PAIR_MEMORY <- true;", self.globals)
        self.assertIn("RAIL_GEOMETRY_EXACT_IDENTITY <- true;", self.globals)
        self.assertIn("RAIL_GEOMETRY_LIVE_REPLAN <- false;", self.globals)
        self.assertIn(
            'RAIL_GEOMETRY_EXACT_IDENTITY = AIController.GetSetting("rail_geometry_exact_identity") != 0;',
            self.settings,
        )
        self.assertIn(
            'RAIL_GEOMETRY_PREFILTER = AIController.GetSetting("rail_geometry_prefilter") != 0;',
            self.settings,
        )
        self.assertIn(
            'RAIL_GEOMETRY_PAIR_MEMORY = AIController.GetSetting("rail_geometry_pair_memory") != 0;',
            self.settings,
        )
        self.assertIn(
            'RAIL_GEOMETRY_LIVE_REPLAN = AIController.GetSetting("rail_geometry_live_replan") != 0;',
            self.settings,
        )

        start = self.info.index('name = "rail_geometry_live_replan"')
        block = self.info[start:self.info.index("});", start)]
        for name in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, rf"{name}\s*=\s*0")

    def test_pathfinder_endpoint_identity_keeps_lead_not_only_station_exit(self):
        legacy = function_body(self.builder, "function OpexMatchPlan(plans, tile)")
        self.assertIn("if (plan.station_exit == tile) return plan;", legacy)
        self.assertNotIn("lead", legacy)
        match = function_body(self.builder, "function OpexMatchPlanExact(plans, tile, lead)")
        self.assertIn("plan.station_exit == tile", match)
        self.assertIn("plan.lead == lead", match)

        complete = function_body(self.builder, "function OpexCompleteRailRouteAfterSearch(")
        self.assertIn("if (RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_PREFILTER)", complete)
        self.assertIn("(RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_EXACT_IDENTITY)", complete)
        self.assertIn("OpexMatchPlanExact(plan.plansA, tiles[0], tiles[1])", complete)
        self.assertIn("OpexMatchPlanExact(plan.plansB, tiles[last], tiles[last - 1])", complete)
        # Gate OFF : chemin historique conserve mot pour mot la selection par station_exit seul.
        self.assertIn("OpexMatchPlan(plan.plansA, tiles[0]);", complete)
        self.assertIn("OpexMatchPlan(plan.plansB, tiles[last]);", complete)

    def test_fixture_same_exit_opposite_orientation_explains_station_on_lead(self):
        """Deux plans valides peuvent partager la sortie tout en ayant des leads opposes.

        C'est exactement le cas que l'ancien appariement par station_exit seul confond : le quai
        oppose peut alors recouvrir le lead que l'A* avait choisi pour l'autre orientation.
        """
        length = 3
        station_exit = 100
        step = 1
        chosen = {
            "anchor": station_exit - step * (length - 1),
            "station_exit": station_exit,
            "lead": station_exit + step,
        }
        opposite = {
            "anchor": station_exit,
            "station_exit": station_exit,
            "lead": station_exit - step,
        }
        chosen_footprint = {chosen["anchor"] + step * i for i in range(length)}
        opposite_footprint = {opposite["anchor"] + step * i for i in range(length)}

        self.assertEqual(chosen["station_exit"], opposite["station_exit"])
        self.assertNotEqual(chosen["lead"], opposite["lead"])
        self.assertNotIn(chosen["lead"], chosen_footprint)
        self.assertIn(chosen["lead"], opposite_footprint)

        plans = [opposite, chosen]
        legacy = next(p for p in plans if p["station_exit"] == station_exit)
        exact = next(
            p for p in plans
            if p["station_exit"] == station_exit and p["lead"] == chosen["lead"]
        )
        self.assertIs(legacy, opposite)
        self.assertIs(exact, chosen)

    def test_preflight_rejects_station_lead_overlap_before_any_real_spend(self):
        geom = function_body(self.builder, "function OpexRailPathGeometryIssue(")
        for token in (
            "OpexRailPlanContainsTile(planA, leadA)",
            "OpexRailPlanContainsTile(planB, leadA)",
            "OpexRailPlanContainsTile(planA, leadB)",
            "OpexRailPlanContainsTile(planB, leadB)",
        ):
            self.assertIn(token, geom)

        complete_start = self.builder.index("function OpexCompleteRailRouteAfterSearch(")
        complete_end = self.builder.index("\nfunction OpexPlanRailRoute(", complete_start)
        complete = self.builder[complete_start:complete_end]
        reject_at = complete.index("OpexRailPathGeometryIssue")
        self.assertLess(reject_at, complete.index("plan.ok = true;"))
        self.assertNotIn("AITile.DemolishTile", complete[:reject_at])
        self.assertNotIn("AIRail.BuildRailStation", complete[:reject_at])

    def test_live_replan_keeps_same_length_and_exact_path_interface(self):
        refresh = function_body(
            self.builder, "function OpexRailRefreshExactPlatforms(catalog, candidate, plan)"
        )
        self.assertIn("local fresh = OpexRailPlatformPlans(catalog, candidate);", refresh)
        self.assertIn("if (fresh.length != plan.length)", refresh)
        self.assertIn("OpexMatchPlanExact(fresh.plansA, tiles[0], tiles[1])", refresh)
        self.assertIn("OpexMatchPlanExact(fresh.plansB, tiles[last], tiles[last - 1])", refresh)
        self.assertIn("OpexRailPathGeometryIssue(tiles, planA, planB)", refresh)
        self.assertNotIn("OpexSearchPath", refresh)
        self.assertNotIn("OpexCreateRailPathfinder", refresh)

    def test_live_replan_only_retries_stnfail_quote_before_real_spend(self):
        execute = function_body(self.builder, "function OpexExecuteRailPlan(")
        first_quote = execute.index("OpexQuoteRailCapital(catalog, candidate, plan, quoteFailure)")
        gate = execute.index("RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_LIVE_REPLAN")
        refresh = execute.index("OpexRailRefreshExactPlatforms(catalog, candidate, plan)")
        second_quote = execute.index(
            "OpexQuoteRailCapital(catalog, candidate, plan, quoteFailure)", first_quote + 1
        )
        real_spend = execute.index("local costs = AIAccounting();")
        self.assertLess(first_quote, gate)
        self.assertLess(gate, refresh)
        self.assertLess(refresh, second_quote)
        self.assertLess(second_quote, real_spend)
        self.assertIn('quoteFailure.reason == "STNFAIL"', execute[first_quote:refresh])
        self.assertIn('OpexDecide("RAIL_GEOM_REPLAN"', execute)

    def test_terminal_jump_filter_matches_proven_skip_without_symmetric_overban(self):
        geom = function_body(self.builder, "function OpexRailPathGeometryIssue(")
        self.assertIn(
            "AIMap.DistanceManhattan(tiles[last - 2], tiles[last - 1]) > 1",
            geom,
        )
        # Le saut cote A (lead -> prochain segment) n'entre pas dans la branche de skip
        # prev->cur d'OpexBuildTrack : ne pas rejeter un cas non prouve condamne.
        self.assertNotIn("AIMap.DistanceManhattan(tiles[1], tiles[2]) > 1", geom)

    def test_only_explicit_persistent_trkfail_enters_pair_memory(self):
        record = function_body(self.task, "function OpexAI::_recordRailAttempt(")
        self.assertIn('result.reason == "TRKFAIL"', record)
        self.assertIn('("persistentGeometry" in result) && result.persistentGeometry', record)
        self.assertIn("RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_PAIR_MEMORY", record)
        self.assertNotIn('|| result.reason == "TRKFAIL"', record)

        persistent = function_body(
            self.builder, "function OpexRailTrackFailureIsPersistentGeometry("
        )
        self.assertIn("failure.error != AIError.ERR_AREA_NOT_CLEAR", persistent)
        self.assertIn("failure.is_station != 1", persistent)
        self.assertIn("failure.owner_self != 1", persistent)
        self.assertIn("failure.tile == leadA || failure.tile == leadB", persistent)
        self.assertNotIn("ERR_VEHICLE_IN_THE_WAY", persistent)

    def test_cash_and_other_transient_failures_are_not_newly_banned(self):
        record = function_body(self.task, "function OpexAI::_recordRailAttempt(")
        memory = record[record.index("if (ABANDON_MEMORY &&"):]
        self.assertNotIn('result.reason == "CASH"', memory)
        self.assertNotIn("ERR_NOT_ENOUGH_CASH", memory)
        consume = function_body(self.task, "function OpexAI::_consumeRailSearch(year)")
        self.assertLess(consume.index('if (result.reason == "CASH")'), consume.index("_recordRailAttempt"))

    def test_existing_abandoned_pair_save_load_shape_is_reused(self):
        save = function_body(self.persist, "function OpexAI::Save()")
        load = function_body(self.persist, "function OpexAI::Load(version, data)")
        self.assertIn("abandonedPairs = this._abandonedPairs", save)
        self.assertIn('if ("abandonedPairs" in data', load)
        self.assertIn("this._abandonedPairs[key] <- val", load)
        self.assertNotIn("persistentGeometry", save)
        self.assertNotIn("persistentGeometry", load)

    def test_rollback_path_remains_after_real_track_failure(self):
        execute = function_body(self.builder, "function OpexExecuteRailPlan(")
        fail = execute[execute.index("if (!connected)"):execute.index("local depot =", execute.index("if (!connected)"))]
        self.assertIn("OpexRollback(tiles, planA, planB, null, null);", fail)
        self.assertLess(fail.index("OpexRailTrackFailureIsPersistentGeometry"), fail.index("OpexRollback"))


if __name__ == "__main__":
    unittest.main()
