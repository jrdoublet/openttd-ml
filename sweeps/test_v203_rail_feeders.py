#!/usr/bin/env python3
"""V203: rabattements ferroviaires (feeders) vers nos gares sources fret."""
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


class TestV203Setting(unittest.TestCase):
    def test_setting_declared_in_info(self):
        info = _read("info.nut")
        self.assertIn('"v203_rail_feeders"', info)
        spec = parse_ai_setting_specs(AI / "info.nut")["v203_rail_feeders"]
        self.assertEqual(spec["default"], 0)
        self.assertEqual((spec["min_value"], spec["max_value"]), (0, 1))
        self.assertEqual(spec["step_size"], 1)

    def test_setting_four_zeroes(self):
        info = _read("info.nut")
        idx = info.index('"v203_rail_feeders"')
        block = info[idx:info.index("});", idx)]
        self.assertIn("easy_value = 0", block)
        self.assertIn("medium_value = 0", block)
        self.assertIn("hard_value = 0", block)
        self.assertIn("custom_value = 0", block)
        self.assertIn("AICONFIG_BOOLEAN", block)

    def test_global_pre(self):
        globals_pre = _read("globals_pre.nut")
        self.assertIn("V203_RAIL_FEEDERS <- false;", globals_pre)

    def test_settings_loaded_once(self):
        settings = _read("settings.nut")
        self.assertEqual(settings.count('GetSetting("v203_rail_feeders")'), 1)
        self.assertIn('V203_RAIL_FEEDERS = AIController.GetSetting("v203_rail_feeders") != 0;', settings)


class TestV203CandidateGeneration(unittest.TestCase):
    def setUp(self):
        self.candidates = _read("candidates.nut")

    def test_feeder_generation_under_setting_in_freight_path(self):
        body = _function_body(self.candidates, "OpexFreightCandidates")
        self.assertIn("if (V203_RAIL_FEEDERS && lines != null)", body)
        self.assertIn("OpexRailFeederCandidates(", body)

    def test_feeder_candidate_generator_logic(self):
        body = _function_body(self.candidates, "OpexRailFeederCandidates")
        self.assertIn("if (!V203_RAIL_FEEDERS || lines == null) return;", body)
        # Filters existing lines: freight rail lines with valid stationB
        self.assertIn('line.kind != "freight"', body)
        self.assertIn('line.mode != "rail"', body)
        self.assertIn('"stationB" in line', body)
        self.assertIn('"cargo" in line', body)
        # Distance band: <= 100 and >= 20
        self.assertIn("dist < 20 || dist > 100", body)
        # Unserved check
        self.assertIn("OpexOriginService(", body)
        # Distinct origin from existing line
        self.assertIn("ORIGIN_SEPARATION", body)
        # Candidate marking
        self.assertIn("candidate.feederOf <- line.lineId;", body)
        self.assertIn("candidate.joinDest <- destTile;", body)
        self.assertIn("candidate.joinPlatform <- line.platformB;", body)
        self.assertIn('candidate.joinEnd <- "B";', body)
        self.assertIn("candidate.originServed = true;", body)

    def test_feeder_capital_discount(self):
        body = _function_body(self.candidates, "OpexRailFeederCandidates")
        # Capital deducts destination station
        self.assertIn("candidate.platformLength * catalog.costStation", body)
        self.assertIn("candidate.capital -=", body)
        self.assertIn("candidate.roi =", body)

    def test_feeder_decision_log_gen(self):
        body = _function_body(self.candidates, "OpexRailFeederCandidates")
        self.assertIn('OpexDecide("V203", "step=gen ok=1 line=" + line.lineId + " cargo=" + cargo);', body)


class TestV203Construction(unittest.TestCase):
    def setUp(self):
        self.builder = _read("builder_rail.nut")
        self.task_rail = _read("task_rail.nut")

    def test_join_dest_uses_join_platform_plans(self):
        body = _function_body(self.builder, "OpexRailPlatformPlans")
        self.assertIn('"joinDest" in candidate', body)
        self.assertIn("OpexJoinPlatformPlans(", body)

    def test_join_failure_fallback_to_normal_construction(self):
        body = _function_body(self.builder, "OpexRailPlatformPlans")
        # strictOriginReuseJoin must be excluded for joinDest so it can fall back
        self.assertIn('!("joinDest" in candidate)', body)
        # On join failure, logs join_fail and falls through to normal search
        self.assertIn('OpexDecide("V203", "step=join_fail ok=0 line=" + lineId + " cargo=" + cargo);', body)
        free_search = body.index("for (local length = wanted; length >= floor; length--)")
        strict_check = body.index("if (strictOriginReuseJoin)")
        self.assertLess(strict_check, free_search)

    def test_build_decision_log(self):
        self.assertIn('OpexDecide("V203", "step=build ok=1 line=" + fLineId + " cargo=" + candidate.cargo);', self.task_rail)
        self.assertIn('OpexDecide("V203", "step=build ok=0 line=" + fLineId + " cargo=" + candidate.cargo);', self.task_rail)


class TestV203LineSeparation(unittest.TestCase):
    def setUp(self):
        self.lines = _read("lines.nut")
        self.projects_gen = _read("projects_generation.nut")

    def test_too_close_handles_v203_feeder(self):
        body = _function_body(self.lines, "_tooClose")
        self.assertIn("V203_RAIL_FEEDERS", body)
        self.assertIn('"joinDest" in candidate', body)
        self.assertIn('"feederOf" in candidate', body)
        self.assertIn('if (isV203Feeder && entry[0] == "B") continue;', body)

    def test_cached_proximity_handles_v203_feeder(self):
        body = _function_body(self.projects_gen, "OpexRailCachedProximity")
        self.assertIn("V203_RAIL_FEEDERS", body)
        self.assertIn('"joinDest" in candidate', body)
        self.assertIn('"feederOf" in candidate', body)
        self.assertIn('if (isV203Feeder && entry[0] == "B") continue;', body)


class TestV203Invariants(unittest.TestCase):
    def test_no_forbidden_keywords(self):
        candidates = _function_body(_read("candidates.nut"), "OpexRailFeederCandidates")
        for kw in ("clone", "parent", "base"):
            self.assertNotIn(kw, candidates, f"Forbidden keyword {kw} found in OpexRailFeederCandidates")

    def test_key_in_table_guards(self):
        candidates = _function_body(_read("candidates.nut"), "OpexRailFeederCandidates")
        # Every read of optional fields is protected by 'in'
        for key in ('"kind"', '"mode"', '"lineId"', '"stationB"', '"cargo"', '"originA"', '"stationA"', '"platformB"'):
            self.assertIn(f"{key} in line", candidates)


if __name__ == "__main__":
    unittest.main()
