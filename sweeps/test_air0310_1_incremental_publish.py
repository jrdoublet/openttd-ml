#!/usr/bin/env python3
"""Contrat statique AIR 03/10 1 : publication partielle sans rebuild complet.

air0310_incremental_publish vaut 0 aux quatre difficultes. A 1, et seulement
si C121_CATALOG_INCREMENTAL est actif, le bloc partialPending convertit le
lot neuf et rejoue OpexReselectProjects. La phase apply garde le rebuild
complet. Aucune partie n'est lancee.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from sweeps.campaign_freeze import parse_ai_setting_specs

ROOT = Path(__file__).resolve().parents[1]

SETTING = "air0310_incremental_publish"
GLOBAL = "AIR0310_INCREMENTAL_PUBLISH"


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _setting_block(info, name):
    start = info.index(f'name = "{name}"')
    return info[start:info.index("});", start)]


def _function_body(source, signature):
    start = source.index(signature)
    nxt = source.find("\nfunction ", start + 1)
    if nxt < 0:
        nxt = len(source)
    return source[start:nxt]


def _explicit_locals(body):
    return re.findall(r"\blocal\s+([A-Za-z_][A-Za-z0-9_]*)", body)


def _brace_balance(text):
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\":
                    i += 1
                i += 1
        elif ch == "'":
            i += 1
            while i < n and text[i] != "'":
                if text[i] == "\\":
                    i += 1
                i += 1
        elif text.startswith("//", i):
            i = text.find("\n", i)
            if i < 0:
                break
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return depth
        i += 1
    return depth


class TestAir0310_1IncrementalPublish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.scheduler = _read("ai/OpexAI/scheduler_tasks.nut")
        cls.update = _read("ai/OpexAI/projects_update.nut")
        cls.selection = _read("ai/OpexAI/projects_selection.nut")
        cls.builders = _read("ai/OpexAI/projects_builders.nut")
        cls.cont = _function_body(
            cls.scheduler, "function OpexC78ContinueCatalogAirRebuild("
        )
        cls.publish = _function_body(
            cls.update, "function OpexAir0310PublishIncremental("
        )
        note_at = cls.update.index("Publication partielle AIR 03/10 1")
        cls.noted = cls.update[note_at:cls.update.index(
            "function OpexAir0310PublishIncremental("
        )] + cls.publish
        cls.reselect = _function_body(cls.selection, "function OpexReselectProjects(")
        cls.affordable = _function_body(
            cls.selection, "function OpexProjectSelectAffordable("
        )
        partial_start = cls.cont.index(
            'if (("partialPending" in s) && s.partialPending)'
        )
        apply_start = cls.cont.index('if (s.phase == "apply")', partial_start)
        scan_start = cls.cont.index(
            "local liveOps = AIController.GetOpsTillSuspend();", apply_start
        )
        cls.partial = cls.cont[partial_start:apply_start]
        cls.apply = cls.cont[apply_start:scan_start]
        cls.scan = cls.cont[scan_start:]

    def test_setting_defaults_to_one_and_is_not_persisted(self):  # adopte le 04/10 (porte A 40x3)
        self.assertEqual(self.info.count(f'name = "{SETTING}"'), 1)
        block = _setting_block(self.info, SETTING)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)
        self.assertIn("step_size = 1", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 1", block)
            self.assertNotIn(f"{key} = 0", block)
        spec = parse_ai_setting_specs(ROOT / "ai/OpexAI/info.nut")[SETTING]
        self.assertTrue(spec["boolean"])
        self.assertEqual(spec["default"], 1)
        self.assertEqual(self.globals.count(f"{GLOBAL} <- false;"), 1)
        self.assertEqual(self.globals.count(f"{GLOBAL} <-"), 1)
        self.assertEqual(
            self.settings.count(f'AIController.GetSetting("{SETTING}")'), 1
        )
        self.assertIn(
            f"{GLOBAL} = C121_CATALOG_INCREMENTAL\n"
            f'      && AIController.GetSetting("{SETTING}") != 0;',
            self.settings,
        )
        self.assertNotIn(f"{GLOBAL} <-", self.settings)
        self.assertNotIn(SETTING, self.persist)
        self.assertNotIn(GLOBAL, self.persist)

    def test_partial_publish_keeps_full_rebuild_fallback(self):
        self.assertIn(f"if ({GLOBAL} && owner._projects != null", self.partial)
        self.assertIn('("lastPublishedCount" in s) && s.lastPublishedCount > 0', self.partial)
        self.assertIn("OpexAir0310PublishIncremental(", self.partial)
        self.assertIn(
            "owner._rebuildProjects(s.fleetPlan, partialAir, false);", self.partial
        )
        self.assertLess(
            self.partial.index("OpexAir0310PublishIncremental("),
            self.partial.index("owner._rebuildProjects(s.fleetPlan, partialAir, false);"),
        )
        self.assertIn('if (publishCounts == null)', self.partial)
        self.assertIn('OpexSpanBegin("catalog.rebuild")', self.partial)
        self.assertLess(
            self.partial.index('OpexSpanBegin("catalog.rebuild")'),
            self.partial.index("OpexAir0310PublishIncremental("),
        )
        self.assertIn("owner._rebuildProjects(s.fleetPlan, airOverride);", self.apply)
        self.assertNotIn("OpexAir0310PublishIncremental", self.apply)
        self.assertNotIn("owner._rebuildProjects(", self.scan)
        self.assertNotIn("air_efficiency_reselect", self.partial)
        self.assertNotIn("air_efficiency_reselect", self.publish)

    def test_span_probe_logs_after_the_measured_rebuild(self):
        self.assertIn("if (PROBE_SPAN_TRACE)", self.partial)
        log = (
            'OpexDecide("AIR0310_PUBLISH", "mode=" + publishMode\n'
            '          + " added=" + publishAdded\n'
            '          + " reconverted=" + publishReconverted\n'
            '          + " refreshed=" + publishRefreshed\n'
            '          + " invalidated=" + publishInvalidated\n'
            '          + " total_plans=" + s.plans.len());'
        )
        self.assertIn(log, self.partial)
        self.assertLess(
            self.partial.index("OpexSpanEnd(spPartial);"),
            self.partial.index('OpexDecide("AIR0310_PUBLISH"'),
        )
        self.assertIn('publishMode = "full"', self.partial)
        self.assertIn('publishMode = "incr"', self.partial)

    def test_incremental_path_replays_selection_and_refreshes_air_state(self):
        self.assertIn("scanPlans.slice(publishedCount)", self.publish)
        self.assertIn("airOps / planCount", self.publish)
        self.assertNotIn("airOps / newPlans.len()", self.publish)
        self.assertGreaterEqual(self.publish.count("OpexProjectFromAir("), 2)
        self.assertLess(
            self.publish.index("local publishCapital = OpexAvailableCapital();"),
            self.publish.index(
                "OpexReselectProjects(projects, publishCapital, owner._abandonedPairs, "
                "owner._lines,\n      owner._railReadyStock);"
            ),
        )
        self.assertIn("OpexFilterAirAlternativesStillValid(", self.reselect)
        self.assertIn(
            "OpexProjectSelectAffordable(alternatives, capitalBudget, PROJECT_TOP_K)",
            self.reselect,
        )
        self.assertIn("PORTFOLIO_FLOOR_PCT", self.affordable)
        self.assertIn("OpexC69ComputeKDec()", self.affordable)
        self.assertIn("OpexProjectRefreshDefensiveSlot(", self.affordable)
        self.assertIn("planningOpcodes", self.noted)
        self.assertIn("economicsDate", self.noted)
        self.assertIn("catalog.paxCargo", self.noted)
        self.assertIn("c118TownIds", self.noted)
        self.assertIn("budgetScore", self.noted)
        self.assertIn("opcodeScore", self.noted)
        self.assertIn("PROJECT_AIR_TRANSACTION_OPS", self.noted)
        self.assertIn("La caisse n'est pas lue ici", self.noted)
        from_air = _function_body(self.builders, "function OpexProjectFromAir(")
        self.assertIn("planningOpcodes = planningOps", from_air)
        self.assertIn("economicsDate = AIDate.GetCurrentDate()", from_air)
        self.assertIn("cargo = catalog.paxCargo", from_air)
        self.assertIn("expectedOpcodes = expectedOps", from_air)
        self.assertNotIn("OpexAvailableCapital()", from_air)

    def test_insertion_order_preserves_rebuild_tie_break(self):
        helper = _function_body(self.update, "function OpexAir0310InsertAirBlock(")
        late_mode = _function_body(self.update, "function OpexAir0310ModeIsLate(")
        self.assertIn("OpexAir0310ModeIsLate(project)", helper)
        self.assertIn('project.mode == "water"', late_mode)
        self.assertIn('project.mode == "fleet"', late_mode)
        self.assertIn("prior.revenueAnnual >= project.revenueAnnual", self.update)
        late = _function_body(self.update, "function OpexAir0310KeyIsLate(")
        self.assertIn('"subsidy|"', late)
        self.assertIn('"fleet|"', late)
        kept = self.publish.index("if (slotKey in keptAir)")
        moved = self.publish.index("if (slotKey in movedAir)")
        pending = self.publish.index("if (slotKey in pendingNew)")
        self.assertLess(kept, moved)
        self.assertLess(moved, pending)
        self.assertIn("OpexStagedAirPlanStillValid(", self.publish)
        self.assertEqual(_brace_balance(self.update), 0)
        self.assertEqual(_brace_balance(self.scheduler), 0)
        names = _explicit_locals(self.publish)
        self.assertEqual(len(names), len(set(names)), names)
        cont_names = _explicit_locals(self.cont)
        self.assertEqual(len(cont_names), len(set(cont_names)), cont_names)


if __name__ == "__main__":
    unittest.main()
