import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start : idx + 1]
    raise AssertionError(f"unterminated function: {signature}")


def air_plans_pipeline(source):
    if "function OpexAirPlansPrepare(" in source:
        blocks = [
            "function OpexAirPlansPrepare(",
            "function OpexAirPlansFindSites(",
            "function OpexAirPlansNewPairs(",
            "function OpexAirPlansDiscoverHubs(",
            "function OpexAirPlansHubToSite(",
            "function OpexAirPlansHubToHub(",
            "function OpexAirPlansFinalize(",
            "function OpexAirPlans(",
        ]
        return "\n".join(body(source, sig) for sig in blocks)
    return body(source, "function OpexAirPlans(")


class C77AirDefensiveSlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projects = read("ai/OpexAI/projects.nut")
        cls.task_projects = read("ai/OpexAI/task_projects.nut")
        cls.builder_air = read("ai/OpexAI/builder_air.nut")
        cls.task_air = read("ai/OpexAI/task_air.nut")
        cls.probes = read("ai/OpexAI/probes.nut")
        cls.info = read("ai/OpexAI/info.nut")

    def test_c77_reuses_live_air_claims_with_corrected_default(self):
        state = body(self.projects, "function OpexDefensiveSlotSelectionState(")
        self.assertIn("!C77_OPPORTUNISTIC_CANDIDATES", state)
        self.assertIn("if (earlySlotState != null)", state)
        self.assertIn("state.servedTowns = earlySlotState.servedTowns;", state)
        self.assertIn("state.defensiveSlotSignal = OpexAirC83SlotSignalEnabled();", state)

        select = body(self.projects, "function OpexProjectSelectAffordable(")
        self.assertIn("OpexDefensiveSlotSelectionState(earlySlotState)", select)
        self.assertIn("OpexProjectRefreshDefensiveSlot(project, defensiveSlotState);", select)

        for setting in (
            "c77_opportunistic_candidates",
            "c77_targeted_build",
            "c77_fixes",
        ):
            c77_setting = self.info.index(f'name = "{setting}"')
            c77_block = self.info[c77_setting : c77_setting + 720]
            self.assertIn("easy_value = 1, medium_value = 1, hard_value = 1", c77_block)
            self.assertIn("custom_value = 1", c77_block)

    def test_competitor_airport_signal_uses_constant_time_slot_count(self):
        enabled = body(self.builder_air, "function OpexAirC83SlotSignalEnabled(")
        self.assertIn('AIGameSettings.IsValid("economy.station_noise_level")', enabled)
        self.assertIn('AIGameSettings.GetValue("economy.station_noise_level") == 0', enabled)
        self.assertIn('AIGameSettings.IsValid("difficulty.town_council_tolerance")', enabled)
        self.assertIn('AIGameSettings.GetValue("difficulty.town_council_tolerance") != 3', enabled)

        signal = body(self.projects, "function OpexC78TownHasCompetitorAirport(")
        self.assertIn("OpexC83TownSlotsRemaining(townId, state)", signal)
        self.assertNotIn("AIGameSettings.GetValue", signal)
        self.assertIn("return remaining == 1;", signal)
        self.assertNotIn("AIR_SITE_RADIUS", signal)
        self.assertNotIn("AIAirport.IsAirportTile", signal)
        self.assertNotIn("AITile.GetOwner", signal)

        slots = body(self.projects, "function OpexC83TownSlotsRemaining(")
        self.assertIn("AITown.GetAllowedNoise(townId)", slots)
        self.assertIn("state.slotRemaining.rawset", slots)

        refresh = body(self.projects, "function OpexProjectRefreshDefensiveSlot(")
        self.assertIn("competitorClaims++;", refresh)
        self.assertIn("OpexC78TownHasCompetitorAirport(townA, state)", refresh)
        self.assertIn("OpexC78TownHasCompetitorAirport(townB, state)", refresh)
        self.assertIn('OpexProjectSetEarlySlotField(project, "defensiveCompetitorClaims", competitorClaims);', refresh)

    def test_defensive_air_is_a_lexicographic_class_after_profit_and_cash_gates(self):
        priority = body(self.projects, "function OpexProjectDefensiveAirPriority(")
        self.assertIn("!C77_OPPORTUNISTIC_CANDIDATES", priority)
        self.assertIn('project.mode != "air"', priority)
        self.assertIn("project.profitAnnual <= 0", priority)
        self.assertIn("if (competitorClaims > 0) return 2;", priority)
        self.assertIn("if (ownClaims > 0) return 1;", priority)

        select = body(self.projects, "function OpexProjectSelectAffordable(")
        refresh_at = select.index("OpexProjectRefreshDefensiveSlot(project, defensiveSlotState);")
        self.assertLess(select.index("financeCapital > capitalBudget"), refresh_at)
        self.assertLess(select.index("project.profitAnnual < floorProfit"), refresh_at)
        self.assertIn("if (C77_OPPORTUNISTIC_CANDIDATES)", select)
        self.assertIn('OpexProjectInsertDefensive(affordable, project, scoreKey, limit, AIR_EARLY_SLOT);', select)
        self.assertIn('OpexProjectInsert(affordable, project, scoreKey, limit, AIR_EARLY_SLOT);', select)

        insert = body(self.projects, "function OpexProjectInsertDefensive(")
        tier_at = insert.index("OpexProjectDefensiveAirPriority(prior)")
        score_at = insert.index("OpexProjectSelectionScore(prior, field)")
        self.assertLess(tier_at, score_at)
        self.assertIn("if (priorTier > projectTier) break;", insert)
        self.assertIn("if (priorTier < projectTier)", insert)

        historical = body(self.projects, "function OpexProjectInsert(")
        self.assertNotIn("OpexProjectDefensiveAirPriority", historical)

    def test_projects_pass_refreshes_only_the_funded_topk_before_spending(self):
        promote = body(self.projects, "function OpexPromoteLiveDefensiveAir(")
        self.assertIn("!C77_OPPORTUNISTIC_CANDIDATES", promote)
        self.assertIn("projects.best", promote)
        self.assertIn("PROJECT_TOP_K", promote)
        self.assertIn("OpexProjectFinanceCapital(project) > capitalBudget", promote)
        self.assertIn("OpexDefensiveSlotSelectionState(earlyState)", promote)
        self.assertIn("OpexProjectRefreshDefensiveSlot(project, defensiveState);", promote)
        self.assertIn("local tier = OpexProjectDefensiveAirPriority(project);", promote)
        self.assertIn("tier > bestTier", promote)
        self.assertIn("projects.best.remove(bestIndex);", promote)
        self.assertIn("projects.best.insert(0, chosen);", promote)
        self.assertNotIn("candidateGroups", promote)
        self.assertNotIn("OpexAirSiteStillBuildable", promote)

        attempt = body(self.task_projects, "function OpexAI::_tryBuildProjects(")
        promote_at = attempt.index("OpexPromoteLiveDefensiveAir(this._projects, OpexAvailableCapital());")
        probe_at = attempt.index("this._c78SlotOnProjectsPass();")
        snapshot_at = attempt.index("c49Best =")
        loop_at = attempt.index("for (local i = 0; i < this._projects.best.len(); i++)")
        self.assertLess(promote_at, probe_at)
        self.assertLess(promote_at, snapshot_at)
        self.assertLess(promote_at, loop_at)

    def test_c83_slot_transition_enqueues_targeted_air_regen_without_pool_scan(self):
        watch = body(self.task_projects, "function OpexAI::_c83WatchAirSlotTransitions(")
        self.assertIn("OpexAirC83WatchTowns(this._catalog.towns)", watch)
        self.assertIn("AITown.GetAllowedNoise(town.id)", watch)
        self.assertIn("OpexAirTownServed(town, this._lines)", watch)
        self.assertIn("if (state != 1 || previous == 1) continue;", watch)
        self.assertIn('this._c77EnqueueEntity(["air"], "town", town.id, true, "c83_slot_race")', watch)
        self.assertNotIn("candidateGroups", watch)
        self.assertNotIn("AIAirport.IsAirportTile", watch)

        top = body(self.builder_air, "function OpexAirC83WatchTowns(")
        self.assertIn("AIR_EARLY_SLOT_TARGET_TOWNS", top)
        self.assertIn("if (best.len() > AIR_EARLY_SLOT_TARGET_TOWNS) best.pop();", top)
        self.assertNotIn("OpexAirSortedTowns", top)

        attempt = body(self.task_projects, "function OpexAI::_tryBuildProjects(")
        watch_at = attempt.index("this._c83WatchAirSlotTransitions();")
        promote_at = attempt.index("OpexPromoteLiveDefensiveAir(this._projects, OpexAvailableCapital());")
        self.assertLess(watch_at, promote_at)

    def test_c78_probe_exposes_defensive_claims_only_inside_probe_paths(self):
        pass_probe = body(self.probes, "function OpexAI::_c78SlotOnProjectsPass(")
        self.assertIn("defensive_claims=", pass_probe)
        attempt = body(self.task_projects, "function OpexAI::_tryBuildProjects(")
        self.assertIn("if (C78_SLOT_INTERCEPT_PROBE)", attempt)
        self.assertIn("defensive_claims=", attempt)

    def test_completed_rail_search_yields_only_one_pass_to_defensive_air(self):
        attempt = body(self.task_projects, "function OpexAI::_tryBuildProjects(")
        defer_at = attempt.index("local c77DeferCompletedRail =")
        consume_at = attempt.index("local railCandidate = this._railSearch.candidate;", defer_at)
        self.assertLess(defer_at, consume_at)
        self.assertIn('!("c77DefensiveDeferred" in this._railSearch)', attempt)
        self.assertIn("this._railSearch.c77DefensiveDeferred <- true;", attempt)
        consume_guard = attempt[defer_at:consume_at]
        self.assertIn("&& !c77DeferCompletedRail", consume_guard)

    def test_c83_can_generate_and_revalidate_own_second_slot_in_top_towns(self):
        plans = air_plans_pipeline(self.builder_air)
        self.assertIn("c83TopTownIds", plans)
        self.assertIn("AIR_EARLY_SLOT_TARGET_TOWNS", plans)
        self.assertIn("OpexAirC83SecondSlotOpen(towns[i])", plans)
        self.assertIn("site.c83OwnSecondSlot <- true;", plans)
        self.assertIn('c83OwnSecondSlotA = ("c83OwnSecondSlot" in sites[a])', plans)
        self.assertIn('c83OwnSecondSlotB = ("c83OwnSecondSlot" in sites[b])', plans)

        live = body(self.task_air, "function OpexAirBatchPlanStillLive(")
        self.assertIn('("c83OwnSecondSlotA" in plan)', live)
        self.assertIn("if (!servedA || !OpexAirC83SecondSlotOpen(plan.siteA.town)) return false;", live)
        self.assertIn("if (!servedB || !OpexAirC83SecondSlotOpen(plan.siteB.town)) return false;", live)

        refresh = body(self.projects, "function OpexProjectRefreshDefensiveSlot(")
        self.assertIn("ownClaims++;", refresh)
        self.assertIn('OpexProjectSetEarlySlotField(project, "defensiveOwnClaims", ownClaims);', refresh)


if __name__ == "__main__":
    unittest.main()
