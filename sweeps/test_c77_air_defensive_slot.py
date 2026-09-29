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

    def test_c77_reuses_live_air_claims_as_permanent_policy(self):
        state = body(self.projects, "function OpexDefensiveSlotSelectionState(")
        self.assertNotIn("C77_OPPORTUNISTIC_CANDIDATES", state)
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
            self.assertNotIn(f'name = "{setting}"', self.info)

    def test_competitor_airport_signal_uses_constant_time_slot_count(self):
        enabled = body(self.builder_air, "function OpexAirC83SlotSignalEnabled(")
        self.assertNotIn("C77_OPPORTUNISTIC_CANDIDATES", enabled)
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
        self.assertNotIn("C77_OPPORTUNISTIC_CANDIDATES", priority)
        self.assertIn('project.mode != "air"', priority)
        self.assertIn("project.profitAnnual <= 0", priority)
        self.assertIn("if (competitorClaims > 0) return 2;", priority)
        self.assertIn("if (ownClaims > 0) return 1;", priority)

        select = body(self.projects, "function OpexProjectSelectAffordable(")
        refresh_at = select.index("OpexProjectRefreshDefensiveSlot(project, defensiveSlotState);")
        self.assertLess(select.index("financeCapital > capitalBudget"), refresh_at)
        self.assertIn("C121_AIR_DEFENSIVE_FLOOR", select)
        self.assertIn("c121DefensiveTier = OpexProjectDefensiveAirPriority(project);", select)
        self.assertIn("if (c121DefensiveTier >= 2) c121DefensiveFloor = floorProfit / 2;", select)
        self.assertIn("else if (c121DefensiveTier == 1) c121DefensiveFloor = floorProfit * 3 / 4;", select)
        self.assertIn("project.profitAnnual < c121DefensiveFloor", select)
        self.assertNotIn("c121DefensiveFloorExempt", select)
        self.assertNotIn("C77_OPPORTUNISTIC_CANDIDATES", select)
        self.assertIn('OpexProjectInsertDefensive(affordable, project, scoreKey, limit, AIR_EARLY_SLOT);', select)
        self.assertNotIn('OpexProjectInsert(affordable, project, scoreKey, limit, AIR_EARLY_SLOT);', select)

        insert = body(self.projects, "function OpexProjectInsertDefensive(")
        tier_at = insert.index("OpexProjectDefensiveAirPriority(prior)")
        score_at = insert.index("OpexProjectSelectionScore(prior, field)")
        self.assertLess(tier_at, score_at)
        self.assertIn("if (priorTier > projectTier) break;", insert)
        self.assertIn("if (priorTier < projectTier)", insert)

    def test_projects_pass_refreshes_only_the_funded_topk_before_spending(self):
        promote = body(self.projects, "function OpexPromoteLiveDefensiveAir(")
        self.assertNotIn("C77_OPPORTUNISTIC_CANDIDATES", promote)
        self.assertIn("projects.best", promote)
        self.assertIn("PROJECT_TOP_K", promote)
        self.assertIn("OpexProjectFinanceCapital(project) > capitalBudget", promote)
        self.assertIn("OpexDefensiveSlotSelectionState(earlyState)", promote)
        self.assertIn("OpexProjectRefreshDefensiveSlot(project, defensiveState);", promote)
        self.assertIn("local tier = OpexProjectDefensiveAirPriority(project);", promote)
        self.assertIn("tier > bestTier", promote)
        self.assertIn("projects.best.remove(bestIndex);", promote)
        self.assertIn("projects.best.insert(0, chosen);", promote)
        self.assertIn('" tick=" + AIController.GetTick()', promote)
        self.assertIn('" townA=" + defensiveTownA + " townB=" + defensiveTownB', promote)
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
        self.assertIn("AIStationList(AIStation.STATION_AIRPORT)", watch)
        self.assertIn("AIStation.GetLocation(st)", watch)
        self.assertIn("AITile.GetClosestTown(ownLoc)", watch)
        self.assertNotIn("AIStation.GetNearestTown(st)", watch)
        self.assertIn("local ownPresent = town.id in ownAirportTowns;", watch)
        self.assertNotIn("OpexAirTownServed(town, this._lines)", watch)
        self.assertIn('ownPresent ? "c83_slot_claimed" : "c83_slot_lost"', watch)
        self.assertIn("if (state != 1 || previous == 1) continue;", watch)
        self.assertIn("action=already_funded", watch)
        self.assertIn("action=enqueue_failed", watch)
        self.assertIn('this._c77EnqueueEntity(["air"], "town", town.id, true, "c83_slot_race")', watch)
        self.assertNotIn("candidateGroups", watch)
        self.assertNotIn("AIAirport.IsAirportTile", watch)

        top = body(self.builder_air, "function OpexAirC83WatchTowns(")
        self.assertIn("AIR_C83_TARGET_TOWNS", top)
        self.assertNotIn("AIR_EARLY_SLOT_TARGET_TOWNS", top)
        self.assertIn("if (best.len() > AIR_C83_TARGET_TOWNS) best.pop();", top)
        self.assertNotIn("OpexAirSortedTowns", top)

        globals_pre = read("ai/OpexAI/globals_pre.nut")
        self.assertIn("AIR_C83_TARGET_TOWNS <- 6;", globals_pre)

        attempt = body(self.task_projects, "function OpexAI::_tryBuildProjects(")
        watch_at = attempt.index("this._c83WatchAirSlotTransitions();")
        promote_at = attempt.index("OpexPromoteLiveDefensiveAir(this._projects, OpexAvailableCapital());")
        self.assertLess(watch_at, promote_at)

    def test_c78_probe_exposes_defensive_claims_only_inside_probe_paths(self):
        slot_town = body(self.probes, "function OpexC78AirSlotTown(")
        self.assertIn("AITile.GetClosestTown(site.anchor)", slot_town)
        self.assertNotIn("AIAirport.GetNearestTown(site.anchor, airportType)", slot_town)
        pass_probe = body(self.probes, "function OpexAI::_c78SlotOnProjectsPass(")
        self.assertIn("OpexC78AirSlotTown(plan.siteA, airportType)", pass_probe)
        self.assertIn("closestA=", pass_probe)
        self.assertIn("defensive_claims=", pass_probe)
        self.assertIn("defensive_competitor_claims=", pass_probe)
        attempt = body(self.task_projects, "function OpexAI::_tryBuildProjects(")
        self.assertIn("if (C78_SLOT_INTERCEPT_PROBE)", attempt)
        self.assertIn("OpexC78AirSlotTown(c78Plan.siteA, c78AirportType)", attempt)
        self.assertIn("defensive_claims=", attempt)
        self.assertIn("defensive_competitor_claims=", attempt)

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
        self.assertIn("AIR_C83_TARGET_TOWNS", plans)
        self.assertIn("OpexAirC83SecondSlotOpen(towns[i])", plans)
        self.assertIn("site.c83OwnSecondSlot <- true;", plans)
        self.assertIn('c83OwnSecondSlotA = ("c83OwnSecondSlot" in sites[a])', plans)
        self.assertIn('c83OwnSecondSlotB = ("c83OwnSecondSlot" in sites[b])', plans)

        live = body(self.task_air, "function OpexAirBatchPlanStillLive(")
        self.assertIn('("c83OwnSecondSlotA" in plan)', live)
        self.assertIn("if (!servedA || !OpexAirC83SecondSlotOpen(plan.siteA.town)) return false;", live)
        self.assertIn("if (!servedB || !OpexAirC83SecondSlotOpen(plan.siteB.town)) return false;", live)

        refresh = body(self.projects, "function OpexProjectRefreshDefensiveSlot(")
        self.assertIn("AITile.GetClosestTown(plan.siteA.anchor)", refresh)
        self.assertIn("AITile.GetClosestTown(plan.siteB.anchor)", refresh)
        self.assertNotIn("AIAirport.GetNearestTown(plan.siteA.anchor", refresh)
        self.assertNotIn("AIAirport.GetNearestTown(plan.siteB.anchor", refresh)
        self.assertIn("ownClaims++;", refresh)
        self.assertIn('OpexProjectSetEarlySlotField(project, "defensiveOwnClaims", ownClaims);', refresh)

    def test_targeted_air_regen_skips_only_pairs_that_cannot_touch_target(self):
        find_site = body(self.builder_air, "function OpexAirFindSite(")
        self.assertIn("requiredSlotTownId = -1", find_site)
        self.assertIn("AITile.GetClosestTown(anchor) != requiredSlotTownId", find_site)
        self.assertIn("local useSiteCache = AIR_SITE_CACHE_ENABLED && requiredSlotTownId < 0;", find_site)

        find_sites = body(self.builder_air, "function OpexAirPlansFindSites(")
        self.assertIn("local c83RequiredSlotTown = (targetTownId >= 0 && towns[i].id == targetTownId)", find_sites)
        self.assertIn("OpexAirFindSite(towns[i], airport, probes, c83RequiredSlotTown)", find_sites)

        new_pairs = body(self.builder_air, "function OpexAirPlansNewPairs(")
        self.assertIn("local targetSiteIndex = -1;", new_pairs)
        self.assertIn("if (targetTownId >= 0 && targetSiteIndex < 0) pairOuterLimit = 0;", new_pairs)
        self.assertIn("else if (targetTownId >= 0 && targetSiteIndex == 0) pairOuterLimit = 1;", new_pairs)
        self.assertIn("for (local a = startA; a < pairOuterLimit; a++)", new_pairs)
        self.assertIn("sites[a].town.id != targetTownId && sites[b].town.id != targetTownId", new_pairs)

        hub_site = body(self.builder_air, "function OpexAirPlansHubToSite(")
        self.assertIn("local targetTownId = ctx.targetTownId;", hub_site)
        self.assertIn("hub.town.id != targetTownId && site.town.id != targetTownId", hub_site)

        discover_hubs = body(self.builder_air, "function OpexAirPlansDiscoverHubs(")
        self.assertIn("OpexAirFindSite(towns[i], airport, hubProbes, c83RequiredSlotTown)", discover_hubs)

        hub_hub = body(self.builder_air, "function OpexAirPlansHubToHub(")
        self.assertIn("local targetTownId = ctx.targetTownId;", hub_hub)
        self.assertIn("hub1.town.id != targetTownId && hub2.town.id != targetTownId", hub_hub)


if __name__ == "__main__":
    unittest.main()
