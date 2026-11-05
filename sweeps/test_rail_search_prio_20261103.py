"""RAIL-SEARCH-PRIO phase 1: settings interface and exact config OFF projection.

The behavioral files are owned by worker-1, not edited by this test worker.
This test uses structural contracts without running OpenTTD or Docker.
"""

# Compare historical contracts after the exact outer FLEET-ARB projection.
from fleet_arb_off import historical_read_bytes as fleet_read_bytes, historical_read_text as fleet_read_text

import hashlib
import json
import re
import unittest
from pathlib import Path

from rail_config_merge_witness import expected_off_sha


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
FIXTURE = json.loads(
    fleet_read_text(ROOT / "sweeps" / "fixtures" / "rail_search_prio_off_20261103.json", encoding="utf-8")
)


def source(name):
    return fleet_read_text(AI / name, encoding="utf-8")


def function_body(name, symbol):
    text = source(name)
    match = re.search(r"\bfunction\s+" + re.escape(symbol) + r"\s*\(", text)
    if not match:
        raise AssertionError(f"{name}: missing function {symbol}")
    brace = text.index("{", match.start())
    level = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            level += 1
        elif text[pos] == "}":
            level -= 1
            if level == 0:
                return text[match.start():pos + 1]
    raise AssertionError(f"{name}: unterminated function {symbol}")


def off_config_bytes(name, data=None):
    """Project later RAIL-LONG OFF, then only SEARCH-PRIO, to its frozen SHA."""
    from n75_mc_legacy import rail_long_config_off_bytes
    if data is None:
        data = fleet_read_bytes(AI / name)
    data = rail_long_config_off_bytes(name, data)
    for insertion in FIXTURE["insertions"][name]:
        fragment = insertion.encode("utf-8")
        if data.count(fragment) != 1:
            raise AssertionError(f"{name}: missing/duplicated opt-in insertion")
        data = data.replace(fragment, b"", 1)
    return data


class RailSearchPrioSettingsContracts(unittest.TestCase):
    def test_single_boolean_global_off_by_default(self):
        globals_pre = source("globals_pre.nut")
        self.assertEqual(len(re.findall(r"(?m)^RAIL_SEARCH_PRIO\s*<-\s*false;", globals_pre)), 1)
        self.assertNotRegex(globals_pre, r"(?m)^RAIL_SEARCH_PRIO\s*<-\s*true;")

    def test_declared_once_for_all_four_difficulties(self):
        info = source("info.nut")
        blocks = re.findall(r"AddSetting\s*\(\s*\{.*?\}\s*\);", info, flags=re.S)
        blocks = [block for block in blocks if 'name = "rail_search_prio"' in block]
        self.assertEqual(len(blocks), 1)
        setting = blocks[0]
        self.assertRegex(setting, r"\bmin_value\s*=\s*0\b")
        self.assertRegex(setting, r"\bmax_value\s*=\s*1\b")
        self.assertIn("flags = AICONFIG_BOOLEAN", setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            with self.subTest(difficulty=difficulty):
                self.assertRegex(setting, rf"\b{difficulty}_value\s*=\s*0\b")

    def test_setting_loaded_only_once_and_as_boolean(self):
        settings = source("settings.nut")
        self.assertEqual(settings.count('AIController.GetSetting("rail_search_prio")'), 1)
        self.assertRegex(
            settings,
            r"RAIL_SEARCH_PRIO\s*=\s*AIController\.GetSetting\(\"rail_search_prio\"\)\s*==\s*1;",
        )
        for name in ("task_rail.nut", "orchestrator.nut", "scheduler.nut"):
            self.assertNotIn('AIController.GetSetting("rail_search_prio")', source(name))

    def test_exact_additive_off_projection_preserves_existing_dirty_tree(self):
        self.assertEqual(set(FIXTURE["baseline_sha256"]), set(FIXTURE["insertions"]))
        for name, expected in FIXTURE["baseline_sha256"].items():
            with self.subTest(name=name):
                original = fleet_read_bytes(AI / name)
                projected = off_config_bytes(name, original)
                self.assertEqual(hashlib.sha256(projected).hexdigest(),
                                 expected_off_sha(name, "rail_search_prio_off", expected, original))
                self.assertNotIn(b"RAIL_SEARCH_PRIO", projected)
                self.assertNotIn(b"rail_search_prio", projected)
                self.assertNotEqual(original, projected)

    def test_settings_only_addition_no_global_rail_behavior_in_config(self):
        self.assertEqual(source("globals_pre.nut").count("RAIL_SEARCH_PRIO <-"), 1)
        self.assertEqual(source("settings.nut").count("RAIL_SEARCH_PRIO ="), 1)
        self.assertEqual(source("info.nut").count('name = "rail_search_prio"'), 1)
        self.assertNotIn("OpexWorkerCancel", "".join(source(n) for n in FIXTURE["insertions"]))


class RailSearchPrioBehaviorContracts(unittest.TestCase):
    """Static integration checks; worker-1 owns and edits all behavioral sources."""

    def test_search_owner_identity_and_elapsed_in_opt_in_logs(self):
        owner = function_body("task_rail.nut", "OpexRailSearchPrioOwner")
        fields = function_body("task_rail.nut", "OpexRailSearchPrioFields")
        log = function_body("task_rail.nut", "OpexRailSearchPrioLog")
        for kind in ('"stock"', '"project"', '"upgrade"', '"other"'):
            self.assertIn(kind, owner)
        for field in ('"owner="', '" kind="', '" days="', '" ticks="',
                      '" src="', '" dst="', '" cargo="', '" line="'):
            self.assertIn(field, fields, field)
        self.assertIn("AIDate.GetCurrentDate()", fields)
        self.assertIn("AIController.GetTick()", fields)
        self.assertIn("if (!RAIL_SEARCH_PRIO || !DECISION_LOG) return;", log)
        self.assertIn('OpexDecide("RAIL_SEARCH_PRIO"', log)

    def test_preemption_is_secondary_only_funded_and_not_same_stock_route(self):
        check = function_body("task_rail.nut", "OpexRailSearchPrioCanPreempt")
        self.assertIn("!RAIL_SEARCH_PRIO", check)
        # Prime clarified: both speculative stock and upgrade are secondary;
        # a primary/project search must NEVER be preempted.
        self.assertRegex(check, r'owner\s*!=\s*"stock"\s*&&\s*owner\s*!=\s*"upgrade"')
        self.assertIn('owner == "stock"', check)
        self.assertIn('owner == "upgrade"', check)
        self.assertIn('ai._activeWorker.kind != "rail_stock"', check)
        self.assertIn("OpexProjectFinanceCapital(project) > OpexAvailableCapital()", check)
        for field in ("old.src == next.src", "old.dst == next.dst",
                      "old.kind == next.kind", "old.cargo == next.cargo"):
            self.assertIn(field, check)

    def test_preempt_cancels_worker_before_releasing_search_and_keeps_ready_stock(self):
        cancel = function_body("task_rail.nut", "OpexRailSearchPrioPreemptStock")
        self.assertIn("OpexRailSearchPrioCanPreempt(ai, project)", cancel)
        self.assertIn("OpexWorkerCancel(worker)", cancel)
        self.assertIn("ai._activeWorker = null", cancel)
        self.assertIn("ai._railSearch = null", cancel)
        self.assertIn("ai._handleRailStockSearchCompleted()", cancel)
        self.assertLess(cancel.index("ai._handleRailStockSearchCompleted()"),
                        cancel.index("OpexWorkerCancel(worker)"))
        cancelled = cancel.index("OpexWorkerCancel(worker)")
        worker_released = cancel.index("ai._activeWorker = null", cancelled)
        self.assertLess(cancelled, worker_released)
        self.assertLess(worker_released, cancel.index("ai._railSearch = null", cancelled))
        self.assertNotRegex(cancel, r"_railReadyStock\s*(?:=|<-)")

    def test_project_discard_attributes_owner_and_calls_preempt_only_when_opted_in(self):
        build = function_body("task_rail.nut", "OpexAI::_tryBuildRailProject")
        self.assertIn("search_in_progress", build)
        self.assertIn("OpexRailSearchPrioPreemptStock(this, project)", build)
        self.assertRegex(build, r"local\s+prioPreempt\s*=\s*RAIL_SEARCH_PRIO\s*&&\s*searchBlocked")
        self.assertIn("OpexRailSearchPrioCanPreempt(this, project)", build)
        self.assertIn("if (prioPreempt && !OpexRailSearchPrioPreemptStock(this, project))", build)
        self.assertIn("OpexRailSearchPrioFields(this._railSearch)", build)
        self.assertIn("passDiscards.append", build)
        # No speculative A* is cancelled before abandoned-pair, vehicle-slot,
        # physical proximity, and cash checks complete.
        preempt = build.index("if (prioPreempt && !OpexRailSearchPrioPreemptStock")
        for guard in ("OpexAbandonedPairKey(candidate)",
                      "OpexRailVehicleSlotAvailable()", "this._tooClose(candidate)",
                      "local lowCash = (money < need)"):
            self.assertLess(build.index(guard), preempt, guard)

    def test_opt_in_reports_search_start_end_and_discard_owner(self):
        task = source("task_rail.nut")
        self.assertIn('OpexRailSearchPrioLog(this._railSearch, "start", "source=projects")', task)
        self.assertIn('OpexRailSearchPrioLog(this._railSearch, "start", "source=stock")', task)
        self.assertIn('OpexRailSearchPrioLog(this._railSearch, "start", "source=expand")', task)
        self.assertIn('OpexRailSearchPrioLog(state, "end", "outcome=" + slice.stop', task)
        self.assertIn('OpexRailSearchPrioLog(state, "end", "outcome=stock_timeout")', task)
        self.assertIn('OpexRailSearchPrioLog(this._railSearch, "blocked"', task)
        self.assertRegex(task, r'reason = "search_in_progress", extra = RAIL_SEARCH_PRIO\s*\?')
        # Historical RAIL_SEARCH lines remain intact when the new flag is OFF;
        # any attached owner/elapsed text is emitted through the opt-in path.
        self.assertIn('(RAIL_SEARCH_PRIO ? " " + OpexRailSearchPrioFields(state) : "")', task)

    def test_original_search_decisions_and_worker_registry_survive(self):
        task = source("task_rail.nut")
        orch = source("orchestrator.nut")
        self.assertIn('OpexDecide("RAIL_SEARCH", "type=resumable outcome="', task)
        self.assertIn('OpexRegisterWorker("rail_stock"', orch)
        self.assertIn('OpexRegisterWorker("rail_search"', orch)
        self.assertIn("OpexWorkerRailStockCancel(worker)", orch)


if __name__ == "__main__":
    unittest.main()
