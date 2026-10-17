#!/usr/bin/env python3
"""Contrat statique V141 : publication AIR sans reconvertir les projets publies.

v141_catalog_incremental et v141_catalog_incremental_check valent 0 aux quatre
difficultes. A 1, et seulement si C121_CATALOG_INCREMENTAL est actif et C111
eteint, OpexAir0310PublishIncremental rafraichit planningOpcodes / date / cargo
sur les projets air deja publies au lieu d'appeler OpexProjectFromAir.
Les plans neufs restent convertis par FromAir. La reelection est inchangee.
Le mode controle, sous probe_events (C56_TASK_TRACE), recalcule aussi FromAir
et journalise V141_CHECK. Aucune partie n'est lancee.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from sweeps.campaign_freeze import parse_ai_setting_specs

ROOT = Path(__file__).resolve().parents[1]

SETTING = "v141_catalog_incremental"
CHECK_SETTING = "v141_catalog_incremental_check"
GLOBAL = "V141_CATALOG_INCREMENTAL"
CHECK_GLOBAL = "V141_CATALOG_INCREMENTAL_CHECK"


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


RESERVED = ("clone", "base", "parent")


class TestV141CatalogIncremental(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.update = _read("ai/OpexAI/projects_update.nut")
        cls.builders = _read("ai/OpexAI/projects_builders.nut")
        cls.publish = _function_body(
            cls.update, "function OpexAir0310PublishIncremental("
        )
        cls.refresh = _function_body(
            cls.update, "function OpexV141RefreshPublishedAir("
        )
        cls.valid = _function_body(
            cls.update, "function OpexV141PublishedAirStillValid("
        )
        cls.diff = _function_body(
            cls.update, "function OpexV141DecisionFieldDiff("
        )
        cls.log = _function_body(
            cls.update, "function OpexV141LogCheck("
        )
        cls.from_air = _function_body(
            cls.builders, "function OpexProjectFromAir("
        )

    def test_settings_defaults_and_are_not_persisted(self):
        for name, global_name, default in (
            (CHECK_SETTING, CHECK_GLOBAL, 0),
        ):
            self.assertEqual(self.info.count(f'name = "{name}"'), 1)
            block = _setting_block(self.info, name)
            self.assertIn("flags = AICONFIG_BOOLEAN", block)
            self.assertIn("min_value = 0", block)
            self.assertIn("max_value = 1", block)
            self.assertIn("step_size = 1", block)
            for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
                self.assertIn(f"{key} = {default}", block)
                if default == 0:
                    self.assertNotIn(f"{key} = 1", block)
            spec = parse_ai_setting_specs(ROOT / "ai/OpexAI/info.nut")[name]
            self.assertTrue(spec["boolean"])
            self.assertEqual(spec["default"], default)
            self.assertEqual(self.globals.count(f"{global_name} <- false;"), 1)
            self.assertEqual(self.globals.count(f"{global_name} <-"), 1)
            # V167 : la verification passe par OpexProbeSetting (groupe 256 du reglage probes)
            reader = "OpexProbeSetting" if name == CHECK_SETTING else "AIController.GetSetting"
            self.assertEqual(
                self.settings.count(f'Setting("{name}")'), 1
            )
            self.assertIn(
                f'{global_name} = {reader}("{name}") != 0;',
                self.settings,
            )
            self.assertNotIn(f"{global_name} <-", self.settings)
            self.assertNotIn(name, self.persist)
            self.assertNotIn(global_name, self.persist)
        from v237_contracts import assert_retired
        assert_retired(self, (SETTING,))

    def test_zero_keeps_fromair_reconvert_on_published_air(self):
        self.assertNotIn("v141Use", self.publish)
        self.assertNotIn("local refreshed = OpexProjectFromAir", self.publish)
        self.assertIn("OpexV141RefreshPublishedAir(project, catalog, airOpsPerPlan)", self.publish)
        self.assertIn("v141Oracle = OpexProjectFromAir", self.publish)

    def test_on_refreshes_published_air_in_place_and_converts_new_plans(self):
        self.assertIn(
            'local v141Check = V141_CATALOG_INCREMENTAL_CHECK && C56_TASK_TRACE;',
            self.publish,
        )
        self.assertIn("OpexV141PublishedAirStillValid(payload)", self.publish)
        self.assertIn("refreshedCount++", self.publish)
        self.assertIn("OpexProjectFromAir(catalog, plan, airOpsPerPlan)", self.publish)
        self.assertIn("planningOpcodes = planningOps", self.refresh)
        self.assertIn("economicsDate = AIDate.GetCurrentDate()", self.refresh)
        self.assertIn("cargo = catalog.paxCargo", self.refresh)
        self.assertNotIn("OpexProjectFromAir(", self.refresh)
        self.assertNotIn("OpexAvailableCapital()", self.refresh)
        self.assertIn("profitAnnual <= 0", self.valid)
        self.assertIn("decisionEconomics", self.valid)
        self.assertIn("budgetScore", self.from_air)
        self.assertIn("planningOpcodes = planningOps", self.from_air)
        self.assertIn("expectedOpcodes = expectedOps", self.from_air)

    def test_check_mode_requires_probe_events_and_logs_v141_check(self):
        self.assertIn(
            "v141Check = V141_CATALOG_INCREMENTAL_CHECK && C56_TASK_TRACE",
            self.publish,
        )
        self.assertIn("if (v141Check)", self.publish)
        self.assertIn("OpexV141LogCheck(", self.publish)
        self.assertIn('OpexDecide("V141_CHECK"', self.log)
        self.assertIn("if (!C56_TASK_TRACE) return", self.log)
        self.assertIn("verdict=", self.log)
        self.assertIn("field=", self.log)
        self.assertIn("budgetScore", self.diff)
        self.assertIn("opcodeScore", self.diff)
        self.assertIn("planningOpcodes", self.diff)
        self.assertIn("identical", self.publish)
        self.assertIn("diff", self.publish)

    def test_squirrel_traps(self):
        for body in (self.publish, self.refresh, self.valid, self.diff, self.log):
            names = _explicit_locals(body)
            self.assertEqual(len(names), len(set(names)), names)
            for reserved in RESERVED:
                self.assertNotIn(reserved, names)
            self.assertNotRegex(body, r"\b[A-Z][A-Z0-9_]*\+\+")
            self.assertNotRegex(body, r"\b[A-Z][A-Z0-9_]*\s*<-\s*[A-Z][A-Z0-9_]*\s*\+")
        self.assertEqual(_brace_balance(self.update), 0)
        self.assertNotIn("line.stationA", self.update)
        self.assertNotIn("line.stationB", self.update)

    def test_campaign_freeze_sees_defaults(self):
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('v141_catalog_incremental',))


if __name__ == "__main__":
    unittest.main()
