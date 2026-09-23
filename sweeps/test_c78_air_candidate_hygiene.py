import re
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


class C78AirCandidateHygieneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.air = read("ai/OpexAI/builder_air.nut")
        cls.projects = read("ai/OpexAI/projects.nut")
        cls.task_air = read("ai/OpexAI/task_air.nut")
        cls.task_projects = read("ai/OpexAI/task_projects.nut")
        cls.orchestrator = read("ai/OpexAI/orchestrator.nut")
        cls.persist = read("ai/OpexAI/persist.nut")
        cls.scheduler_tasks = read("ai/OpexAI/scheduler_tasks.nut")

    def test_town_pool_depends_on_map_and_town_count(self):
        self.assertNotIn("AIR_TOWN_POOL <-", self.air)
        self.assertNotIn("AIR_HUB_TOWN_POOL <-", self.air)
        pool = body(self.air, "function OpexAirTownPoolLimit(")
        self.assertIn("AIMap.GetMapSizeX()", pool)
        self.assertIn("AIMap.GetMapSizeY()", pool)
        self.assertIn("AIR_TOWN_MIN_DISTANCE", pool)
        self.assertIn("local gridCapacity = cellsX * cellsY;", pool)
        self.assertIn("local perimeterCapacity = 4 * (cellsX + cellsY);", pool)
        self.assertIn("gridCapacity < perimeterCapacity ? gridCapacity : perimeterCapacity", pool)
        self.assertIn("towns.len()", pool)
        plans = air_plans_pipeline(self.air)
        self.assertIn("OpexAirTownPoolLimit(towns)", plans)
        self.assertIn("resumeState.townLimit", plans)

    def test_station_limit_and_stale_sites_are_rejected_before_ranking(self):
        remember = body(self.air, "function OpexAirRememberTownStationLimit(")
        self.assertIn("AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN", remember)
        find_site = body(self.air, "function OpexAirFindSite(")
        self.assertIn("OpexAirRememberTownStationLimit", find_site)
        still_buildable = body(self.air, "function OpexAirSiteStillBuildable(")
        self.assertIn("AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN", still_buildable)
        plans = air_plans_pipeline(self.air)
        self.assertLess(
            plans.index("OpexAirSiteStillBuildable(site, airport, plane, false"),
            plans.index("OpexAirChooseRoutePlane("),
        )

        for signature in (
            "function OpexReselectProjects(",
            "function OpexIncrementalUpdateProjects(",
            "function OpexBuildProjects(",
        ):
            selection = body(self.projects, signature)
            self.assertLess(
                selection.index("OpexFilterAirAlternativesStillValid("),
                selection.index("OpexProjectSelectAffordable("),
            )

    def test_generation_and_build_share_one_unordered_abandon_key(self):
        pair_key = body(self.air, "function OpexAirPairKey(")
        self.assertIn("if (a > b)", pair_key)
        self.assertIn('return "air|" + a + "|" + b;', pair_key)

        plans = air_plans_pipeline(self.air)
        self.assertIn("OpexAirPairIsAbandoned(abandoned, sites[a], sites[b])", plans)
        self.assertIn("OpexAirPairIsAbandoned(abandoned, hub, site)", plans)
        self.assertIn("OpexAirPairIsAbandoned(abandoned, hub1, hub2)", plans)

        direct = body(self.task_air, "function OpexAI::_tryBuildAir(")
        self.assertIn("this._markPairAbandoned(OpexAirPairKey(plan.siteA, plan.siteB));", direct)
        portfolio = body(self.task_air, "function OpexAI::_tryBuildAirProject(")
        self.assertIn("local abandonedKey = OpexAirPairKey(plan.siteA, plan.siteB);", portfolio)
        self.assertIn("OpexAirPairIsAbandoned(this._abandonedPairs, plan.siteA, plan.siteB)", portfolio)

    def test_first_portfolio_air_attempt_is_revalidated(self):
        attempt = body(self.task_air, "function OpexAI::_tryBuildAirProject(")
        self.assertNotIn("if (builtCount > 0)", attempt)
        build_at = attempt.index("OpexBuildAirRoute(")
        self.assertLess(attempt.index("OpexAirBatchPlanStillLive("), build_at)
        self.assertLess(attempt.index("OpexAirBatchSiteStillBuildable(plan.siteA"), build_at)
        self.assertLess(attempt.index("OpexAirBatchSiteStillBuildable(plan.siteB"), build_at)

    def test_air_pair_scan_can_resume_on_combo_a_b_budget(self):
        plans = air_plans_pipeline(self.air)
        self.assertIn("resumeState = null, opsBudget = 0, deadlineTick = 0", plans)
        self.assertIn("resumeState.combo", plans)
        self.assertIn("resumeState.a", plans)
        self.assertIn("resumeState.b", plans)
        self.assertIn("resumeState.sites", plans)
        self.assertIn("resumeState.bestPlan", plans)
        self.assertIn("resumeState.combos", plans)
        self.assertIn("sliced && resumeState.combos != null", plans)
        self.assertIn("pairProgress && ((opsBudget > 0 && sliceOps >= opsBudget)", plans)
        self.assertIn("resumeState.a = nextA;", plans)
        self.assertIn("resumeState.b = nextB;", plans)
        self.assertIn("AIController.GetTick() >= deadlineTick", plans)
        self.assertIn("OpexAirSiteStillBuildable", plans)
        self.assertIn("if (!sliced || !resumingCombo)", plans)

    def test_air_site_scan_and_revalidation_resume_before_pairs(self):
        plans = air_plans_pipeline(self.air)
        for field in (
            "resumeState.towns",
            "resumeState.scanIndex",
            "resumeState.scanSites",
            "resumeState.scanProbes",
            "resumeState.rankIndex",
            "resumeState.rankSites",
        ):
            self.assertIn(field, plans)
        find_at = plans.index("OpexAirFindSite(towns[i], airport, probes)")
        scan_cursor_at = plans.index("resumeState.scanIndex = i + 1;", find_at)
        scan_budget_at = plans.index("scanSliceOps >= opsBudget", scan_cursor_at)
        pair_at = plans.index("local startA =", scan_budget_at)
        self.assertLess(find_at, scan_cursor_at)
        self.assertLess(scan_cursor_at, scan_budget_at)
        self.assertLess(scan_budget_at, pair_at)
        rank_probe_at = plans.index("OpexAirSiteStillBuildable(site, airport, plane, false", scan_budget_at)
        rank_cursor_at = plans.index("resumeState.rankIndex = rankIndex + 1;", rank_probe_at)
        rank_budget_at = plans.index("rankSliceOps >= opsBudget", rank_cursor_at)
        self.assertLess(rank_probe_at, rank_cursor_at)
        self.assertLess(rank_cursor_at, rank_budget_at)

    def test_catalog_air_slicing_is_large_pool_only(self):
        start = body(self.scheduler_tasks, "function OpexC78StartCatalogAirRebuild(")
        self.assertIn("OpexAirTownPoolLimit(owner._catalog.towns) <= 64", start)
        self.assertLess(
            start.index("OpexAirTownPoolLimit(owner._catalog.towns) <= 64"),
            start.index("task.c78AirRebuild <-"),
        )
        cont = body(self.scheduler_tasks, "function OpexC78ContinueCatalogAirRebuild(")
        self.assertIn("AIR_PLAN_SLICE_OPS", cont)
        self.assertIn("AIR_PLAN_SLICE_OPS <- 180000;", self.air)
        self.assertIn("local liveOps = AIController.GetOpsTillSuspend();", cont)
        self.assertIn("local sliceBudget = liveOps;", cont)
        self.assertIn("if (sliceBudget <= 0) sliceBudget = 1;", cont)
        self.assertIn("if (sliceBudget > AIR_PLAN_SLICE_OPS) sliceBudget = AIR_PLAN_SLICE_OPS;", cont)
        self.assertIn("sliceBudget, AIController.GetTick() + BUILD_TICK_MARGIN", cont)

        requeue = body(self.scheduler_tasks, "function OpexC78RequeueInitialCatalogSlice(")
        self.assertIn("if (owner._projects != null) return;", requeue)
        self.assertIn("task.dueCycle = owner._taskCycle;", requeue)
        self.assertIn("owner._taskCursor = 0;", requeue)
        self.assertGreaterEqual(cont.count("OpexC78RequeueInitialCatalogSlice(owner, task);"), 3)

    def test_catalog_refresh_reason_survives_c78_resume_scope(self):
        dispatch = body(self.scheduler_tasks, "function OpexAI::_dispatchCatalog(")
        self.assertIn('local refreshReason = "month";', dispatch)
        self.assertIn("refreshReason = task.c78AirRebuild.refreshReason;", dispatch)
        self.assertIn("refreshReason = this._portfolioInvalidated ?", dispatch)
        self.assertNotIn("local refreshReason = this._portfolioInvalidated ?", dispatch)

    def test_large_map_catalog_defers_partial_and_exact_publication_to_next_dispatch(self):
        cont = body(self.scheduler_tasks, "function OpexC78ContinueCatalogAirRebuild(")
        self.assertIn('if (("partialPending" in s) && s.partialPending)', cont)
        partial_start = cont.index('if (("partialPending" in s) && s.partialPending)')
        apply_start = cont.index('if (s.phase == "apply")', partial_start)
        partial_block = cont[partial_start:apply_start]
        self.assertIn("owner._rebuildProjects(s.fleetPlan, partialAir, false);", partial_block)
        self.assertIn("s.published = true;", partial_block)
        self.assertIn("s.partialPending = false;", partial_block)
        self.assertIn('if (s.phase == "apply")', cont)
        scan_start = cont.index("local liveOps = AIController.GetOpsTillSuspend();", apply_start)
        apply_block = cont[apply_start:scan_start]
        self.assertIn("owner._rebuildProjects(s.fleetPlan, airOverride);", apply_block)
        scan_block = cont[scan_start:]
        self.assertNotIn("owner._rebuildProjects(", scan_block)
        pending_at = scan_block.index("s.partialPending = true;")
        pending_return = scan_block.index("return false;", pending_at)
        self.assertLess(pending_at, pending_return)
        apply_phase = scan_block.index('s.phase = "apply";')
        requeue_phase = scan_block.index("OpexC78RequeueInitialCatalogSlice(owner, task);", apply_phase)
        return_phase = scan_block.index("return false;", requeue_phase)
        self.assertLess(apply_phase, requeue_phase)
        self.assertLess(requeue_phase, return_phase)
        rebuild = body(self.task_projects, "function OpexAI::_rebuildProjects(")
        self.assertIn("airOverride = null, advanceStage = true", rebuild)
        self.assertIn("OpexAirTownPoolLimit(this._catalog.towns) > 64", rebuild)
        self.assertIn('task.name == "catalog"', rebuild)
        self.assertIn("advanceStage = false;", rebuild)
        self.assertIn("if (advanceStage && STAGED_BOOTSTRAP", rebuild)

    def test_c77_air_worker_keeps_slice_state_until_done(self):
        regen = body(self.projects, "function OpexRegenerateAirProjectsSlice(")
        self.assertIn("sliceState.plans", regen)
        self.assertIn("sliceState.airCursor", regen)
        self.assertIn("opsBudget, deadlineTick", regen)
        self.assertLess(
            regen.index('if (!("done" in sliceState.airCursor) || !sliceState.airCursor.done)'),
            regen.index("OpexApplyGeneratedModeProjects("),
        )

        worker = body(self.orchestrator, "function OpexWorkerRegenCandidatesStep(")
        self.assertIn('if (mode == "air")', worker)
        self.assertIn("s.airState", worker)
        self.assertIn("OpexRegenerateAirProjectsSlice", worker)
        self.assertLess(worker.index('if (!airSlice.done) return "running";'), worker.index("s.cursor++;"))

        save_worker = body(self.persist, "function OpexSaveActiveWorker(")
        regen_branch = save_worker.index('if (worker.kind == "regen_candidates")')
        self.assertGreater(regen_branch, 0)
        regen_save = save_worker[regen_branch:]
        self.assertNotIn("airState =", regen_save)
        self.assertNotIn("preparedCursor =", regen_save)
        self.assertIn('cursor = ("cursor" in s) ? s.cursor : 0', regen_save)

    def test_catalog_air_resume_state_is_transient_across_save_load(self):
        save = body(self.persist, "function OpexAI::Save()")
        load = body(self.persist, "function OpexAI::Load(")
        self.assertNotIn("c78AirRebuild", save)
        self.assertNotIn("c78AirRebuild", load)


if __name__ == "__main__":
    unittest.main()
