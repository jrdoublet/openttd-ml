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
        cls.from_air = _function_body(
            cls.builders, "function OpexProjectFromAir("
        )

    def test_campaign_freeze_sees_defaults(self):
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('v141_catalog_incremental',))


if __name__ == "__main__":
    unittest.main()
