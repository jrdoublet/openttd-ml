#!/usr/bin/env python3
"""Tests de contrat pour C80 Étape 2 : worker RailSearchStock autonome N=1 sur reliquat (c80_rail_stock_worker)."""
from __future__ import annotations

import unittest
from pathlib import Path
import re
from diag_c80_projects_gap import extract, analyze_events
from opex_projects_source import read_projects_source

ROOT = Path(__file__).resolve().parents[1]


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class TestC80RailStockWorkerContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.main = _read("ai/OpexAI/main.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.projects = read_projects_source()
        cls.task_projects = _read("ai/OpexAI/task_projects.nut")
        cls.task_rail = _read("ai/OpexAI/task_rail.nut")
        cls.orchestrator = _read("ai/OpexAI/orchestrator.nut")
        cls.scheduler = _read("ai/OpexAI/scheduler.nut")

    def test_setting_declared_in_info_nut(self):
        self.assertIn('name = "c80_rail_stock_worker"', self.info)
        start = self.info.index('name = "c80_rail_stock_worker"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("custom_value = 0", block)
        self.assertIn("easy_value = 0", block)
        self.assertIn("medium_value = 0", block)
        self.assertIn("hard_value = 0", block)

    def test_global_declared_in_globals_pre_nut(self):
        self.assertIn("C80_RAIL_STOCK_WORKER <- false;", self.globals)

    def test_setting_loaded_with_gate_dependency_in_settings_nut(self):
        self.assertIn(
            'C80_RAIL_STOCK_WORKER = C80_RAIL_STOCK_GATE && (AIController.GetSetting("c80_rail_stock_worker") != 0);',
            self.settings,
        )

    def test_member_declared_and_initialized_in_main_nut(self):
        self.assertIn("_railStockCooldown = null;", self.main)
        self.assertIn("this._railStockCooldown = {};", self.main)

    def test_transient_reconstructed_in_persist_nut(self):
        self.assertIn("this._railStockCooldown = {};", self.persist)
        self.assertIn('worker.kind == "rail_stock"', self.persist)

    def test_worker_registered_in_orchestrator_nut(self):
        self.assertIn('OpexRegisterWorker("rail_stock", OpexWorkerRailStockStep, OpexWorkerRailStockCancel);', self.orchestrator)
        self.assertIn('function OpexWorkerRailStockStep(worker, opsBudget, deadlineTick)', self.orchestrator)
        self.assertIn('function OpexWorkerRailStockCancel(worker)', self.orchestrator)

    def test_orchestrator_tick_handles_rail_stock(self):
        self.assertIn('ai._checkRailStockExpiry();', self.orchestrator)
        self.assertIn('this._activeWorker.kind == "rail_stock"', self.orchestrator)
        self.assertIn('ai._tryStartRailStockWorker();', self.orchestrator)

    def test_stock_capacity_n1_enforced(self):
        self.assertIn("this._railReadyStock.len() >= 1", self.task_rail)
        self.assertIn("this._railReadyStock.len() < 1", self.task_projects)

    def test_duration_180_days_enforced(self):
        # 1. Péremption stock 180 j
        self.assertIn("age > 180", self.task_rail)
        # 2. Timeout recherche 180 j
        self.assertIn("curDate - startDate > 180", self.orchestrator)

    def test_revalidation_mandatory_before_build(self):
        self.assertIn("function OpexAI::_revalidateRailStockPlan(candidate, plan)", self.task_rail)
        self.assertIn("this._revalidateRailStockPlan(candidate, entry.plan)", self.task_rail)
        # Contrat : _revalidateRailStockPlan n'appelle plus OpexBuildTrack mais OpexTestRailTrack
        start_reval = self.task_rail.index("function OpexAI::_revalidateRailStockPlan")
        end_reval = self.task_rail.index("\n}\n", start_reval) + 3
        reval_body = self.task_rail[start_reval:end_reval]
        self.assertNotIn("OpexBuildTrack", reval_body)
        self.assertIn("OpexTestRailTrack", reval_body)

        # OpexBuildTrack n'est plus byte-identique à 6895781 : sonde additive
        # RAIL_TRACK_FAIL (3e paramètre failure = null). failure null n'écrit rien.
        # OpexTestRailTrack reste le jumeau sans AreTilesConnected ni ces champs.
        rail = (ROOT / "ai/OpexAI/builder_rail.nut").read_text(encoding="utf-8")
        start = rail.index("function OpexBuildTrack(")
        end = rail.index("\nfunction OpexTestRailTrack(", start)
        body = rail[start:end]
        self.assertTrue(body.startswith(
            "function OpexBuildTrack(tiles, structures = null, failure = null)"))
        self.assertIn("return failed;", body)
        self.assertIn("ok = AIRail.BuildRail(prev, cur, next);", body)
        self.assertIn("ok = AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur);", body)
        self.assertIn(
            "ok = !bridges.IsEmpty() && AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next);",
            body)
        self.assertIn("!AIRail.AreTilesConnected(prev, cur, next)", body)
        self.assertIn('OpexRailCaptureTrackFailure(failure, tiles, i, cur, "connect", err, manhPrev, manhNext);', body)
        self.assertIn("OpexRailCaptureTrackFailure(failure, tiles, i, cur, segmentKind, err, manhPrev, manhNext);", body)
        self.assertIn('if (failure != null && !("index" in failure))', body)
        self.assertEqual(body.count('if (failure != null && !("index" in failure))'), 2)
        fills = body.split('if (failure != null && !("index" in failure))')
        self.assertEqual(len(fills), 3)
        self.assertNotIn("failure.is_station", fills[0])
        self.assertNotIn("failure.dup_index", fills[0])
        self.assertNotIn("AITile.IsBuildable(cur)", fills[0])
        self.assertNotIn("OpexRailCaptureTrackFailure", fills[0])
        helper = rail[rail.index("function OpexRailCaptureTrackFailure("):start]
        tile_state = (
            "failure.is_buildable <- AITile.IsBuildable(cur) ? 1 : 0;",
            "failure.is_rail <- AIRail.IsRailTile(cur) ? 1 : 0;",
            "failure.is_station <- AIRail.IsRailStationTile(cur) ? 1 : 0;",
            "failure.is_road <- AIRoad.IsRoadTile(cur) ? 1 : 0;",
            "failure.is_water <- AITile.IsWaterTile(cur) ? 1 : 0;",
            "failure.owner_self <- (AITile.GetOwner(cur) == "
            "AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)) ? 1 : 0;",
            "failure.slope <- AITile.GetSlope(cur);",
            "failure.dup_index <- dupIndex;",
            "for (local j = 0; j < i; j++) {",
            "if (tiles[j] == cur) {",
        )
        for line in tile_state:
            self.assertIn(line, helper)
        self.assertIn("failure.kind <- kind;", helper)
        self.assertNotIn("GetLastError()", helper)
        self.assertNotIn("OpexDecide", helper)
        for part in fills[1:]:
            self.assertLess(part.index("local err = AIError.GetLastError();"),
                            part.index("local manhPrev = AIMap.DistanceManhattan(prev, cur);"))
            self.assertLess(part.index("local manhNext = AIMap.DistanceManhattan(cur, next);"),
                            part.index("OpexRailCaptureTrackFailure("))
            self.assertNotIn("failure.is_station", part)
            self.assertNotIn("failure.dup_index", part)
        self.assertNotIn("OpexDecide", body)
        twin = rail[end:rail.index("\nfunction OpexBuildDepot(", end)]
        self.assertIn("function OpexTestRailTrack(tiles, structures = null)", twin)
        self.assertIn("firstSegment", twin)
        self.assertIn("firstTile", twin)
        self.assertNotIn("failure", twin)
        self.assertNotIn("manh_prev", twin)
        self.assertNotIn("is_station", twin)
        self.assertNotIn("dup_index", twin)
        self.assertNotIn("IsRailStationTile", twin)

        execute = rail[rail.index("function OpexExecuteRailPlan("):rail.index("\nfunction OpexBuildLine(")]
        self.assertIn("local trackFailure = null;\n  if (DECISION_LOG || RAIL_GEOMETRY_GUARD) trackFailure = {};", execute)
        self.assertIn("OpexBuildTrack(tiles, plan.structures, trackFailure)", execute)
        self.assertIn("OpexBuildTrack(tiles2, plan.structures2);", execute)
        self.assertEqual(execute.count("OpexBuildTrack(tiles, plan.structures, trackFailure)"), 1)
        self.assertIn(
            "local connected = trackFailed == 0 &&\n"
            "      AIRail.AreTilesConnected(planA.station_exit, tiles[1], tiles[2]) &&\n"
            "      AIRail.AreTilesConnected(tiles[last - 2], tiles[last - 1], planB.station_exit);",
            execute)
        track_at = execute.index('OpexDecide("RAIL_TRACK_FAIL"')
        track_log = execute[execute.rindex("if (!connected)", 0, track_at):
                            execute.index('result.reason = "TRKFAIL"', track_at)]
        self.assertIn("if (DECISION_LOG)", track_log)
        self.assertIn("tiles.len() >= 3", track_log)
        self.assertIn("exit_a=", track_log)
        self.assertIn("exit_b=", track_log)
        self.assertIn('cause=" + (trackFailed > 0 ? "track" : "connect")', track_log)
        log_order = (
            "cause=", "failed=", "tiles=", "exit_a=", "exit_b=",
            "idx=", "tile=", "kind=", "err=", "mprev=", "mnext=",
            "bld=", "rail=", "stn=", "road=", "watr=", "own=", "slp=", "dup=",
            "leadb=", "exitb=",
            "h0=", "h1=", "h2=", "d01=", "d12=",
            "t2=", "t1=", "t0=", "d21=", "d10=",
        )
        log_pos = -1
        for token in log_order:
            at = track_log.index(token)
            self.assertGreater(at, log_pos, token)
            log_pos = at
        for key in (
            "is_buildable", "is_rail", "is_station", "is_road", "is_water",
            "owner_self", "slope", "dup_index", "lead", "station_exit",
        ):
            self.assertIn(f'("{key}" in ', track_log)
        self.assertIn("trackFailure.is_buildable", track_log)
        self.assertIn("trackFailure.is_station", track_log)
        self.assertIn("trackFailure.dup_index", track_log)
        self.assertIn("planB.lead", track_log)
        self.assertIn("planB.station_exit", track_log)
        self.assertLess(track_log.index("exitb="), track_log.index('OpexDecide("RAIL_TRACK_FAIL"'))
        geom = track_log[track_log.index("exitb="):track_log.index('OpexDecide("RAIL_TRACK_FAIL"')]
        self.assertIn("if (tiles.len() >= 3)", geom)
        self.assertIn("tiles[0]", geom)
        self.assertIn("tiles[1]", geom)
        self.assertIn("tiles[2]", geom)
        self.assertIn("tiles[last - 2]", geom)
        self.assertIn("tiles[last - 1]", geom)
        self.assertIn("tiles[last]", geom)
        self.assertIn("AIMap.DistanceManhattan(tiles[0], tiles[1])", geom)
        self.assertIn("AIMap.DistanceManhattan(tiles[1], tiles[2])", geom)
        self.assertIn("AIMap.DistanceManhattan(tiles[last - 2], tiles[last - 1])", geom)
        self.assertIn("AIMap.DistanceManhattan(tiles[last - 1], tiles[last])", geom)
        fail_only = track_log[track_log.index("if (trackFailed > 0"):track_log.index('if ("lead" in planB)')]
        self.assertNotIn("h0=", fail_only)
        self.assertNotIn("d01=", fail_only)
        self.assertNotIn("t2=", fail_only)
        self.assertNotIn("d21=", fail_only)
        self.assertLess(track_at, execute.index("OpexRollback(tiles, planA, planB, null, null);"))
        stn_at = execute.index('OpexDecide("RAIL_STN_FAIL"')
        stn_block = execute[execute.rindex("if (!okA || !okB)", 0, stn_at):stn_at]
        self.assertIn("if (DECISION_LOG)", stn_block)
        self.assertLess(stn_at, execute.index("OpexRollback(null, planA, planB, null, null);"))
        self.assertIn("ok_a=", execute)
        self.assertIn("len_a=", execute)
        self.assertIn("len_b=", execute)

    def test_rail_attempt_logs_station_exit_crossings(self):
        """startx/endx sur chaque RAIL_ATTEMPT. -1 si le tracé n'est pas sur result."""
        record_at = self.task_rail.index("function OpexAI::_recordRailAttempt(")
        record = self.task_rail[record_at:self.task_rail.index("\nfunction ", record_at)]
        attempt_at = record.index('OpexDecide("RAIL_ATTEMPT"')
        attempt = record[attempt_at:record.index("if (result.ok)", attempt_at)]
        self.assertIn("if (DECISION_LOG)", record[:attempt_at])
        order = (
            "src=", "dst=", "kind=", "manh=", "pre=", "model=",
            "quote=", "actual=", "ok=", "reason=", "iters=", "ops=",
            "startx=", "endx=",
        )
        pos = -1
        for token in order:
            at = attempt.index(token)
            self.assertGreater(at, pos, token)
            pos = at
        self.assertIn('("startx" in result) ? result.startx : -1', attempt)
        self.assertIn('("endx" in result) ? result.endx : -1', attempt)
        self.assertNotIn("result.startx : 0", attempt)
        self.assertNotIn("result.endx : 0", attempt)

        rail = (ROOT / "ai/OpexAI/builder_rail.nut").read_text(encoding="utf-8")
        execute = rail[rail.index("function OpexExecuteRailPlan("):rail.index("\nfunction OpexBuildLine(")]
        cross = execute[execute.index("local tiles = plan.tiles;"):execute.index("if (RAIL_DEVIS)")]
        self.assertIn("if (DECISION_LOG)", cross)
        self.assertLess(cross.index("local crossStart = -1;"), cross.index("result.startx <-"))
        self.assertLess(cross.index("local crossEnd = -1;"), cross.index("result.endx <-"))
        self.assertIn("tiles != null && tiles.len() >= 2", cross)
        self.assertIn("tiles != null && tiles.len() >= 3", cross)
        self.assertIn("(AIMap.DistanceManhattan(tiles[0], tiles[1]) > 1) ? 1 : 0", cross)
        self.assertIn("(AIMap.DistanceManhattan(tiles[tail - 2], tiles[tail - 1]) > 1) ? 1 : 0", cross)
        self.assertIn("result.startx <- crossStart;", cross)
        self.assertIn("result.endx <- crossEnd;", cross)
        twin_at = rail.index("function OpexTestRailTrack(")
        twin = rail[twin_at:rail.index("\nfunction OpexBuildDepot(", twin_at)]
        self.assertNotIn("startx", twin)
        self.assertNotIn("endx", twin)
        self.assertNotIn("h0=", twin)

    def test_v89_throughput_interaction_documented_and_guarded(self):
        # Le worker absorbe le reliquat et V89 cède sous C80_RAIL_STOCK_WORKER
        self.assertIn("if (C80_RAIL_STOCK_WORKER) V89_RAIL_SEARCH_THROUGHPUT = false;", self.settings)
        # Et le worker possède sa boucle interne sur reliquat
        self.assertIn("minThreshold = (ai._v89EstimatedSliceOps > 1500) ? ai._v89EstimatedSliceOps : 1500;", self.orchestrator)

    def test_no_pending_under_gate_and_no_search_in_progress_when_plan_ready(self):
        # Quand un plan prêt existe, _railSearch != null ne bloque plus
        self.assertIn('RAIL_SEARCH_RESUMABLE && this._railSearch != null && !(("railPlan" in candidate) && candidate.railPlan != null)', self.task_rail)
        # Sous la porte, _startRailSearch n'est pas appelé depuis _tryBuildRailProject
        call_sites = [m.start() for m in re.finditer(r"this\._startRailSearch", self.task_rail)]
        self.assertEqual(len(call_sites), 3, "Il doit y avoir exactement 3 sites d'appel à this._startRailSearch")
        for idx in call_sites:
            preceding_context = self.task_rail[max(0, idx - 2000):idx]
            self.assertIn("C80_RAIL_STOCK_GATE", preceding_context)

    def test_traces_declared(self):
        required_traces = [
            "RAIL_STOCK_START",
            "RAIL_STOCK_DEPOSIT",
            "RAIL_STOCK_TIMEOUT",
            "RAIL_STOCK_EXPIRE",
            "RAIL_STOCK_CONSUME",
            "RAIL_STOCK_REVALIDATE_FAIL",
            "RAIL_STOCK_SELECT",
            "RAIL_STOCK_SKIP_BELOW_THRESHOLD",
            "RAIL_STOCK_SCORE",
            "RAIL_STOCK_REPAIR",
        ]
        for trace in required_traces:
            self.assertIn(f'"{trace}"', self.task_rail + self.task_projects + self.projects)

    def test_stock_contains_complete_project_and_selection_replays_each_pass(self):
        self.assertIn("project = readyProject", self.task_rail)
        self.assertIn("OpexProjectFromCandidate(candidate)", self.task_rail)
        self.assertIn("kept.push(entry.project)", self.projects)
        assembly = self.projects[self.projects.index('OpexC56TaskLog("STAGE_ENTER", "c56_stage_assembly"'):]
        self.assertNotRegex(assembly, r"foreach \(candidate in rail\.candidates\) \{\s*if \(C80_RAIL_STOCK_WORKER\)")
        self.assertIn("OpexReselectProjects(projects, capitalBudget, ai._abandonedPairs, ai._lines, ai._railReadyStock)", self.projects)
        self.assertIn("::OpexPromoteLiveDefensiveAir = ::OpexPromoteLiveDefensiveAirStock", self.main)
        self.assertIn("this._projects.railStockAI <- this", self.task_projects)
        self.assertIn("railStockFusionOpcodes", self.projects)
        self.assertIn("this._railReadyStock[pairKey].project != project", self.task_rail)

    def test_coarse_score_and_selection_threshold_contract(self):
        # 1. Calcul du fundScore papier avec exactement les fonctions de la sélection
        self.assertIn("local paperProject = OpexProjectFromCandidate(candidate);", self.task_rail)
        self.assertIn("local paperFinanceCapital = OpexProjectFinanceCapital(paperProject);", self.task_rail)
        self.assertIn("local paperProfit = C70_PROFIT_CALIBRATED ? OpexCalibratedProfit(paperProject) : paperProject.profitAnnual;", self.task_rail)
        self.assertIn("local coarseFundScore = OpexProjectScore(paperProfit, paperFinanceCapital);", self.task_rail)
        # 2. Seuil mémorisé du dernier projet financé de la dernière sélection non vide
        self.assertIn("local threshold = this._railStockLastFundedScore;", self.task_rail)
        self.assertIn("local thresholdDate = this._railStockLastFundedDate;", self.task_rail)
        self.assertIn("threshold > 0.0 && coarseFundScore < threshold", self.task_rail)
        self.assertIn("threshold_date=", self.task_rail)
        # 3. Suppression intégrale de bestUnfundedScore et selectionReduced
        self.assertNotIn("bestUnfundedScore", self.task_rail)
        self.assertNotIn("selectionReduced", self.task_rail)
        # 4. Mémoire transitoire vidée au chargement
        self.assertIn("this._railStockLastFundedScore = 0.0;", self.persist)
        self.assertIn("this._railStockLastFundedDate = -1;", self.persist)
        # 5. Mesure de fiabilité avant / après A*
        self.assertIn("RAIL_STOCK_SCORE", self.task_rail)
        self.assertIn("before=", self.task_rail)
        self.assertIn("after=", self.task_rail)

    def test_repair_instead_of_abandon_contract(self):
        # En cas d'échec de revalidation, tentative de relance A* pour la même paire
        self.assertIn("local started = this._startRailStockSearch(candidate, true, reval.reason);", self.task_rail)
        # Retrait uniquement si la recherche ne peut pas démarrer ou échoue
        self.assertIn("if (!started)", self.task_rail)
        self.assertIn("isRepair", self.task_rail)
        self.assertIn("repairReason", self.task_rail)
        self.assertIn("issue=repaired", self.task_rail)
        self.assertIn("issue=started", self.task_rail)

    def test_diagnostic_counts_ready_funded_built_and_merge_cost(self):
        events = extract("\n".join([
            "OPEX 1970-1-1 C56_TASK RAIL_STOCK_DEPOSIT src=1 dst=2",
            "OPEX 1970-1-2 C56_TASK RAIL_STOCK_SELECT ready=1 funded=1 merge_ops=47",
            "OPEX 1970-1-3 C56_TASK RAIL_STOCK_CONSUME src=1 dst=2 delay_days=2",
            "OPEX 1970-1-4 C56_TASK RAIL_STOCK_SKIP_BELOW_THRESHOLD src=1 dst=3 score=120 threshold=250 threshold_date=1970-1-1",
            "OPEX 1970-1-5 C56_TASK RAIL_STOCK_SCORE src=1 dst=2 before=300 after=280 diff=-20",
            "OPEX 1970-1-6 C56_TASK RAIL_STOCK_REPAIR src=1 dst=2 reason=track_blocked issue=started",
            "OPEX 1970-1-7 C56_TASK RAIL_STOCK_REPAIR src=1 dst=2 reason=track_blocked issue=repaired",
        ]))
        metrics = analyze_events(events)
        self.assertEqual(metrics["stock_ready_passes"], 1)
        self.assertEqual(metrics["stock_funded_passes"], 1)
        self.assertEqual(metrics["stock_built"], 1)
        self.assertEqual(metrics["stock_merge_ops"], [47])
        self.assertEqual(metrics["stock_skips_below_threshold"], 1)
        self.assertEqual(metrics["stock_repairs_count"], 2)
        self.assertEqual(metrics["stock_repairs_repaired"], 1)
        self.assertEqual(metrics["stock_repairs_by_issue"]["started"], 1)
        self.assertEqual(metrics["stock_repairs_by_issue"]["repaired"], 1)
        self.assertEqual(metrics["score_diff_avg"], -20.0)
        self.assertEqual(metrics["score_diffs"], [-20.0])
        self.assertEqual(metrics["ready_unfunded_details"], [])


if __name__ == "__main__":
    unittest.main()
