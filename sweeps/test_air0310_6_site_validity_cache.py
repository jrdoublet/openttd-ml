#!/usr/bin/env python3
"""Contrat V122 : cache de validite des sites air entre reelections.

air0310_site_validity_cache vaut 0 aux quatre difficultes. A 1, et seulement
si C121_CATALOG_INCREMENTAL est actif, OpexFilterAirAlternativesStillValid
reutilise OpexAirSiteStillBuildable pour la cle keyA/keyB jusqu'au changement
de mois ou jusqu'a un chantier ou une demolition d'OpexAI. A 0, le corps
historique du filtre est le seul execute. C120_AIR_FILTER_SNAPSHOT et ses
compteurs ne changent pas. Aucune partie n'est lancee.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from sweeps.campaign_freeze import parse_ai_setting_specs

ROOT = Path(__file__).resolve().parents[1]

SETTING = "air0310_site_validity_cache"
GLOBAL = "AIR0310_SITE_VALIDITY_CACHE"
INVALIDATE = "OpexAir0310InvalidateSiteValidity"
KEY = '(reuseA ? "R|" : "N|") + plan.airport.type + "|" + plan.plane.planeType + "|" + plan.siteA.anchor'
SNAPSHOT = """  if (C120_AIR_TERRITORIAL_RANKING) {
    C120_AIR_FILTER_SNAPSHOT = {
      date = AIDate.GetCurrentDate(), inputAir = c120InputAir,
      filteredAir = c120FilteredAir, liveAir = c120InputAir - c120FilteredAir,
    };
  }"""


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


def _gated_calls(body):
    return body.count(f"if ({GLOBAL}) {INVALIDATE}();")


def site_key(reuse, airport_type, plane_type, anchor):
    """Meme chaine que keyA/keyB."""
    return ("R|" if reuse else "N|") + f"{airport_type}|{plane_type}|{anchor}"


def cache_begin(state, month, local_limited):
    """Miroir de OpexAir0310SiteValidityBegin. None = cache vide."""
    if state is None or state["month"] != month:
        state = {"month": month, "entries": {}, "limited": {}}
    for town_id in state["limited"]:
        local_limited[town_id] = True
    return state


def cache_ok(state, key, reuse, town_id, local_limited, probe):
    """Miroir de OpexAir0310SiteValidityOk. probe(local) -> bool, et peut
    marquer la ville. Retourne (ok, probed)."""
    if key in state["entries"]:
        return state["entries"][key], False
    ok = probe(local_limited)
    state["entries"][key] = ok
    if not reuse and not ok and town_id in local_limited:
        state["limited"][town_id] = True
    return ok, True


class TestAir0310SiteValidityCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.generation = _read("ai/OpexAI/projects_generation.nut")
        cls.coverage = _read("ai/OpexAI/air_coverage.nut")
        cls.construction = _read("ai/OpexAI/air_construction.nut")
        cls.recovery = _read("ai/OpexAI/air_recovery.nut")
        cls.sites = _read("ai/OpexAI/air_sites.nut")
        cls.rail = _read("ai/OpexAI/builder_rail.nut")
        cls.road = _read("ai/OpexAI/builder_road.nut")
        cls.water = _read("ai/OpexAI/builder_water.nut")
        cls.planning = _read("ai/OpexAI/air_planning.nut")
        cls.catalog = _read("ai/OpexAI/air_catalog_c121.nut")
        cls.lines = _read("ai/OpexAI/lines.nut")
        cls.task_air = _read("ai/OpexAI/task_air.nut")
        cls.hist = _brace_body(
            cls.generation, "function OpexFilterAirAlternativesStillValid(")
        cls.cached = _brace_body(
            cls.generation, "function OpexAir0310FilterAirAlternativesStillValid(")
        cls.month = _brace_body(cls.coverage, "function OpexAir0310SiteValidityMonth(")
        cls.invalidate = _brace_body(
            cls.coverage, "function OpexAir0310InvalidateSiteValidity(")
        cls.begin = _brace_body(cls.coverage, "function OpexAir0310SiteValidityBegin(")
        cls.ok = _brace_body(cls.coverage, "function OpexAir0310SiteValidityOk(")
        cls.endpoint = _brace_body(
            cls.coverage, "function OpexC121InvalidateEndpointGeometry(")
        cls.town_cache = _brace_body(
            cls.coverage, "function OpexAirResetStationCoverageTownCache(")
        cls.reset = _brace_body(cls.coverage, "function OpexAirResetSiteCache(")
        cls.level = _brace_body(cls.sites, "function OpexAirLevelFootprint(")
        cls.build = _brace_body(
            cls.construction, "function OpexBuildAirRoute(")
        cls.still = _brace_body(cls.sites, "function OpexAirSiteStillBuildable(")

    def test_setting_defaults_to_one_and_is_not_persisted(self):  # adopte le 05/10 (optimisation d'opcodes)
        self.assertEqual(self.info.count(f'name = "{SETTING}"'), 1)
        block = _setting_block(self.info, SETTING)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)
        self.assertIn("step_size = 1", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 1", block)
            self.assertNotIn(f"{key} = 0", block)
        self.assertIn("1 = on (default), 0 = probe every unique site on every filter", block)
        spec = parse_ai_setting_specs(ROOT / "ai/OpexAI/info.nut")[SETTING]
        self.assertTrue(spec["boolean"])
        self.assertEqual(spec["default"], 1)
        self.assertEqual(self.globals.count(f"{GLOBAL} <- false;"), 1)
        self.assertEqual(self.globals.count(f"{GLOBAL} <-"), 1)
        self.assertEqual(
            self.settings.count(f'AIController.GetSetting("{SETTING}")'), 1)
        load = (
            f"{GLOBAL} = C121_CATALOG_INCREMENTAL\n"
            f'      && AIController.GetSetting("{SETTING}") != 0;'
        )
        self.assertIn(load, self.settings)
        self.assertIn("AIR0310_SITE_VALIDITY_STATE = null;", self.settings)
        publish = (
            "AIR0310_INCREMENTAL_PUBLISH = C121_CATALOG_INCREMENTAL\n"
            '      && AIController.GetSetting("air0310_incremental_publish") != 0;'
        )
        self.assertLess(self.settings.index(publish), self.settings.index(load))
        self.assertNotIn(SETTING, self.persist)
        self.assertNotIn(GLOBAL, self.persist)
        self.assertNotIn("AIR0310_SITE_VALIDITY_STATE", self.persist)

    def test_flag_zero_keeps_the_historical_filter_body(self):
        self.assertEqual(_brace_balance(self.generation), 0)
        self.assertEqual(_brace_balance(self.coverage), 0)
        for body in (self.hist, self.cached, self.month, self.invalidate,
                     self.begin, self.ok):
            names = _explicit_locals(body)
            self.assertEqual(len(names), len(set(names)), names)
        gate = (
            "if (AIR0310_SITE_VALIDITY_CACHE)\n"
            "    return OpexAir0310FilterAirAlternativesStillValid("
            "alternatives, abandonedPairs, lines);"
        )
        self.assertIn(gate, self.hist)
        after = self.hist.split(gate, 1)[1].lstrip()
        self.assertTrue(after.startswith("local live = [];"))
        self.assertNotIn("AIR0310", after)
        self.assertNotIn("OpexAir0310", after)
        self.assertIn("local siteValidity = {};", after)
        self.assertIn("local stationLimitedTowns = {};", after)
        self.assertEqual(self.generation.count("local siteValidity = {};"), 1)
        self.assertIn(KEY, self.hist)
        self.assertIn(KEY, self.cached)
        key_b = KEY.replace("reuseA", "reuseB").replace("siteA", "siteB")
        self.assertIn(key_b, self.hist)
        self.assertIn(key_b, self.cached)
        self.assertEqual(self.hist.count(SNAPSHOT), 1)
        self.assertEqual(self.cached.count(SNAPSHOT), 1)
        self.assertNotIn("local siteValidity", self.cached)
        self.assertIn("OpexAir0310SiteValidityBegin(stationLimitedTowns)", self.cached)
        self.assertEqual(self.cached.count("OpexAir0310SiteValidityOk("), 2)
        self.assertIn("c120InputAir++", self.hist)
        self.assertIn("c120FilteredAir++", self.hist)
        self.assertIn("c120InputAir++", self.cached)
        self.assertIn("c120FilteredAir++", self.cached)
        self.assertNotIn(GLOBAL, self.planning)
        self.assertIn("local siteValidity = {}", self.planning)

    def test_cache_keeps_town_limit_on_misses_only(self):
        self.assertIn("AIDate.GetYear(date) * 12 + AIDate.GetMonth(date)", self.month)
        self.assertIn("AIR0310_SITE_VALIDITY_STATE = null;", self.invalidate)
        self.assertIn("state.month != month", self.begin)
        self.assertIn("state.limited", self.begin)
        self.assertIn("stationLimitedTowns.rawset(townId, true)", self.begin)
        self.assertLess(self.ok.index("if (key in state.entries) return state.entries[key];"),
                        self.ok.index("OpexAirSiteStillBuildable("))
        self.assertIn("state.limited.rawset(site.town.id, true)", self.ok)
        self.assertIn("!reuse && !ok", self.ok)

        builds = {"n": 0}

        def probe_true_then_limit(local_limited, town=7):
            """Miroir de StillBuildable : ville deja dans la table -> false
            avant BuildAirport. Le cache appelle quand meme la fonction sur
            un miss ; seule la sonde couteuse est sautee."""
            if town in local_limited:
                return False
            builds["n"] += 1
            if builds["n"] >= 2:
                local_limited[town] = True
                return False
            return True

        state = None
        local = {}
        state = cache_begin(state, 1970 * 12, local)
        ok_a, probed = cache_ok(
            state, site_key(False, 1, 2, 10), False, 7, local,
            lambda towns: probe_true_then_limit(towns))
        self.assertTrue(ok_a)
        self.assertTrue(probed)
        ok_b, probed = cache_ok(
            state, site_key(False, 1, 2, 11), False, 7, local,
            lambda towns: probe_true_then_limit(towns))
        self.assertFalse(ok_b)
        self.assertTrue(probed)
        self.assertEqual(builds["n"], 2)
        self.assertIn(7, state["limited"])
        ok_a2, probed = cache_ok(
            state, site_key(False, 1, 2, 10), False, 7, local, lambda towns: True)
        self.assertTrue(ok_a2)
        self.assertFalse(probed)
        before = builds["n"]
        ok_c, probed = cache_ok(
            state, site_key(False, 1, 2, 12), False, 7, local,
            lambda towns: probe_true_then_limit(towns))
        self.assertFalse(ok_c)
        self.assertTrue(probed)
        self.assertEqual(builds["n"], before)
        self.assertFalse(state["entries"][site_key(False, 1, 2, 12)])

        local_next = {}
        state = cache_begin(state, 1970 * 12, local_next)
        self.assertIn(7, local_next)
        before = builds["n"]
        ok_d, probed = cache_ok(
            state, site_key(False, 1, 2, 13), False, 7, local_next,
            lambda towns: probe_true_then_limit(towns))
        self.assertFalse(ok_d)
        self.assertTrue(probed)
        self.assertEqual(builds["n"], before)
        self.assertFalse(state["entries"][site_key(False, 1, 2, 13)])
        ok_a3, probed = cache_ok(
            state, site_key(False, 1, 2, 10), False, 7, local_next, lambda towns: False)
        self.assertTrue(ok_a3)
        self.assertFalse(probed)

        false_key = site_key(False, 1, 2, 11)
        self.assertFalse(state["entries"][false_key])
        _, probed = cache_ok(
            state, false_key, False, 7, local_next, lambda towns: True)
        self.assertFalse(probed)
        self.assertFalse(state["entries"][false_key])

        local_month = {}
        state = cache_begin(state, 1970 * 12 + 1, local_month)
        self.assertEqual(state["entries"], {})
        self.assertEqual(state["limited"], {})
        self.assertEqual(local_month, {})
        ok_fresh, probed = cache_ok(
            state, site_key(False, 1, 2, 10), False, 7, local_month, lambda towns: False)
        self.assertFalse(ok_fresh)
        self.assertTrue(probed)

        state = None
        local_drop = {}
        state = cache_begin(state, 1970 * 12 + 1, local_drop)
        self.assertEqual(state["entries"], {})
        _, probed = cache_ok(
            state, site_key(True, 3, 4, 99), True, 8, local_drop, lambda towns: True)
        self.assertTrue(probed)
        self.assertNotIn(8, state["limited"])

    def test_invalidation_follows_real_construction_only(self):
        self.assertEqual(_gated_calls(self.endpoint), 0)
        self.assertNotIn(INVALIDATE, self.endpoint)
        self.assertNotIn(INVALIDATE, self.town_cache)
        self.assertNotIn(INVALIDATE, self.sites)
        self.assertNotIn(INVALIDATE, self.catalog)
        self.assertNotIn("AITestMode", self.level)
        self.assertIn("AITile.LevelTiles(anchor, end)", self.level)
        for signature, source in (
            ("function OpexAirProbeSite(", self.construction),
            ("function OpexStationPlans(", self.rail),
            ("function OpexJoinPlatformPlans(", self.rail),
            ("function OpexSimulateRailInfraCost(", self.rail),
            ("function OpexAI::_revalidateRailStockPlan(", _read("ai/OpexAI/task_rail.nut")),
        ):
            self.assertNotIn(INVALIDATE, _brace_body(source, signature))

        self.assertEqual(_gated_calls(self.reset), 1)
        self.assertLess(
            self.reset.index("AIR_STATION_COVERAGE_MISSES = 0;"),
            self.reset.index(f"if ({GLOBAL}) {INVALIDATE}();"))
        self.assertEqual(_gated_calls(self.build), 2)
        self.assertLess(
            self.build.index(f"if ({GLOBAL}) {INVALIDATE}();"),
            self.build.index("local levelA = OpexAirLevelFootprint("))
        level_b = self.build.index("local levelB = OpexAirLevelFootprint(")
        self.assertLess(self.build.rindex(f"if ({GLOBAL}) {INVALIDATE}();"), level_b)
        joined = _brace_body(self.construction, "function OpexAirBuildJoinedStops(")
        self.assertEqual(_gated_calls(joined), 1)
        self.assertLess(joined.index("local test = AITestMode();"), joined.index(INVALIDATE))
        rollback = _brace_body(self.construction, "function OpexAirRollback(")
        self.assertLess(rollback.index("OPEX_AIR_ROLLBACKS.append(ticket)"),
                        rollback.index(INVALIDATE))
        self.assertLess(rollback.index(INVALIDATE),
                        rollback.index("OpexAirContinueRollback(ticket)"))
        cleanup = _brace_body(self.recovery, "function OpexAirContinueRollback(")
        self.assertIn("if (!used && AIAirport.RemoveAirport(tile)) continue;", cleanup)
        self.assertLess(cleanup.index("AIAirport.RemoveAirport(tile)"),
                        cleanup.index(INVALIDATE))
        self.assertIn("airports.len() != airportCount", cleanup)

        execute = _brace_body(self.rail, "function OpexExecuteRailPlan(")
        upgrade = _brace_body(self.rail, "function OpexExecuteUpgradeAfterSearch(")
        dual = _brace_body(self.rail, "function OpexTryDoubleTrack(")
        tear = _brace_body(self.rail, "function OpexRollback(")
        self.assertEqual(_gated_calls(execute), 1)
        self.assertLess(execute.index("budget.begin();"), execute.index(INVALIDATE))
        self.assertLess(execute.index(INVALIDATE), execute.index("AITile.DemolishTile(planA.anchor"))
        self.assertEqual(_gated_calls(upgrade), 1)
        self.assertLess(upgrade.index(INVALIDATE),
                        upgrade.index("AITile.DemolishTile(planA2.anchor"))
        self.assertEqual(_gated_calls(dual), 1)
        self.assertLess(dual.index("if (!AIStation.IsValidStation(stationIdA)"),
                        dual.index(INVALIDATE))
        self.assertLess(tear.index("AITile.DemolishTile(planB.anchor"),
                        tear.index(INVALIDATE))
        self.assertLess(tear.index(INVALIDATE), tear.index("if (tiles == null) return;"))

        road_build = _brace_body(self.road, "function OpexBuildRoadRoute(")
        road_back = _brace_body(self.road, "function OpexRoadRollback(")
        self.assertLess(road_build.index('result.reason = "SPACING"'),
                        road_build.index(INVALIDATE))
        self.assertLess(road_build.index("budget.begin();"), road_build.index(INVALIDATE))
        self.assertLess(road_back.index("if (!allSold) return;"), road_back.index(INVALIDATE))
        water_build = _brace_body(self.water, "function OpexBuildWaterRoute(")
        water_back = _brace_body(self.water, "function OpexWaterRollback(")
        self.assertLess(water_build.index("WATER_OPCODE_COMPAT_FALSE"),
                        water_build.index(INVALIDATE))
        self.assertLess(water_build.index(INVALIDATE),
                        water_build.index("AIMarine.BuildDock(plan.siteA.dock"))
        self.assertLess(water_back.index("AIMarine.RemoveDock(dockA)"),
                        water_back.index(INVALIDATE))

        for rel, count in (
            ("ai/OpexAI/task_air.nut", 2),
            ("ai/OpexAI/task_road.nut", 1),
            ("ai/OpexAI/task_town.nut", 1),
            ("ai/OpexAI/task_water.nut", 1),
            ("ai/OpexAI/task_rail.nut", 1),
        ):
            text = _read(rel)
            parts = text.split("this._lines.append(")
            self.assertEqual(len(parts) - 1, count, rel)
            for part in parts[:-1]:
                self.assertIn(f"if ({GLOBAL}) {INVALIDATE}();", part[-180:])
        report = _read("ai/OpexAI/task_report.nut")
        self.assertLess(report.index("this._lines.remove(toRemove[k]);"),
                        report.index(f"if ({GLOBAL} && toRemove.len() > 0) {INVALIDATE}();"))

    def test_stale_site_fails_in_the_existing_build_path(self):
        self.assertLess(
            self.build.index("local levelA = OpexAirLevelFootprint("),
            self.build.index("local okA = levelA.ok && AIAirport.BuildAirport("))
        self.assertLess(
            self.build.index("local levelB = OpexAirLevelFootprint("),
            self.build.index("local okB = levelB.ok && AIAirport.BuildAirport("))
        self.assertIn('result.reason = reuseA ? "HUB" : "AFAIL";', self.build)
        failure_b = self.build.split("if (airportB == null)", 1)[1].split("local stationA", 1)[0]
        self.assertIn('result.reason = reuseB ? "HUBB" : "BFAIL";', failure_b)
        self.assertIn("OpexAirInvalidateCachedSite(plan.siteB, airport);", failure_b)
        self.assertIn(
            'AIGameSettings.GetValue("economy.infrastructure_maintenance") == 0',
            failure_b)
        self.assertIn("OpexAirRollback(reuseA ? null : airportA, null, []);", failure_b)
        self.assertIn("OpexBuildFailureIsAbandonable(result)", self.task_air)
        abandon = _brace_body(self.lines, "function OpexBuildFailureIsAbandonable(")
        self.assertIn('result.reason == "RECOVERY"', abandon)
        self.assertIn('result.reason == "CASH"', abandon)
        self.assertIn("result.error == AIError.ERR_NOT_ENOUGH_CASH", abandon)
        self.assertIn("ERR_STATION_TOO_MANY_STATIONS_IN_TOWN", self.still)
        body = self.still.split("{", 1)[1]
        self.assertLess(body.index("if (reuse)"), body.index("site.town.id in stationLimitedTowns"))
        self.assertLess(
            body.index("site.town.id in stationLimitedTowns"),
            body.index("AIAirport.BuildAirport("))


if __name__ == "__main__":
    unittest.main()
