"""V244 : chemin V184 permanent a une recherche ; contrats de rechargement."""
#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# rebasé le 24/10 : de8e1abe (résolution ROOT relative à __file__ pour portabilité lors de l'exécution depuis sweeps)
ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_setting_specs  # noqa: E402


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("unterminated " + name)


class Declaration(unittest.TestCase):
    def test_setting_removed(self):
        self.assertNotIn("v184_rail_search_slots", parse_ai_setting_specs(AI / "info.nut"))

    def test_global_removed(self):
        self.assertNotIn("V184_RAIL_SEARCH_SLOTS", _read("globals_pre.nut"))

    def test_settings_read_removed(self):
        self.assertNotIn("v184_rail_search_slots", _read("settings.nut"))


class SingleSearchContract(unittest.TestCase):
    def test_slot_state_retained_for_reset(self):
        self.assertIn("_v184RailSlots = null;", _read("main.nut"))
        self.assertIn("_v184SlotCursor = 0;", _read("main.nut"))

    def test_start_initializes(self):
        self.assertIn("this._v184InitRailSlots();",
                      _function_body(_read("main.nut"), "OpexAI::Start"))

    def test_init_always_resets_single_search_slots(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_v184InitRailSlots")
        self.assertIn("this._v184RailSlots = null;", body)
        self.assertIn("this._v184SlotCursor = 0;", body)
        self.assertNotIn("if (", body)
        self.assertNotIn("array(", body)

    def test_guard_uses_current_search(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_tryBuildRailProject")
        self.assertIn("local searchBlocked = (this._railSearch != null);", body)
        self.assertIn("searchBlocked && !c121PrepPlan", body)

    def test_multislot_helpers_removed(self):
        for name in ("_v184CanStartRailSearch", "_v184FindFreeSlot", "_v184ActiveSearchCount",
                     "_v184SelectNextSearchSlot", "_v184SyncRailSearch", "_v184FindSlotByPhase"):
            self.assertNotIn(name, _read("main.nut"))
            self.assertNotIn(name, _read("task_rail.nut"))

    def test_scheduler_has_no_round_robin(self):
        body = _function_body(_read("scheduler.nut"), "OpexAI::_advanceRailSearchSliceWithLedgers")
        self.assertNotIn("_v184", body)
        self.assertIn("this._continueRailSearch();", body)

    def test_pass_consumes_one_completed_search(self):
        body = _function_body(_read("task_projects.nut"), "OpexAI::_tryBuildProjects")
        self.assertNotIn("_v184", body)
        self.assertEqual(body.count("this._consumeResumableRailAtPassStart("), 1)
        self.assertIn('this._railSearch.phase == "build"', body)

    def test_search_state_uses_slot_zero(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_startRailSearch")
        self.assertIn("slotIndex = 0,", body)
        self.assertNotIn("_v184", body)

    def test_decision_log_preserves_single_search_format(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_continueRailSearch")
        self.assertNotIn("slotStr", body)
        self.assertIn('OpexDecide("RAIL_SEARCH", "type=resumable outcome=" + slice.stop + " iters=" + state.spent + " budget=" + state.iterationBudget);', body)


class PersistenceContract(unittest.TestCase):
    def test_search_pending_format_unchanged(self):
        save = _function_body(_read("persist.nut"), "OpexAI::Save")
        load = _function_body(_read("persist.nut"), "OpexAI::Load")
        self.assertIn("railSearchPending = this._railSearch != null,", save)
        self.assertIn('this._reloadDroppedRailSearch = ("railSearchPending" in data) && data.railSearchPending;', load)

    def test_reconcile_rebuilds_after_dropping_live_pathfinder(self):
        body = _function_body(_read("persist.nut"), "OpexAI::_reconcileAfterLoad")
        self.assertIn("if (this._reloadDroppedRailSearch)", body)
        for token in ("this._railSearch = null;", "this._projects = null;", "this._ranked = null;",
                      "this._portfolioInvalidated = true;", "task.dueCycle = this._taskCycle;"):
            self.assertIn(token, body)
        self.assertLess(body.index("this._railSearch = null;"), body.index("this._v184InitRailSlots();"))
        self.assertIn("this._reloadDroppedRailSearch = false;\n  this._v184InitRailSlots();", body)
        self.assertNotIn("V184_RAIL_SEARCH_SLOTS", body)


class ForbiddenIdentifiers(unittest.TestCase):
    def test_no_forbidden_identifiers_in_v184_methods(self):
        rail = _read("task_rail.nut")
        v184_section = rail[rail.index("/* V184 : reinitialisation"):]
        forbidden = ["p" + "arent", "c" + "lone", "b" + "ase"]
        for word in forbidden:
            self.assertNotIn(word, v184_section.lower())


if __name__ == "__main__":
    unittest.main()
