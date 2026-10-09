#!/usr/bin/env python3
"""Contrats statiques de v131_rail_repair (reparation locale de trace rail stocke)."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def squirrel_code(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"//.*", "", src)
    return src


def function_body(src, signature):
    idx = src.index(signature)
    start = src.index("{", idx)
    depth = 0
    for i in range(start, len(src)):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[idx : i + 1]
    raise ValueError(f"accolade fermante introuvable pour {signature}")


REPAIR_HEADERS = (
    "function OpexV131RepairLog(",
    "function OpexV131PlanResult(",
    "function OpexV131SegmentBuilds(",
    "function OpexV131ScanBlocked(",
    "function OpexV131CountBlocked(",
    "function OpexV131RawRuns(",
    "function OpexV131MergedRuns(",
    "function OpexV131OnPlatform(",
    "function OpexV131PlatformCargoOk(",
    "function OpexV131PlatformsOverlap(",
    "function OpexV131ConsiderShift(",
    "function OpexV131SidewaysShift(",
    "function OpexV131PickFresh(",
    "function OpexV131FindShift(",
    "function OpexV131PerpOffsets(",
    "function OpexV131CanBranchOut(",
    "function OpexV131CanBranchIn(",
    "function OpexV131PlanAnchorRun(",
    "function OpexV131IgnoreForRun(",
    "function OpexV131MakeFinder(",
    "function OpexV131DetectSpliceMode(",
    "function OpexV131PathAnchors(",
    "function OpexV131SplicePrefix(",
    "function OpexV131SpliceSuffix(",
    "function OpexV131SpliceSpan(",
    "function OpexV131ApplySplice(",
    "function OpexV131RebuildStructures(",
    "function OpexV131KeepStructures(",
    "function OpexV131StationsBuild(",
    "function OpexV131WriteRepairedPlan(",
    "function OpexAI::_v131RepairIsPending(",
    "function OpexAI::_v131RepairExhausted(",
    "function OpexAI::_v131DropDuplicateOwnRail(",
    "function OpexAI::_v131PlanRepairs(",
    "function OpexAI::_v131TryStartRepair(",
    "function OpexAI::_v131KickRepair(",
    "function OpexAI::_v131FailRepair(",
    "function OpexAI::_v131CommitRepair(",
    "function OpexAI::_v131OnRepairSliceDone(",
)


class TestV131RailRepair(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = source("info.nut")
        cls.settings = source("settings.nut")
        cls.globals = source("globals_pre.nut")
        cls.rail = source("task_rail.nut")
        cls.rail_code = squirrel_code(cls.rail)
        cls.reval = function_body(
            cls.rail, "function OpexAI::_revalidateRailStockPlan("
        )
        cls.start = function_body(
            cls.rail, "function OpexAI::_v131TryStartRepair("
        )
        cls.plan = function_body(
            cls.rail, "function OpexAI::_v131PlanRepairs("
        )
        cls.scan = function_body(cls.rail, "function OpexV131ScanBlocked(")
        cls.merged = function_body(cls.rail, "function OpexV131MergedRuns(")
        cls.anchors = function_body(cls.rail, "function OpexV131PlanAnchorRun(")
        cls.cargo = function_body(cls.rail, "function OpexV131PlatformCargoOk(")
        cls.log = function_body(cls.rail, "function OpexV131RepairLog(")
        cls.dup = function_body(
            cls.rail, "function OpexAI::_v131DropDuplicateOwnRail("
        )

    def test_setting_default_zero_all_difficulties(self):
        block = self.info[self.info.index('name = "v131_rail_repair"') :]
        block = block[: block.index("})")]
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, level + r"_value = 0\b")

    def test_setting_read_once(self):
        self.assertEqual(self.settings.count('GetSetting("v131_rail_repair")'), 1)
        self.assertIn(
            'V131_RAIL_REPAIR = AIController.GetSetting("v131_rail_repair") != 0;',
            self.settings,
        )
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn(
                'GetSetting("v131_rail_repair")',
                path.read_text(encoding="utf-8"),
                path.name,
            )
        self.assertRegex(self.globals, r"V131_RAIL_REPAIR <- false;")
        self.assertRegex(self.globals, r"V131_REPAIR_MAX_TILES <- 35;")
        self.assertRegex(self.globals, r"V131_REPAIR_MAX_RUNS <- 3;")
        self.assertRegex(self.globals, r"V131_REPAIR_MAX_ITERS <- 2500;")

    def test_duplicate_guard_threshold_at_least_40_percent(self):
        gate = self.reval.index("if (!V131_RAIL_REPAIR)")
        dup = self.reval.index("this._v131DropDuplicateOwnRail(")
        station = self.reval.index("AIRail.BuildRailStation")
        self.assertLess(gate, dup)
        self.assertIn('reason = "duplicate_own_rail"', self.reval)
        self.assertIn("own * 10 >= tiles.len() * 4", self.dup)
        self.assertIn("AIRail.IsRailTile", self.dup)
        self.assertIn("AICompany.ResolveCompanyID", self.dup)
        self.assertIn('OpexV131RepairLog(candidate, "duplicate"', self.dup)

    def test_clean_unmodified_path_when_setting_zero(self):
        self.assertIn("if (!V131_RAIL_REPAIR)", self.reval)
        zero_branch = self.reval[self.reval.index("if (!V131_RAIL_REPAIR)") : self.reval.index("/* V131_RAIL_REPAIR actif")]
        self.assertIn('return { ok = false, reason = "station_blocked" };', zero_branch)
        self.assertIn('reason = "track_blocked"', zero_branch)
        self.assertIn('return { ok = false, reason = "depot_blocked" };', zero_branch)
        self.assertIn('return { ok = true, reason = "ok" };', zero_branch)
        self.assertNotIn("v131", zero_branch)

    def test_merged_runs_fuses_close_obstacles(self):
        self.assertIn("nextRun.start - cur.end - 1 <= 6", self.merged)
        self.assertIn("OpexV131MergedRuns", self.plan)

    def test_adaptive_anchor_selection(self):
        self.assertIn("start <= 3", self.anchors)
        self.assertIn("planA.station_exit", self.anchors)
        self.assertIn("planA.lead", self.anchors)
        self.assertIn("end >= n - 4", self.anchors)
        self.assertIn("planB.lead", self.anchors)
        self.assertIn("planB.station_exit", self.anchors)
        self.assertIn("OpexV131CanBranchOut", self.anchors)
        self.assertIn("OpexV131CanBranchIn", self.anchors)
        self.assertIn('mode = "full"', self.anchors)
        self.assertIn('mode = "prefix"', self.anchors)
        self.assertIn('mode = "suffix"', self.anchors)
        self.assertIn('mode = "span"', self.anchors)

    def test_adaptive_iteration_budget(self):
        self.assertIn("planned.blockedTiles * 40", self.start)
        self.assertIn("dist * 20", self.start)
        self.assertIn("budget > V131_REPAIR_MAX_ITERS", self.start)

    def test_callers_keep_plan_only_while_repair_is_pending(self):
        prep = self.rail.index("if (c121PrepPlan)")
        prep_drop = self.rail.index("this._c121RailPrepDropStock(", prep)
        prep_pending = self.rail.index(
            'reval.reason == "v131_repair_pending"', prep
        )
        self.assertLess(prep_pending, prep_drop)
        self.assertLess(self.rail.index("if (V131_RAIL_REPAIR", prep), prep_pending)
        stock = self.rail.index(
            "this._revalidateRailStockPlan(candidate, entry.plan)"
        )
        stock_pending = self.rail.index(
            'reval.reason == "v131_repair_pending"', stock
        )
        stock_search = self.rail.index("this._startRailStockSearch(", stock)
        self.assertLess(stock_pending, stock_search)
        self.assertIn("if (V131_RAIL_REPAIR", self.rail[stock:stock_pending])
        self.assertNotIn("duplicate_own_rail", self.rail[prep:prep_drop])
        self.assertNotIn("duplicate_own_rail", self.rail[stock:stock_search])

    def test_repair_search_multi_slice_progress(self):
        continue_body = function_body(
            self.rail, "function OpexAI::_continueRailSearch("
        )
        self.assertIn('if (V131_RAIL_REPAIR && state.kind == "v131_repair")', continue_body)
        self.assertIn("if (!slice.done) return;", continue_body)
        self.assertIn("this._v131OnRepairSliceDone(state, slice);", continue_body)

    def test_slot_busy_handled_without_stock_drop(self):
        self.assertIn('return "slot_busy";', self.start)
        self.assertIn('reason = "slot_busy"', self.reval)
        self.assertIn('reval.reason == "slot_busy"', self.rail)

    def test_repair_failure_and_phase_management(self):
        on_slice = function_body(
            self.rail, "function OpexAI::_v131OnRepairSliceDone("
        )
        self.assertIn('slice.stop == "ABND"', on_slice)
        self.assertIn('failReason = "budget_exhausted"', on_slice)
        self.assertIn('slice.stop == "DEAD"', on_slice)
        self.assertIn('failReason = "deadline_exhausted"', on_slice)
        fail_body = function_body(
            self.rail, "function OpexAI::_v131FailRepair("
        )
        self.assertIn('state.phase = "done";', fail_body)
        commit_body = function_body(
            self.rail, "function OpexAI::_v131CommitRepair("
        )
        self.assertIn('state.phase = "done";', commit_body)

    def test_repair_uses_the_single_existing_slot(self):
        self.assertIn('kind = "v131_repair"', self.start)
        self.assertIn("segmented = null", self.start)
        self.assertIn("this._railSearch =", self.start)
        self.assertIn("isRepair = true", self.start)
        kick = function_body(self.rail, "function OpexAI::_v131KickRepair(")
        self.assertIn("this._continueRailSearch()", kick)
        self.assertIn("this._v131KickRepair(", self.reval)
        self.assertNotIn("isStockSearch", self.start)
        self.assertNotIn("_railRepairSearch", self.start)
        self.assertNotIn("_activeWorker =", self.start)
        self.assertNotIn('phase = "build"', self.start)

    def test_station_shift_and_fresh_platform_pick(self):
        self.assertIn("OpexJoinPlatformPlans", function_body(
            self.rail, "function OpexV131FindShift("
        ))
        self.assertIn("OpexRailPlatformPlans", self.plan)
        self.assertIn("OpexRailPlatformCargoValue", self.cargo)
        self.assertIn("value > 0", self.cargo)
        self.assertIn("value >= 8", self.cargo)
        pick = function_body(self.rail, "function OpexV131PickFresh(")
        self.assertIn("dist > 16", pick)

    def test_log_format_and_decision_gate(self):
        self.assertIn("if (!DECISION_LOG) return;", self.log)
        self.assertIn('OpexDecide("V131_REPAIR"', self.log)
        for field in ("action=", "runs=", "tiles=", "iters=", "ops=", "src=", "dst="):
            self.assertIn(field, self.log)
        joined = "\n".join(function_body(self.rail, header) for header in REPAIR_HEADERS)
        for action in ("start", "ok", "fail", "fallback", "duplicate"):
            self.assertIn('"' + action + '"', joined)

    def test_no_nested_functions_or_reserved_ids(self):
        for header in REPAIR_HEADERS:
            body = function_body(self.rail_code, header)
            inner = body[body.index("{") + 1 :]
            self.assertNotIn("function ", inner, header)
            self.assertNotRegex(inner, r"\bclone\b", header)
            self.assertNotRegex(inner, r"\bbase\b", header)
            self.assertNotRegex(inner, r"\bparent\b", header)
            self.assertNotRegex(inner, r"\byield\b", header)
            self.assertNotRegex(inner, r"\bdelete\b", header)
            self.assertNotRegex(inner, r"\bstatic\b", header)
            self.assertNotRegex(inner, r"\benum\b", header)
            self.assertNotRegex(inner, r"\bconst\b", header)

    def test_braces_balanced(self):
        for name in ("task_rail.nut", "settings.nut", "globals_pre.nut", "info.nut"):
            code = squirrel_code(source(name))
            self.assertEqual(code.count("{"), code.count("}"), name)
            self.assertEqual(code.count("("), code.count(")"), name)


if __name__ == "__main__":
    unittest.main()
