#!/usr/bin/env python3
"""Contrat V123 : recontrole des sites air avant chantier, hors cache V122.

air0310_site_recheck_before_build vaut 0 aux quatre difficultes. A 1, et
seulement si le cache V122 est actif, OpexBuildAirRoute reevalue
OpexAirSiteStillBuildable pour siteA et siteB a frais, avec un
stationLimitedTowns amorce comme le filtre, juste avant toute depense.
Un site invalide met a jour le cache a false, ne depense rien et ne
bannit pas la paire. Sans V122, V123 n'a pas d'effet. A 0, le corps
historique du chantier est le seul execute. Aucune partie n'est lancee.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from sweeps.campaign_freeze import parse_ai_setting_specs

ROOT = Path(__file__).resolve().parents[1]

SETTING = "air0310_site_recheck_before_build"
GLOBAL = "AIR0310_SITE_RECHECK_BEFORE_BUILD"
CACHE = "AIR0310_SITE_VALIDITY_CACHE"
KEY = '(reuseA ? "R|" : "N|") + plan.airport.type + "|" + plan.plane.planeType + "|" + plan.siteA.anchor'
RECHECK_KEY = '(reuseA ? "R|" : "N|") + airport.type + "|" + plane.planeType + "|" + plan.siteA.anchor'


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _setting_block(info, name):
    start = info.index(f'name = "{name}"')
    return info[start:info.index("});", start)]


def _brace_body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start:idx + 1]
    raise AssertionError(f"unterminated function: {signature}")


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


def site_key(reuse, airport_type, plane_type, anchor):
    return ("R|" if reuse else "N|") + f"{airport_type}|{plane_type}|{anchor}"


def cache_begin(state, month, local_limited):
    if state is None or state["month"] != month:
        state = {"month": month, "entries": {}, "limited": {}}
    for town_id in state["limited"]:
        local_limited[town_id] = True
    return state


def recheck_one(state, key, reuse, town_id, local_limited, probe):
    """Miroir de OpexAir0310RecheckOneSite : toujours sonder, puis ecrire."""
    ok = probe(local_limited)
    state["entries"][key] = ok
    if not reuse and not ok and town_id in local_limited:
        state["limited"][town_id] = True
    return ok


def cache_ok(state, key, reuse, town_id, local_limited, probe):
    """Miroir de OpexAir0310SiteValidityOk."""
    if key in state["entries"]:
        return state["entries"][key], False
    ok = probe(local_limited)
    state["entries"][key] = ok
    if not reuse and not ok and town_id in local_limited:
        state["limited"][town_id] = True
    return ok, True


class TestAir0310SiteRecheckBeforeBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.coverage = _read("ai/OpexAI/air_coverage.nut")
        cls.construction = _read("ai/OpexAI/air_construction.nut")
        cls.generation = _read("ai/OpexAI/projects_generation.nut")
        cls.task_air = _read("ai/OpexAI/task_air.nut")
        cls.lines = _read("ai/OpexAI/lines.nut")
        cls.build = _brace_body(cls.construction, "function OpexBuildAirRoute(")
        cls.recheck = _brace_body(
            cls.coverage, "function OpexAir0310RecheckSitesBeforeBuild(")
        cls.one = _brace_body(
            cls.coverage, "function OpexAir0310RecheckOneSite(")
        cls.note = _brace_body(
            cls.coverage, "function OpexAir0310NoteSiteRecheck(")
        cls.ok = _brace_body(
            cls.coverage, "function OpexAir0310SiteValidityOk(")
        cls.begin = _brace_body(
            cls.coverage, "function OpexAir0310SiteValidityBegin(")
        cls.try_project = _brace_body(
            cls.task_air,
            "function OpexAI::_tryBuildAirProject(year, project, rank, builtCount, passDiscards, anchor, yy)",
        )
        cls.try_direct = _brace_body(
            cls.task_air, "function OpexAI::_tryBuildAir(year)")
        cls.abandon = _brace_body(
            cls.lines, "function OpexBuildFailureIsAbandonable(")

    def test_setting_defaults_to_zero_and_is_not_persisted(self):
        self.assertEqual(self.info.count(f'name = "{SETTING}"'), 1)
        block = _setting_block(self.info, SETTING)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)
        self.assertIn("step_size = 1", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 0", block)
            self.assertNotIn(f"{key} = 1", block)
        spec = parse_ai_setting_specs(ROOT / "ai/OpexAI/info.nut")[SETTING]
        self.assertTrue(spec["boolean"])
        self.assertEqual(spec["default"], 0)
        self.assertEqual(self.globals.count(f"{GLOBAL} <- false;"), 1)
        self.assertEqual(self.globals.count(f"{GLOBAL} <-"), 1)
        self.assertEqual(
            self.settings.count(f'AIController.GetSetting("{SETTING}")'), 1)
        load = (
            f"{GLOBAL} = C121_CATALOG_INCREMENTAL\n"
            f'      && AIController.GetSetting("{SETTING}") != 0;'
        )
        self.assertIn(load, self.settings)
        self.assertIn("AIR0310_SITE_RECHECK_STATS = null;", self.settings)
        cache_load = (
            f"{CACHE} = C121_CATALOG_INCREMENTAL\n"
            '      && AIController.GetSetting("air0310_site_validity_cache") != 0;'
        )
        self.assertLess(self.settings.index(cache_load), self.settings.index(load))
        self.assertNotIn(SETTING, self.persist)
        self.assertNotIn(GLOBAL, self.persist)
        self.assertNotIn("AIR0310_SITE_RECHECK_STATS", self.persist)
        self.assertNotIn("AIR0310_SITE_VALIDITY_STATE", self.persist)

    def test_without_v122_the_flag_is_inert(self):
        self.assertIn(
            f"if (!{CACHE} || !{GLOBAL}) return true;", self.recheck)
        gate = (
            f"if ({CACHE} && {GLOBAL}) {{\n"
            "    if (!OpexAir0310RecheckSitesBeforeBuild(plan, airport, planeChoice, reuseA, reuseB)) {\n"
            '      result.reason = "RECHECK";\n'
            "      return result;"
        )
        self.assertIn(gate, self.build)
        self.assertLess(
            self.build.index("local reuseB = (\"reuseB\" in plan) && plan.reuseB;"),
            self.build.index(f"if ({CACHE} && {GLOBAL})"))
        self.assertLess(
            self.build.index('result.reason = "RECHECK";'),
            self.build.index("local costs = AIAccounting();"))
        self.assertLess(
            self.build.index('result.reason = "RECHECK";'),
            self.build.index("budget.begin();"))
        self.assertLess(
            self.build.index('result.reason = "RECHECK";'),
            self.build.index("local levelA = OpexAirLevelFootprint("))
        after = self.build.split(gate, 1)[1]
        self.assertIn("local preA = AIR_EFFICIENCY_PREFLIGHT", after)
        self.assertNotIn("OpexAir0310RecheckSitesBeforeBuild", after)
        self.assertNotIn(GLOBAL, self.generation)

    def test_recheck_probes_at_cost_and_writes_false(self):
        self.assertEqual(_brace_balance(self.coverage), 0)
        self.assertEqual(_brace_balance(self.construction), 0)
        for body in (self.recheck, self.one, self.note, self.ok, self.begin):
            names = _explicit_locals(body)
            self.assertEqual(len(names), len(set(names)), names)
        self.assertNotIn("OpexAir0310SiteValidityOk(", self.recheck)
        self.assertNotIn("OpexAir0310SiteValidityOk(", self.one)
        self.assertIn("OpexAirSiteStillBuildable(", self.one)
        self.assertLess(
            self.one.index("OpexAirSiteStillBuildable("),
            self.one.index("state.entries.rawset(key, ok);"))
        self.assertNotIn("if (key in state.entries)", self.one)
        self.assertIn("OpexAir0310SiteValidityBegin(stationLimitedTowns)", self.recheck)
        self.assertEqual(self.recheck.count("OpexAir0310RecheckOneSite("), 2)
        self.assertIn(RECHECK_KEY, self.recheck)
        key_b = RECHECK_KEY.replace("reuseA", "reuseB").replace("siteA", "siteB")
        self.assertIn(key_b, self.recheck)
        self.assertIn(KEY, self.generation)
        self.assertNotIn("OpexAir0310InvalidateSiteValidity", self.recheck)
        self.assertNotIn("OpexAir0310InvalidateSiteValidity", self.one)
        self.assertIn("rechecks = 0, rechecks_failed = 0", self.note)
        self.assertIn("stats.rechecks++", self.note)
        self.assertIn("stats.rechecks_failed++", self.note)
        self.assertIn("PROBE_SPAN_TRACE || DECISION_LOG", self.note)
        self.assertIn('OpexDecide("AIR0310_SITE_RECHECK"', self.note)
        self.assertIn("rechecks=", self.note)
        self.assertIn("rechecks_failed=", self.note)
        self.assertIn("OpexAir0310NoteSiteRecheck(failed)", self.recheck)

        probes = {"n": 0}

        def probe_now_false(local_limited):
            probes["n"] += 1
            return False

        state = {"month": 1970 * 12, "entries": {}, "limited": {}}
        key = site_key(False, 1, 2, 10)
        state["entries"][key] = True
        local = {}
        state = cache_begin(state, 1970 * 12, local)
        ok = recheck_one(state, key, False, 7, local, probe_now_false)
        self.assertFalse(ok)
        self.assertEqual(probes["n"], 1)
        self.assertFalse(state["entries"][key])

        local_next = {}
        state = cache_begin(state, 1970 * 12, local_next)
        ok_filter, probed = cache_ok(
            state, key, False, 7, local_next, lambda towns: True)
        self.assertFalse(ok_filter)
        self.assertFalse(probed)
        self.assertEqual(probes["n"], 1)

        key_b = site_key(False, 1, 2, 11)
        state["entries"][key_b] = True
        ok_b = recheck_one(state, key_b, False, 8, local_next, probe_now_false)
        self.assertFalse(ok_b)
        self.assertEqual(probes["n"], 2)
        ok_again, probed = cache_ok(
            state, key_b, False, 8, local_next, lambda towns: True)
        self.assertFalse(ok_again)
        self.assertFalse(probed)

    def test_failed_recheck_does_not_spend_or_abandon(self):
        self.assertLess(
            self.build.index('result.reason = "RECHECK";'),
            self.build.index("local costs = AIAccounting();"))
        self.assertNotIn("budget.begin();", self.build.split(
            'result.reason = "RECHECK";', 1)[0].split(
            f"if ({CACHE} && {GLOBAL})", 1)[1])
        self.assertNotIn("OpexAirLevelFootprint(", self.build.split(
            'result.reason = "RECHECK";', 1)[0].split(
            f"if ({CACHE} && {GLOBAL})", 1)[1])
        self.assertIn('result.reason == "RECHECK"', self.abandon)
        self.assertLess(
            self.abandon.index('result.reason == "RECOVERY"'),
            self.abandon.index('result.reason == "RECHECK"'))
        self.assertLess(
            self.abandon.index('result.reason == "RECHECK"'),
            self.abandon.index("ABANDON_MEMORY_TRANSIENT_GUARD"))

        project_fail = self.try_project.split('if (!result.ok)', 1)[1]
        recheck_branch = project_fail.split("local errorAnchor", 1)[0]
        self.assertIn('result.reason == "RECHECK"', recheck_branch)
        self.assertIn('reason = "site_recheck"', recheck_branch)
        self.assertIn('outcome = "rejected"', recheck_branch)
        self.assertNotIn("OpexBuildFailureIsAbandonable", recheck_branch)
        self.assertNotIn("_markPairAbandoned", recheck_branch)
        self.assertNotIn("_padAirFailedSites", recheck_branch)
        self.assertLess(
            self.try_project.index('result.reason == "RECHECK"'),
            self.try_project.index("OpexBuildFailureIsAbandonable(result)"))

        direct_fail = self.try_direct.split("if (!result.ok)", 1)[1]
        direct_recheck = direct_fail.split("if (DECISION_LOG)", 2)[0]
        self.assertIn('result.reason == "RECHECK"', direct_recheck)
        self.assertIn("reason=site_recheck", self.try_direct)
        self.assertNotIn("OpexBuildFailureIsAbandonable", direct_recheck)
        self.assertNotIn("_markPairAbandoned", direct_recheck)
        self.assertLess(
            self.try_direct.index('result.reason == "RECHECK"'),
            self.try_direct.index("OpexBuildFailureIsAbandonable(result)"))
        after_recheck = self.try_direct.split('reason=site_recheck', 1)[1]
        self.assertLess(
            after_recheck.index("break;"),
            after_recheck.index("OpexBuildFailureIsAbandonable(result)"))


if __name__ == "__main__":
    unittest.main()
