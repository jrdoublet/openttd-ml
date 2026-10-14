#!/usr/bin/env python3
"""V205: rabattements ferroviaires en transfert vers une gare d'origine fret existante."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_setting_specs  # noqa: E402


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    needle = "function " + name
    if needle not in source:
        needle = "function OpexAI::" + name
    start = source.index(needle)
    brace = source.index("{", start)
    depth = 1
    idx = brace + 1
    while depth > 0 and idx < len(source):
        ch = source[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        idx += 1
    return source[start:idx]


class TestV205Setting(unittest.TestCase):
    def test_setting_declared_in_info(self):
        info = _read("info.nut")
        self.assertIn('"v205_rail_transfer"', info)
        spec = parse_ai_setting_specs(AI / "info.nut")["v205_rail_transfer"]
        self.assertEqual(spec["default"], 0)
        self.assertEqual((spec["min_value"], spec["max_value"]), (0, 1))
        self.assertEqual(spec["step_size"], 1)

    def test_setting_four_zeroes(self):
        info = _read("info.nut")
        idx = info.index('"v205_rail_transfer"')
        block = info[idx:info.index("});", idx)]
        self.assertIn("easy_value = 0", block)
        self.assertIn("medium_value = 0", block)
        self.assertIn("hard_value = 0", block)
        self.assertIn("custom_value = 0", block)
        self.assertIn("AICONFIG_BOOLEAN", block)

    def test_global_pre(self):
        globals_pre = _read("globals_pre.nut")
        self.assertIn("V205_RAIL_TRANSFER <- false;", globals_pre)

    def test_settings_loaded_once(self):
        settings = _read("settings.nut")
        self.assertEqual(settings.count('GetSetting("v205_rail_transfer")'), 1)
        self.assertIn('V205_RAIL_TRANSFER = AIController.GetSetting("v205_rail_transfer") != 0;', settings)


class TestV205CandidateGeneration(unittest.TestCase):
    def setUp(self):
        self.candidates = _read("candidates.nut")

    def test_transfer_generation_called_in_freight_candidates(self):
        body = _function_body(self.candidates, "OpexFreightCandidates")
        self.assertIn("if (V205_RAIL_TRANSFER && lines != null)", body)
        self.assertIn("OpexRailTransferFeederCandidates(", body)

    def test_transfer_feeder_candidate_generator_guards(self):
        body = _function_body(self.candidates, "OpexRailTransferFeederCandidates")
        self.assertIn("if (!V205_RAIL_TRANSFER || lines == null) return;", body)
        # Line L filters
        self.assertIn('line.kind != "freight"', body)
        self.assertIn('line.mode != "rail"', body)
        self.assertIn('"lineId" in line', body)
        self.assertIn('"stationA" in line', body)
        self.assertIn('"stationB" in line', body)
        self.assertIn('"platformA" in line', body)
        self.assertIn('"cargo" in line', body)
        # Cannot chain feeders: line L cannot be a feeder itself
        self.assertIn('"v205TransferTo" in line', body)
        # Distance bands
        self.assertIn("ownDist < 25 || ownDist > 90", body)
        self.assertIn("totalDist <= lineDist * 0.8", body)
        # Unserved check
        self.assertIn("OpexOriginService(", body)
        # Separation from existing line origin and station
        self.assertIn("ORIGIN_SEPARATION", body)
        self.assertIn("MIN_SEPARATION", body)

    def test_line_capacity_calculation_and_capping(self):
        body = _function_body(self.candidates, "OpexRailTransferFeederCandidates")
        # Capacity from trains, wagons, oneWayDays, wagon capacity
        self.assertIn("monthlyCapacityL = (numTrains * lineWagons * wagonCap * (30.0 / (2.0 * lineOneWayDays))).tointeger();", body)
        # Tracks already loaded volume
        self.assertIn("alreadyLoaded", body)
        self.assertIn("remainingCapacity = monthlyCapacityL - alreadyLoaded;", body)
        self.assertIn("if (remainingCapacity <= 0) continue;", body)
        # Production capped by remaining capacity
        self.assertIn("feederMonthly = sourceMonthly > remainingCapacity ? remainingCapacity : sourceMonthly;", body)

    def test_candidate_markings(self):
        body = _function_body(self.candidates, "OpexRailTransferFeederCandidates")
        self.assertIn("candidate.v205TransferTo <- line.lineId;", body)
        self.assertIn("candidate.joinDest <- stationA;", body)
        self.assertIn("candidate.v205TotalDist <- totalDist;", body)
        self.assertIn("candidate.v205OwnDist <- ownDist;", body)
        self.assertIn("candidate.joinPlatform <- line.platformA;", body)
        self.assertIn("candidate.joinStationId <- stId;", body)
        self.assertIn("candidate.joinLineId <- line.lineId;", body)
        self.assertIn('candidate.joinEnd <- "B";', body)
        self.assertIn("candidate.originServed = true;", body)

    def test_feeder_economics(self):
        body = _function_body(self.candidates, "OpexRailTransferFeederCandidates")
        # Revenue on total distance and total days
        self.assertIn("totalOneWayDays = candidate.oneWayDays + lineOneWayDays;", body)
        self.assertIn("totalIncomeDays = OpexCeilDiv(totalOneWayDays, 1);", body)
        self.assertIn("unitIncome = AICargo.GetCargoIncome(cargo, totalDist, totalIncomeDays);", body)
        self.assertIn("candidate.revenueAnnual = (12 * candidate.carried * unitIncome).tointeger();", body)
        # Capital deduction for joined destination station
        self.assertIn("savedCost = candidate.platformLength * catalog.costStation;", body)
        self.assertIn("candidate.capital -= savedCost;", body)
        # ROI and ratios recalculated
        self.assertIn("candidate.profitAnnual = candidate.revenueAnnual - candidate.runningAnnual - candidate.amortAnnual;", body)
        self.assertIn("candidate.roi = (candidate.profitAnnual > 0) ? (candidate.profitAnnual * 1000) / candidate.capital : 0;", body)
        self.assertIn("candidate.opcodeRatio = (candidate.profitAnnual * 1000) / iterations;", body)

    def test_decision_log_gen(self):
        body = _function_body(self.candidates, "OpexRailTransferFeederCandidates")
        self.assertIn('OpexDecide("V205", "step=gen ok=1 line=" + line.lineId + " feeder=-1 cargo=" + cargo + " total_dist=" + totalDist + " own_dist=" + ownDist);', body)


class TestV205Construction(unittest.TestCase):
    def setUp(self):
        self.builder = _read("builder_rail.nut")
        self.task_rail = _read("task_rail.nut")

    def test_join_dest_strict_and_no_fallback(self):
        body = _function_body(self.builder, "OpexRailPlatformPlans")
        # Missing platform/station guard
        self.assertIn('V205_RAIL_TRANSFER && ("v205TransferTo" in candidate)', body)
        self.assertIn('OpexDecide("V205", "step=join_fail ok=0 line=" + candidate.v205TransferTo', body)
        # strictOriginReuseJoin enabled for V205
        self.assertIn('if (V205_RAIL_TRANSFER && ("v205TransferTo" in candidate)) {\n      strictOriginReuseJoin = true;\n    }', body)
        # Guard before search ensures no fallback to direct line
        free_search = body.index("for (local length = wanted; length >= floor; length--)")
        v205_guard = body.index('/* V205 : pas de repli en ligne directe si jointure impossible */')
        self.assertLess(v205_guard, free_search)

    def test_feeder_train_orders(self):
        body = _function_body(self.builder, "OpexBuildTrains")
        # Takes isTransferFeeder and v205Context
        self.assertIn("isTransferFeeder = false, v205Context = null", body)
        # Source full load
        self.assertIn("flagsA = ((kind == \"pax\" && !PAX_FULL_LOAD) ? AIOrder.OF_NONE : AIOrder.OF_FULL_LOAD_ANY) | nonstopFlag;", body)
        # Destination transfer and no load
        self.assertIn("destFreightFlags = AIOrder.OF_TRANSFER | AIOrder.OF_NO_LOAD;", body)
        # Order decision log
        self.assertIn('OpexDecide("V205", "step=orders ok=1 line="', body)

    def test_execute_rail_plan_passes_v205_context(self):
        exec_plan = _function_body(self.builder, "OpexExecuteRailPlan")
        self.assertIn('local isTransferFeeder = V205_RAIL_TRANSFER && ("v205TransferTo" in candidate);', exec_plan)
        self.assertIn("isTransferFeeder, v205Ctx);", exec_plan)

    def test_task_rail_build_logging_and_line_fields(self):
        record_body = _function_body(self.task_rail, "_recordRailAttempt")
        self.assertIn('OpexDecide("V205", "step=build ok="', record_body)
        self.assertIn('"v205TransferTo" in candidate', record_body)
        self.assertIn('v205TransferTo = ("v205TransferTo" in candidate) ? candidate.v205TransferTo : -1,', record_body)
        self.assertIn('joinDest = ("joinDest" in candidate) ? candidate.joinDest : null,', record_body)
        self.assertIn('v205TotalDist = ("v205TotalDist" in candidate) ? candidate.v205TotalDist : -1,', record_body)
        self.assertIn('v205OwnDist = ("v205OwnDist" in candidate) ? candidate.v205OwnDist : -1,', record_body)


class TestV205Separation(unittest.TestCase):
    def setUp(self):
        self.lines = _read("lines.nut")
        self.projects_gen = _read("projects_generation.nut")

    def test_too_close_handles_v205_feeder(self):
        body = _function_body(self.lines, "_tooClose")
        self.assertIn("V205_RAIL_TRANSFER", body)
        self.assertIn('"v205TransferTo" in candidate', body)
        self.assertIn('"joinDest" in candidate', body)
        self.assertIn('if (isV205Feeder && entry[0] == "B") continue;', body)

    def test_cached_proximity_handles_v205_feeder(self):
        body = _function_body(self.projects_gen, "OpexRailCachedProximity")
        self.assertIn("V205_RAIL_TRANSFER", body)
        self.assertIn('"v205TransferTo" in candidate', body)
        self.assertIn('"joinDest" in candidate', body)
        self.assertIn('if (isV205Feeder && entry[0] == "B") continue;', body)


class TestV205Invariants(unittest.TestCase):
    def test_no_forbidden_keywords(self):
        candidates = _function_body(_read("candidates.nut"), "OpexRailTransferFeederCandidates")
        for kw in ("clone", "parent", "base"):
            self.assertNotIn(kw, candidates, f"Forbidden keyword {kw} found in OpexRailTransferFeederCandidates")

    def test_key_in_table_guards(self):
        candidates = _function_body(_read("candidates.nut"), "OpexRailTransferFeederCandidates")
        for key in ('"kind"', '"mode"', '"lineId"', '"stationA"', '"stationB"', '"platformA"', '"cargo"', '"originA"'):
            self.assertIn(f"{key} in line", candidates)


if __name__ == "__main__":
    unittest.main()
