#!/usr/bin/env python3
"""Contrat AIR 03/10 5 : un miss age ou prix ne perime pas toute la geometrie.

air0310_endpoint_split vaut 0 aux quatre difficultes. A 1, et seulement si
C121_CATALOG_INCREMENTAL est actif, un miss catalogue "age", ou "input" dont
la distance et le monthlyPax V93 sont inchanges, ne bumpe pas
C121_CATALOG_ENDPOINT_EPOCH et ne vide pas AIR_C121_STATION_COVERAGE_CACHE.
Le plan recalcule la production et la concurrence, et reutilise les tuiles
si l'estampille ville/gare/geometrie a moins de 365 jours. Distance et
monthlyPax gardent l'invalidation globale. Aucune partie n'est lancee.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from sweeps.campaign_freeze import parse_ai_setting_specs

ROOT = Path(__file__).resolve().parents[1]

SETTING = "air0310_endpoint_split"
GLOBAL = "AIR0310_ENDPOINT_SPLIT"


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


def catalog_reason(entry, plan, date, v93, revs):
    """Meme chaine que OpexC121CatalogChoice. None = hit."""
    if entry is None:
        return "new"
    if entry["airportRev"] != revs["airportRev"]:
        return "engine"
    if entry["townA"] != revs["townA"] or entry["townB"] != revs["townB"]:
        return "town"
    if (entry["stationRevA"] != revs["stationRevA"]
            or entry["stationRevB"] != revs["stationRevB"]
            or entry["routes"] != plan["hubRoutes"]):
        return "station"
    if (entry["airportLearn"] != revs["airportLearn"]
            or entry["hubLearnA"] != revs["hubLearnA"]
            or entry["hubLearnB"] != revs["hubLearnB"]
            or entry["armLearn"] != revs["armLearn"]):
        return "learning"
    if date - entry["date"] >= 365:
        return "age"
    if (entry["distance"] != plan["distance"]
            or (v93 and entry["monthlyPax"] != plan["monthlyPax"])
            or entry["airportPrice"] != plan["airportPrice"]
            or entry["airportMaintenance"] != plan["airportMaintenance"]):
        return "input"
    return None


def geometry_cause(reason, entry_present, distance_same, v93, monthly_same):
    """null Python = ne pas incrementer l'epoque. Miroir de
    OpexC121EndpointSplitGeometryCause. L'age court-circuite avant l'input :
    une distance changee sous un miss age ne bumpe pas l'epoque."""
    if reason == "age":
        return None
    if reason != "input":
        return "input"
    if not entry_present:
        return "input"
    if not distance_same:
        return "distance"
    if v93 and not monthly_same:
        return "monthlyPax"
    return None


def route_catalog_miss(split_enabled, incremental, reason, cause):
    """Effet du miss sur l'epoque et le drapeau economie du plan."""
    refresh = reason in ("input", "age")
    econ = False
    stored = None
    if split_enabled and refresh:
        if cause is None:
            refresh = False
            econ = True
        else:
            stored = cause
    bumped = bool(refresh and incremental)
    return {
        "refresh_endpoints": refresh,
        "econ": econ,
        "stored_cause": stored,
        "epoch_bumped": bumped,
        "coverage_cache_cleared": bumped,
    }


def geom_miss_cause(cached, stamp):
    if cached is None or stamp is None or "catalogStamp" not in cached:
        return "absent"
    if cached.get("stopTiles") is None or cached.get("coverageTiles") is None:
        return "absent"
    old = cached["catalogStamp"]
    if old["town"] != stamp["town"]:
        return "town"
    if old["station"] != stamp["station"]:
        return "station"
    if old["geometry"] != stamp["geometry"]:
        return "geometry"
    if stamp["date"] < old["date"]:
        return "date"
    if stamp["date"] - old["date"] >= 365:
        return "age"
    return "fresh"


def geometry_fresh(cached, stamp):
    if cached is None or stamp is None:
        return False
    if cached.get("stopTiles") is None or cached.get("coverageTiles") is None:
        return False
    return geom_miss_cause(cached, stamp) == "fresh"


class EndpointWorld:
    """Cache partage. L'invalidation historique bumpe l'epoque et vide le
    cache de couverture de gare ; elle ne supprime pas les entrees."""

    def __init__(self):
        self.epoch = 0
        self.coverage = {"station-map": object()}
        self.endpoints = {}
        self.stats = None
        self.logs = []

    def invalidate(self, incremental):
        if not incremental:
            return
        self.epoch += 1
        self.coverage.clear()

    def note(self, split_enabled, decision_log, kind, cause):
        if not split_enabled:
            return
        if self.stats is None:
            self.stats = {
                "endpointGeomHits": 0,
                "endpointGeomMisses": 0,
                "econRecomputes": 0,
                "byCause": {},
            }
        stats = self.stats
        if kind == "geom_hit":
            stats["endpointGeomHits"] += 1
        elif kind == "geom_miss":
            stats["endpointGeomMisses"] += 1
            stats["byCause"][cause] = stats["byCause"].get(cause, 0) + 1
        elif kind == "econ":
            stats["econRecomputes"] += 1
        if decision_log and kind == "geom_miss":
            self.logs.append(
                f"cause={cause} geomHits={stats['endpointGeomHits']}"
                f" geomMisses={stats['endpointGeomMisses']}"
                f" econ={stats['econRecomputes']}"
            )


def serve_endpoint(world, *, split_enabled, incremental, econ_flag, force_flag,
                   miss_cause, key, stamp, caller_stops, caller_coverage,
                   decision_log=False):
    """Miroir de OpexAirB9DemandShadowEndpointCargo une fois la cle connue."""
    econ = bool(split_enabled and incremental and econ_flag)
    force = bool(incremental and force_flag)
    cached = world.endpoints.get(key)
    fresh = geometry_fresh(cached, stamp)
    if not force and not econ and cached is not None and fresh:
        return {"hit": True, "result": cached, "wrote": False, "union": False}
    deciding = caller_stops is None and caller_coverage is None
    geom_from_cache = bool(econ and deciding and fresh)
    if geom_from_cache:
        stops = cached["stopTiles"]
        coverage = cached["coverageTiles"]
    elif not deciding and caller_coverage is not None:
        stops = [] if caller_stops is None else caller_stops
        coverage = caller_coverage
    else:
        stops = [] if caller_stops is None else caller_stops
        coverage = caller_coverage if caller_coverage is not None else ("rebuilt", object())
    if econ and deciding:
        if geom_from_cache:
            world.note(split_enabled, decision_log, "geom_hit", None)
        else:
            world.note(split_enabled, decision_log, "geom_miss",
                       geom_miss_cause(cached, stamp))
    elif split_enabled and force and deciding:
        world.note(split_enabled, decision_log, "geom_miss",
                   miss_cause if miss_cause is not None else "input")
    union = ("union", object(), stops, coverage)
    if econ:
        world.note(split_enabled, decision_log, "econ", None)
    result = {
        "union": union,
        "stopTiles": stops,
        "coverageTiles": coverage,
        "catalogStamp": stamp,
    }
    keep_shared = econ and (geom_from_cache or caller_stops is not None
                            or caller_coverage is not None)
    wrote = False
    if not keep_shared:
        world.endpoints[key] = result
        wrote = True
    return {"hit": False, "result": result, "wrote": wrote, "union": True,
            "geom_from_cache": geom_from_cache, "keep_shared": keep_shared}


def _entry(**overrides):
    base = {
        "airportRev": 0, "townA": 0, "townB": 0, "stationRevA": 0,
        "stationRevB": 0, "routes": 1, "airportLearn": 0, "hubLearnA": 0,
        "hubLearnB": 0, "armLearn": 0, "date": 1000, "distance": 40,
        "monthlyPax": 80, "airportPrice": 10, "airportMaintenance": 2,
    }
    base.update(overrides)
    return base


def _plan(**overrides):
    base = {
        "hubRoutes": 1, "distance": 40, "monthlyPax": 80,
        "airportPrice": 10, "airportMaintenance": 2,
    }
    base.update(overrides)
    return base


def _revs(**overrides):
    base = {
        "airportRev": 0, "townA": 0, "townB": 0, "stationRevA": 0,
        "stationRevB": 0, "airportLearn": 0, "hubLearnA": 0,
        "hubLearnB": 0, "armLearn": 0,
    }
    base.update(overrides)
    return base


def _stamp(date=1100, town=0, station=0, geometry=0):
    return {"date": date, "town": town, "station": station, "geometry": geometry}


def _cached(stamp, marker="old-econ"):
    return {
        "marker": marker,
        "stopTiles": ("stops", marker),
        "coverageTiles": ("coverage", marker),
        "catalogStamp": dict(stamp),
    }


class TestAir0310EndpointSplit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.catalog = _read("ai/OpexAI/air_catalog_c121.nut")
        cls.coverage = _read("ai/OpexAI/air_coverage.nut")
        cls.planning = _read("ai/OpexAI/air_planning.nut")
        cls.economics = _read("ai/OpexAI/air_economics_c121.nut")
        cls.choice = _brace_body(cls.catalog, "function OpexC121CatalogChoice(")
        cls.cause = _brace_body(
            cls.catalog, "function OpexC121EndpointSplitGeometryCause(")
        cls.clear_flags = _brace_body(
            cls.catalog, "function OpexAir0310EndpointSplitClear(")
        cls.clear_snapshot = _brace_body(
            cls.catalog, "function OpexC121CatalogClearPlanSnapshot(")
        cls.endpoint = _brace_body(
            cls.coverage, "function OpexAirB9DemandShadowEndpointCargo(")
        cls.fresh = _brace_body(cls.coverage, "function OpexC121EndpointCacheFresh(")
        cls.geom_fresh = _brace_body(
            cls.coverage, "function OpexAir0310EndpointGeometryFresh(")
        cls.geom_cause = _brace_body(
            cls.coverage, "function OpexC121EndpointGeomMissCause(")
        cls.note = _brace_body(cls.coverage, "function OpexAir0310EndpointSplitNote(")
        cls.report = _brace_body(
            cls.coverage, "function OpexAir0310EndpointSplitReport(")
        cls.union = _brace_body(cls.coverage, "function OpexAirB9TownUnionMonthly(")
        cls.invalidate = _brace_body(
            cls.coverage, "function OpexC121InvalidateEndpointGeometry(")
        cls.station_lines = _brace_body(
            cls.catalog, "function OpexC121CatalogRefreshStationLines(")
        cls.finalize = _brace_body(cls.planning, "function OpexAirPlansFinalize(")
        cls.choose = _brace_body(
            cls.economics, "function OpexC121ChooseRoutePlane(")

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
        self.assertIn(
            f"{GLOBAL} = C121_CATALOG_INCREMENTAL\n"
            f'      && AIController.GetSetting("{SETTING}") != 0;',
            self.settings,
        )
        self.assertIn("AIR0310_ENDPOINT_STATS = null;", self.settings)
        self.assertNotIn(SETTING, self.persist)
        self.assertNotIn(GLOBAL, self.persist)
        self.assertNotIn("AIR0310_ENDPOINT_STATS", self.persist)
        self.assertNotIn("c121CatalogRefreshEndpointEcon", self.persist)
        self.assertNotIn("c121CatalogEndpointMissCause", self.persist)
        publish = (
            "AIR0310_INCREMENTAL_PUBLISH = C121_CATALOG_INCREMENTAL\n"
            '      && AIController.GetSetting("air0310_incremental_publish") != 0;'
        )
        self.assertLess(self.settings.index(publish), self.settings.index(
            f"{GLOBAL} = C121_CATALOG_INCREMENTAL"))

    def test_source_keeps_historical_path_and_cache_lot(self):
        self.assertEqual(_brace_balance(self.catalog), 0)
        self.assertEqual(_brace_balance(self.coverage), 0)
        self.assertEqual(_brace_balance(self.planning), 0)
        for body in (self.choice, self.cause, self.endpoint, self.note,
                     self.report, self.geom_cause):
            names = _explicit_locals(body)
            self.assertEqual(len(names), len(set(names)), names)
        self.assertEqual(
            self.catalog.count("delete plan.c121CatalogRefreshEndpoints;"), 2)
        self.assertIn(
            'plan.c121CatalogRefreshEndpoints <- reason == "input" || reason == "age";',
            self.choice)
        self.assertIn(
            "if (plan.c121CatalogRefreshEndpoints) OpexC121InvalidateEndpointGeometry();",
            self.choice)
        self.assertLess(
            self.choice.index("OpexC121CatalogClearPlanSnapshot(plan);"),
            self.choice.index("plan.c121CatalogRefreshEndpoints <-"))
        self.assertLess(
            self.choice.index("if (plan.c121CatalogRefreshEndpoints) OpexC121InvalidateEndpointGeometry();"),
            self.choice.index("choice = OpexC121ChooseRoutePlane"))
        self.assertEqual(self.choice.count("OpexAir0310EndpointSplitClear(plan);"), 2)
        self.assertIn("if (AIR0310_ENDPOINT_SPLIT && plan.c121CatalogRefreshEndpoints)",
                      self.choice)
        self.assertIn("c121Demand", self.clear_snapshot)
        self.assertNotIn("c121CatalogRefreshEndpointEcon", self.clear_snapshot)
        snapshot = self.choice[self.choice.index("C121_CATALOG_CACHE.rawset(key, {"):]
        self.assertNotIn("c121CatalogRefreshEndpointEcon", snapshot)
        self.assertNotIn("c121CatalogEndpointMissCause", snapshot)
        self.assertIn("cacheStamp == null || OpexC121EndpointCacheFresh", self.endpoint)
        self.assertIn("old.town == stamp.town && old.station == stamp.station", self.fresh)
        self.assertIn("old.geometry == stamp.geometry", self.fresh)
        self.assertIn("stamp.date - old.date < 365", self.fresh)
        self.assertIn("C121_CATALOG_ENDPOINT_EPOCH++;", self.invalidate)
        self.assertIn("AIR_C121_STATION_COVERAGE_CACHE.clear();", self.invalidate)
        self.assertNotIn("C121_AIR_ENDPOINT_CACHE", self.invalidate)
        self.assertIn("OpexC121InvalidateEndpointGeometry();", self.station_lines)
        self.assertIn("OpexC121InvalidateEndpointGeometry();", self.settings)
        self.assertIn('if (reason == "age") return null;', self.cause)
        self.assertLess(self.cause.index('reason == "age"'),
                        self.cause.index('reason != "input"'))
        self.assertLess(self.cause.index("entry.distance != plan.distance"),
                        self.cause.index("entry.monthlyPax != plan.monthlyPax"))
        self.assertNotIn("airportPrice", self.cause)
        self.assertNotIn("airportMaintenance", self.cause)
        self.assertIn("entry.airportPrice != plan.airport.price", self.choice)
        self.assertIn("entry.airportMaintenance != plan.airport.maintenance", self.choice)
        self.assertIn("V93_AIR_DEMAND_PRODUCTION && entry.monthlyPax != plan.monthlyPax",
                      self.cause)

    def test_endpoint_reuses_tiles_and_always_recomputes_union(self):
        self.assertNotIn("if (!econRefresh)", self.endpoint)
        self.assertIn(
            "local union = OpexAirB9TownUnionMonthly(\n"
            "      site.town, site.anchor, airportType, cargo, stops, stationId, coverageTiles);",
            self.endpoint)
        self.assertIn("OpexC121StationCompetitionBuckets(", self.union)
        self.assertLess(
            self.endpoint.index("if (geomFromCache) stops = cached.stopTiles;"),
            self.endpoint.index("if (reused) {"))
        self.assertLess(
            self.endpoint.index("if (geomFromCache) coverageTiles = cached.coverageTiles;"),
            self.endpoint.index("if (coverageTiles == null)"))
        self.assertIn(
            "local keepShared = econRefresh && (geomFromCache || stopTiles != null || sharedCoverageTiles != null);",
            self.endpoint)
        self.assertIn(
            "if (cacheKey != null && !keepShared) C121_AIR_ENDPOINT_CACHE.rawset(cacheKey, result);",
            self.endpoint)
        self.assertIn("a.stopTiles, a.coverageTiles", self.coverage)
        self.assertIn("b.stopTiles, b.coverageTiles", self.coverage)
        self.assertIn('return "absent";', self.geom_cause)
        self.assertIn('return "town";', self.geom_cause)
        self.assertIn('return "station";', self.geom_cause)
        self.assertIn('return "geometry";', self.geom_cause)
        self.assertIn('return "date";', self.geom_cause)
        self.assertIn('return "age";', self.geom_cause)
        self.assertIn("return OpexC121EndpointCacheFresh(cached, cacheStamp);", self.geom_fresh)

    def test_probe_is_outside_the_demand_span_except_decision_log_misses(self):
        self.assertIn("endpointGeomHits", self.note)
        self.assertIn("endpointGeomMisses", self.note)
        self.assertIn("econRecomputes", self.note)
        self.assertLess(
            self.note.index('if (!DECISION_LOG || kind != "geom_miss") return;'),
            self.note.index('OpexDecide("ENDPOINT_MISS", "cause=" + cause'))
        self.assertNotIn("OpexAir0310EndpointSplitReport", self.choose)
        self.assertNotIn("OpexSpanAgg(\"air.c121.demand\"", self.planning)
        self.assertIn("OpexAir0310EndpointSplitReport();", self.finalize)
        self.assertLess(
            self.finalize.index("c121_endpoint_misses="),
            self.finalize.index("OpexAir0310EndpointSplitReport();"))
        self.assertIn(
            "if ((DECISION_LOG || PROBE_SPAN_TRACE) && AIR0310_ENDPOINT_SPLIT)",
            self.finalize)
        self.assertIn('OpexDecide("ENDPOINT_MISS", "cause=" + causes', self.report)
        self.assertIn('local causes = "none";', self.report)

    def test_setting_off_keeps_global_invalidation_for_age_and_price(self):
        for reason, plan_over in (
            ("age", {}),
            ("input", {"airportPrice": 12}),
            ("input", {"airportMaintenance": 9}),
        ):
            entry = _entry()
            plan = _plan(**plan_over)
            found = catalog_reason(entry, plan, 1400 if reason == "age" else 1100, True, _revs())
            self.assertEqual(found, reason)
            cause = geometry_cause(found, True, True, True, True)
            self.assertIsNone(cause)
            off = route_catalog_miss(False, True, found, cause)
            self.assertTrue(off["epoch_bumped"])
            self.assertTrue(off["coverage_cache_cleared"])
            self.assertFalse(off["econ"])
            self.assertTrue(off["refresh_endpoints"])

    def test_distance_and_monthly_keep_global_invalidation(self):
        entry = _entry()
        distance = catalog_reason(
            entry, _plan(distance=41, airportPrice=99), 1100, True, _revs())
        self.assertEqual(distance, "input")
        cause = geometry_cause(distance, True, False, True, False)
        self.assertEqual(cause, "distance")
        routed = route_catalog_miss(True, True, distance, cause)
        self.assertTrue(routed["epoch_bumped"])
        self.assertEqual(routed["stored_cause"], "distance")
        self.assertFalse(routed["econ"])

        monthly = catalog_reason(entry, _plan(monthlyPax=1), 1100, True, _revs())
        self.assertEqual(monthly, "input")
        cause = geometry_cause(monthly, True, True, True, False)
        self.assertEqual(cause, "monthlyPax")
        routed = route_catalog_miss(True, True, monthly, cause)
        self.assertTrue(routed["epoch_bumped"])
        self.assertEqual(routed["stored_cause"], "monthlyPax")

        ignored = catalog_reason(entry, _plan(monthlyPax=1), 1100, False, _revs())
        self.assertIsNone(ignored)

    def test_age_or_price_does_not_bump_and_reuses_fresh_tiles(self):
        entry = _entry()
        for label, plan, date in (
            ("age", _plan(distance=99, monthlyPax=1, airportPrice=50), 2000),
            ("price", _plan(airportPrice=50), 1100),
            ("maintenance", _plan(airportMaintenance=7), 1100),
        ):
            reason = catalog_reason(entry, plan, date, True, _revs())
            self.assertEqual(reason, "age" if label == "age" else "input", label)
            same_distance = entry["distance"] == plan["distance"]
            same_monthly = entry["monthlyPax"] == plan["monthlyPax"]
            cause = geometry_cause(reason, True, same_distance, True, same_monthly)
            self.assertIsNone(cause, label)
            routed = route_catalog_miss(True, True, reason, cause)
            self.assertFalse(routed["epoch_bumped"], label)
            self.assertFalse(routed["coverage_cache_cleared"], label)
            self.assertTrue(routed["econ"], label)
            self.assertFalse(routed["refresh_endpoints"], label)

        world = EndpointWorld()
        old = _cached(_stamp())
        other = _cached(_stamp(), marker="other")
        world.endpoints["pax-a"] = old
        world.endpoints["pax-b"] = other
        coverage = world.coverage["station-map"]
        served = serve_endpoint(
            world, split_enabled=True, incremental=True, econ_flag=True,
            force_flag=False, miss_cause=None, key="pax-a", stamp=_stamp(),
            caller_stops=None, caller_coverage=None)
        self.assertFalse(served["hit"])
        self.assertTrue(served["union"])
        self.assertTrue(served["geom_from_cache"])
        self.assertFalse(served["wrote"])
        self.assertIs(world.endpoints["pax-a"], old)
        self.assertIs(world.endpoints["pax-b"], other)
        self.assertIs(served["result"]["stopTiles"], old["stopTiles"])
        self.assertIs(served["result"]["coverageTiles"], old["coverageTiles"])
        self.assertIsNot(served["result"], old)
        self.assertIs(world.coverage["station-map"], coverage)
        self.assertEqual(world.epoch, 0)
        self.assertEqual(world.stats["endpointGeomHits"], 1)
        self.assertEqual(world.stats["endpointGeomMisses"], 0)
        self.assertEqual(world.stats["econRecomputes"], 1)
        self.assertEqual(world.logs, [])

        mail = serve_endpoint(
            world, split_enabled=True, incremental=True, econ_flag=True,
            force_flag=False, miss_cause=None, key="mail-a", stamp=_stamp(),
            caller_stops=old["stopTiles"], caller_coverage=old["coverageTiles"])
        self.assertFalse(mail["wrote"])
        self.assertNotIn("mail-a", world.endpoints)
        self.assertEqual(world.stats["endpointGeomHits"], 1)
        self.assertEqual(world.stats["econRecomputes"], 2)
        self.assertIs(mail["result"]["stopTiles"], old["stopTiles"])

        untouched = serve_endpoint(
            world, split_enabled=True, incremental=True, econ_flag=False,
            force_flag=False, miss_cause=None, key="pax-b", stamp=_stamp(),
            caller_stops=None, caller_coverage=None)
        self.assertTrue(untouched["hit"])
        self.assertIs(untouched["result"], other)
        self.assertEqual(world.stats["econRecomputes"], 2)

    def test_stale_stamp_rebuilds_one_key_without_epoch_bump(self):
        base = _stamp(date=100)
        cases = {
            "absent": {"stopTiles": None, "coverageTiles": None, "catalogStamp": dict(base)},
            "town": _cached(_stamp(date=1100, town=1)),
            "station": _cached(_stamp(date=1100, station=4)),
            "geometry": _cached(_stamp(date=1100, geometry=3)),
            "date": _cached(_stamp(date=1200)),
            "age": _cached(_stamp(date=700)),
        }
        now = _stamp(date=1100)
        self.assertEqual(geom_miss_cause(None, now), "absent")
        self.assertEqual(geom_miss_cause(cases["absent"], now), "absent")
        for cause, cached in cases.items():
            if cause == "absent":
                continue
            self.assertEqual(geom_miss_cause(cached, now), cause)
            self.assertFalse(geometry_fresh(cached, now))
        self.assertEqual(geom_miss_cause(_cached(now), now), "fresh")

        world = EndpointWorld()
        stale = cases["age"]
        other = _cached(now, marker="kept")
        world.endpoints["pax-a"] = stale
        world.endpoints["pax-b"] = other
        served = serve_endpoint(
            world, split_enabled=True, incremental=True, econ_flag=True,
            force_flag=False, miss_cause=None, key="pax-a", stamp=now,
            caller_stops=None, caller_coverage=None, decision_log=True)
        self.assertTrue(served["wrote"])
        self.assertIs(world.endpoints["pax-a"], served["result"])
        self.assertIs(world.endpoints["pax-b"], other)
        self.assertEqual(world.epoch, 0)
        self.assertIn("station-map", world.coverage)
        self.assertEqual(world.stats["endpointGeomMisses"], 1)
        self.assertEqual(world.stats["byCause"], {"age": 1})
        self.assertEqual(world.stats["econRecomputes"], 1)
        self.assertEqual(world.logs, ["cause=age geomHits=0 geomMisses=1 econ=0"])

    def test_distance_miss_bumps_epoch_and_logs_cause_without_touching_other_plans_early(self):
        world = EndpointWorld()
        old = _cached(_stamp())
        world.endpoints["pax-a"] = old
        routed = route_catalog_miss(True, True, "input", "distance")
        if routed["epoch_bumped"]:
            world.invalidate(True)
        self.assertEqual(world.epoch, 1)
        self.assertEqual(world.coverage, {})
        served = serve_endpoint(
            world, split_enabled=True, incremental=True, econ_flag=False,
            force_flag=True, miss_cause="distance", key="pax-a",
            stamp=_stamp(geometry=world.epoch), caller_stops=None,
            caller_coverage=None, decision_log=True)
        self.assertTrue(served["wrote"])
        self.assertIsNot(world.endpoints["pax-a"], old)
        self.assertEqual(world.stats["byCause"], {"distance": 1})
        self.assertEqual(world.stats["econRecomputes"], 0)
        self.assertFalse(geometry_fresh(old, _stamp(geometry=world.epoch)))

    def test_other_reasons_do_not_take_the_split(self):
        entry = _entry()
        plan = _plan()
        samples = {
            "engine": catalog_reason(entry, plan, 1100, True, _revs(airportRev=1)),
            "town": catalog_reason(entry, plan, 1100, True, _revs(townA=2)),
            "station": catalog_reason(entry, plan, 1100, True, _revs(stationRevB=3)),
            "learning": catalog_reason(entry, plan, 1100, True, _revs(armLearn=1)),
            "new": catalog_reason(None, plan, 1100, True, _revs()),
        }
        for reason in samples.values():
            routed = route_catalog_miss(True, True, reason, geometry_cause(
                reason, True, True, True, True))
            self.assertFalse(routed["epoch_bumped"])
            self.assertFalse(routed["econ"])
            self.assertFalse(routed["refresh_endpoints"])

    def test_split_without_incremental_does_not_run(self):
        routed = route_catalog_miss(False, False, "age", None)
        self.assertFalse(routed["epoch_bumped"])
        self.assertFalse(routed["econ"])
        world = EndpointWorld()
        old = _cached(_stamp())
        world.endpoints["pax-a"] = old
        served = serve_endpoint(
            world, split_enabled=False, incremental=True, econ_flag=True,
            force_flag=True, miss_cause=None, key="pax-a", stamp=_stamp(),
            caller_stops=None, caller_coverage=None)
        self.assertTrue(served["wrote"])
        self.assertIsNone(world.stats)
        self.assertEqual(world.logs, [])


if __name__ == "__main__":
    unittest.main()
