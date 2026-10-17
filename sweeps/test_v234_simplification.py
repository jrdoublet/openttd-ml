"""Retired town/road policies: static runtime and legacy-save contracts."""
import re
import unittest
from pathlib import Path

from campaign_freeze import effective_ai_settings, parse_ai_settings

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
RETIRED = """town_growth town_growth_plan_memo town_growth_skip_noop
town_growth_roi_gate c80_worker_town road_finance_unbias_p0
road_finance_gate_shadow_p0 road_quote_components_shadow_p0 road_time_scaled_cap
road_loading_fix road_pax_dwell_days policy_vehicle_events project_top_k_dynamic
v139_feeder_bus""".split()
# Match strings and comments together: // and /* inside strings are ordinary text.
NON_CODE = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27')


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class V234Simplification(unittest.TestCase):
    def test_retired_settings_cannot_be_requested(self):
        defaults = parse_ai_settings(AI / "info.nut")
        for name in RETIRED:
            with self.subTest(name=name):
                self.assertNotIn(name, defaults)
                self.assertNotIn('"' + name + '"', source("settings.nut"))
                with self.assertRaises(ValueError):
                    effective_ai_settings(AI / "info.nut", ((name, 1),))

    def test_dwell_is_six_days_and_never_assigned(self):
        self.assertIn("const ROAD_PAX_STOP_DWELL_DAYS = 6;", source("globals_pre.nut"))
        self.assertIn('local dwellDays = (kind == "pax") ? ROAD_PAX_STOP_DWELL_DAYS : 0;', source("economy.nut"))
        self.assertNotIn("ROAD_PAX_STOP_DWELL_DAYS", source("settings.nut"))

    def test_no_town_construction_or_worker(self):
        self.assertFalse((AI / "task_town.nut").exists())
        for name in ("main.nut", "scheduler.nut", "scheduler_tasks.nut", "orchestrator.nut"):
            self.assertNotIn("_tryTownGrowth", source(name))
            self.assertNotIn("_dispatchTownGrowth", source(name))
            self.assertNotIn("OpexWorkerTownGrowth", source(name))
        self.assertNotIn('OpexRegisterWorker("town_growth"', source("orchestrator.nut"))

    def test_legacy_save_keys_and_numeric_cursor_remain_compatible(self):
        self.assertIn('{ name = "town_growth", dueCycle = 2147483647, enabled = false }', source("main.nut"))
        persist = source("persist.nut")
        self.assertIn('if (kind == "town_growth") return null;', persist)
        for field in ("taskCursor", "taskDue", "vehiclesToRetire", "unprofitableStreaks"):
            self.assertIn('"' + field + '" in data', persist)
        self.assertIn('line.purpose == "town_growth"', source("task_report.nut"))
        self.assertIn("ai._markTownGrowthRejected(line.srcTown);", source("task_report.nut"))

    def test_no_undeclared_bare_uppercase_global(self):
        code = "\n".join(NON_CODE.sub(" ", p.read_text(encoding="utf-8")) for p in AI.rglob("*.nut"))
        declared = set(re.findall(r"\b([A-Z][A-Z0-9_]*)\s*<-", code))
        declared.update(re.findall(r"\b(?:const|local)\s+([A-Z][A-Z0-9_]*)", code))
        # These two names are supplied by the NoAI settings API.
        declared.update(("AICONFIG_BOOLEAN", "CONFIG_BOOLEAN"))
        reads = set(re.findall(r"(?<![.\w])([A-Z][A-Z0-9_]{1,})\b", code))
        self.assertEqual(sorted(reads - declared), [])

    def test_squirrel_delimiters_balance(self):
        for path in AI.rglob("*.nut"):
            with self.subTest(path=path.name):
                code = NON_CODE.sub(" ", path.read_text(encoding="utf-8"))
                stack = []
                for token in re.findall(r"[{}\[\]()]", code):
                    if token in "{[(":
                        stack.append(token)
                    else:
                        self.assertTrue(stack, token)
                        self.assertEqual(stack.pop(), {"}": "{", "]": "[", ")": "("}[token])
                self.assertEqual(stack, [])

    def test_retired_helpers_have_no_remaining_calls(self):
        code = "\n".join(NON_CODE.sub(" ", p.read_text(encoding="utf-8")) for p in AI.rglob("*.nut"))
        for name in ("OpexRoadPaxUniqueMonthly", "OpexRoadCatchmentOverlapFrac",
                     "OpexRoadFleetVehicleCap", "OpexRoadQuotePlanComponents",
                     "OpexBuildFeederCandidates", "OpexV139SaveUnjoinedStops"):
            self.assertNotIn(name, code)
