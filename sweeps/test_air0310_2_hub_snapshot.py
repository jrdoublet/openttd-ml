#!/usr/bin/env python3
"""Contrat statique AIR 03/10 2 : snapshot ordonne des hubs entre tranches.

air0310_hub_snapshot vaut 0 aux quatre difficultes. A 0, chaque tranche
redécouvre. A 1, et seulement si C121_CATALOG_INCREMENTAL est actif, le meme
combo avec la meme signature reprend hubs et sites sans OpexAirPlansDiscoverHubs.
Aucune partie n'est lancee.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from sweeps.campaign_freeze import parse_ai_setting_specs

ROOT = Path(__file__).resolve().parents[1]

SETTING = "air0310_hub_snapshot"
GLOBAL = "AIR0310_HUB_SNAPSHOT"


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


def _naive_body(source, signature):
    """Extracteur sans ignorer commentaires ni chaines, comme test_c77."""
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


def _pair_key(tile_a, tile_b):
    if tile_a > tile_b:
        tile_a, tile_b = tile_b, tile_a
    return f"air|{tile_a}|{tile_b}"


def _signature(lines, station_count):
    live = 0
    for line in lines or []:
        if line.get("mode") != "air":
            continue
        if line.get("deadStreak", 0) >= 2:
            continue
        live += 1
    return f"{live}:{station_count}"


def _decide(snap, combo_index, signature, cursors):
    """Meme combo et meme signature : reuse. Meme combo sinon : curseurs au depart."""
    if snap is not None and snap["combo"] == combo_index and snap["sig"] == signature:
        return "reuse", dict(cursors)
    if snap is not None and snap["combo"] == combo_index:
        return "invalidate", {
            "hubPhase": 0,
            "hubSiteI": 0,
            "hubSiteJ": 0,
            "hubHubI": 0,
            "hubHubJ": 1,
        }
    return "discover", dict(cursors)


def _refresh_routes(hubs, orphan, routes_by_station):
    refreshed = []
    for index, hub in enumerate(hubs):
        copy = dict(hub)
        is_orphan = orphan is not None and index < len(orphan) and orphan[index]
        if not is_orphan:
            copy["routes"] = routes_by_station.get(copy["stationId"], 0)
        refreshed.append(copy)
    return refreshed


def _skip_key(arm, airport_type, tile_a, tile_b):
    return f"{arm}|{airport_type}|{_pair_key(tile_a, tile_b)}"


class TestAir0310_2HubSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.planning = _read("ai/OpexAI/air_planning.nut")
        cls.plans = _function_body(cls.planning, "function OpexAirPlans(")
        cls.discover = _function_body(cls.planning, "function OpexAirPlansDiscoverHubs(")
        cls.hub_site = _function_body(cls.planning, "function OpexAirPlansHubToSite(")
        cls.hub_hub = _function_body(cls.planning, "function OpexAirPlansHubToHub(")
        cls.prepare = _function_body(cls.planning, "function OpexAir0310HubSnapshotPrepare(")
        cls.store = _function_body(cls.planning, "function OpexAir0310HubSnapshotStore(")
        cls.count = _function_body(cls.planning, "function OpexAir0310HubSnapshotCount(")
        cls.signature = _function_body(
            cls.planning, "function OpexAir0310HubTopologySignature("
        )
        cls.copy_hubs = _function_body(cls.planning, "function OpexAir0310CopyHubList(")
        cls.refresh = _function_body(cls.planning, "function OpexAir0310RefreshHubRoutes(")
        cls.hub_ok = _function_body(cls.planning, "function OpexAir0310RestoredHubUsable(")
        cls.site_ok = _function_body(cls.planning, "function OpexAir0310RestoredSiteUsable(")
        cls.remember = _function_body(
            cls.planning, "function OpexAir0310RememberPublishedHubPairs("
        )
        cls.skip = _function_body(cls.planning, "function OpexAir0310SkipRestoredPair(")
        reuse_at = cls.plans.index("if (!reuseHubs) {")
        cls.reuse_block = cls.plans[reuse_at:cls.plans.index(
            'OpexC56TaskLog("STAGE_EXIT", "air_hub_discover"', reuse_at
        )]

    def test_setting_defaults_to_one_and_is_not_persisted(self):  # adopte le 04/10 (optimisation d'opcodes)
        self.assertEqual(self.info.count(f'name = "{SETTING}"'), 1)
        block = _setting_block(self.info, SETTING)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)
        self.assertIn("step_size = 1", block)
        self.assertIn("1 = on (default), 0 = rediscover every slice", block)
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

    def test_span_wraps_only_a_real_discovery(self):
        call = "OpexAirPlansDiscoverHubs(ctx, combo, airport, plane);"
        self.assertEqual(self.planning.count(call), 1)
        self.assertEqual(self.plans.count(call), 1)
        self.assertEqual(self.planning.count('OpexSpanBegin("air.hub_discover")'), 1)
        self.assertIn("local reuseHubs = false;", self.plans)
        self.assertLess(
            self.plans.index("local reuseHubs = false;"),
            self.plans.index("if (AIR0310_HUB_SNAPSHOT && ctx.sliced)"),
        )
        self.assertLess(
            self.plans.index("OpexAir0310HubSnapshotPrepare(ctx, comboIndex, airport, plane);"),
            self.plans.index("if (!reuseHubs) {"),
        )
        self.assertIn('OpexSpanBegin("air.hub_discover")', self.reuse_block)
        self.assertIn(call, self.reuse_block)
        self.assertLess(
            self.reuse_block.index('OpexSpanBegin("air.hub_discover")'),
            self.reuse_block.index(call),
        )
        self.assertLess(
            self.reuse_block.index(call),
            self.reuse_block.index("if (spDisc != null) OpexSpanEnd(spDisc);"),
        )
        self.assertLess(
            self.reuse_block.index("if (spDisc != null) OpexSpanEnd(spDisc);"),
            self.reuse_block.index("OpexAir0310HubSnapshotStore(ctx, comboIndex);"),
        )
        self.assertIn("if (AIR0310_HUB_SNAPSHOT) ctx.air0310HubOrphan <- [];", self.reuse_block)
        self.assertLess(
            self.reuse_block.index("ctx.air0310HubOrphan <- [];"),
            self.reuse_block.index(call),
        )
        self.assertNotIn("OpexAir0310HubSnapshotPrepare", self.reuse_block)

    def test_snapshot_keeps_order_signature_and_resets_cursors(self):
        for field in ("combo = comboIndex", "sig = sig", "hubs = OpexAir0310CopyHubList(ctx.hubs)",
                      "sites = OpexAir0310CopySiteList(ctx.sites)", "orphan = orphanCopy"):
            self.assertIn(field, self.store)
        self.assertNotIn("hubAvgIncome", self.store)
        self.assertNotIn("GetCargoIncome", self.store)
        self.assertIn('if (("deadStreak" in line) && line.deadStreak >= 2) continue;', self.signature)
        self.assertIn("AIStationList(AIStation.STATION_AIRPORT)", self.signature)
        self.assertIn("stationList.Count()", self.signature)
        self.assertIn("return live + \":\" + stations;", self.signature)
        self.assertIn("ctx.hubs = OpexAir0310CopyHubList(snap.hubs);", self.prepare)
        self.assertIn("ctx.sites = OpexAir0310CopySiteList(snap.sites);", self.prepare)
        self.assertIn("OpexAir0310RefreshHubRoutes(ctx,", self.prepare)
        self.assertIn('return "reuse";', self.prepare)
        self.assertIn("delete resumeState.air0310HubSnap;", self.prepare)
        self.assertIn("resumeState.hubPhase <- 0;", self.prepare)
        self.assertIn("resumeState.hubSiteI <- 0;", self.prepare)
        self.assertIn("resumeState.hubSiteJ <- 0;", self.prepare)
        self.assertIn("resumeState.hubHubI <- 0;", self.prepare)
        self.assertIn("resumeState.hubHubJ <- 1;", self.prepare)
        self.assertIn('return "invalidate";', self.prepare)
        self.assertIn('return "discover";', self.prepare)
        self.assertLess(
            self.prepare.index('return "reuse";'),
            self.prepare.index("delete resumeState.air0310HubSnap;"),
        )
        self.assertIn(
            'if ("air0310HubSnap" in ctx.resumeState) delete ctx.resumeState.air0310HubSnap;',
            self.plans,
        )
        self.assertIn(
            'if ("air0310HubSkip" in ctx.resumeState) delete ctx.resumeState.air0310HubSkip;',
            self.plans,
        )
        self.assertNotIn("air0310HubCounts", self.plans[self.plans.index("if (AIR0310_HUB_SNAPSHOT) {"):])

    def test_dynamic_routes_are_refreshed_and_endpoints_rechecked(self):
        self.assertIn("town = hub.town", self.copy_hubs)
        self.assertIn("anchor = hub.anchor", self.copy_hubs)
        self.assertIn("stationId = hub.stationId", self.copy_hubs)
        self.assertIn("routes = hub.routes", self.copy_hubs)
        self.assertNotIn("orphan", self.copy_hubs)
        self.assertIn("if (isOrphan) continue;", self.refresh)
        self.assertIn(
            "hubs[i].routes = OpexAir0310CountStationRoutes(ctx, hubs[i].stationId);",
            self.refresh,
        )
        self.assertIn("AIAirport.IsAirportTile(hub.anchor)", self.hub_ok)
        self.assertIn("AIStation.IsValidStation(hub.stationId)", self.hub_ok)
        self.assertIn(
            "hub.routes >= OpexAirAirportMaxRoutes(AIAirport.GetAirportType(hub.anchor))",
            self.hub_ok,
        )
        self.assertIn(
            "OpexAirSiteStillBuildable(site, airport, plane, false, ctx.stationLimitedTowns)",
            self.site_ok,
        )
        self.assertNotIn("ctx.hubs.remove", self.hub_ok)
        self.assertNotIn("ctx.sites.remove", self.site_ok)
        for arm, body, needle in (
            ("hubsite", self.hub_site, 'OpexAir0310SkipRestoredPair(ctx, airport, "hubsite", hub, null, site, plane)'),
            ("hubhub", self.hub_hub, 'OpexAir0310SkipRestoredPair(ctx, airport, "hubhub", hub1, hub2, null, plane)'),
        ):
            self.assertIn(f"if (AIR0310_HUB_SNAPSHOT && (ctx.air0310HubRestored || ctx.air0310HubSkip != null)", body)
            self.assertIn(needle, body)
            self.assertLess(body.index(needle), body.index("if (EXP_AIR_HUB_PAIR_PREFILTER"))
        self.assertLess(
            self.hub_site.index("local site = sites[sj];"),
            self.hub_site.index('OpexAir0310SkipRestoredPair(ctx, airport, "hubsite"'),
        )
        self.assertLess(
            self.hub_site.index('OpexAir0310SkipRestoredPair(ctx, airport, "hubsite"'),
            self.hub_site.index("CATALOG_COST_ACTIVE.airHubSitePairs++"),
        )
        self.assertLess(
            self.hub_hub.index("local hub1 = hubs[i];"),
            self.hub_hub.index("CATALOG_COST_ACTIVE.airHubHubPairs++"),
        )
        self.assertLess(
            self.hub_hub.index('OpexAir0310SkipRestoredPair(ctx, airport, "hubhub"'),
            self.hub_hub.index("CATALOG_COST_ACTIVE.airHubHubPairs++"),
        )
        self.assertEqual(self.hub_hub.count("local hub1 = hubs[i];"), 1)
        self.assertEqual(self.hub_hub.count("local hub2 = hubs[j];"), 1)
        self.assertLess(
            self.hub_hub.index("if (AIR_HUBHUB_MARGINAL)"),
            self.hub_hub.index("for (local i = resumeI; i < hubs.len(); i++)"),
        )
        self.assertIn("AICargo.GetCargoIncome(catalog.paxCargo, dist, incomeDays)", self.hub_hub)
        self.assertIn('plan.arm + "|" + airportType + "|" + OpexAirPairKey(plan.siteA, plan.siteB)', self.remember)
        self.assertNotIn("plan.plane", self.remember)
        self.assertIn("if (!ctx.air0310HubRestored) return false;", self.skip)
        self.assertIn("if (AIR0310_HUB_SNAPSHOT) OpexAir0310NoteHubOrigin(ctx, 0);", self.discover)
        self.assertIn("if (AIR0310_HUB_SNAPSHOT) OpexAir0310NoteHubOrigin(ctx, 1);", self.discover)
        self.assertLess(
            self.discover.index("OpexAir0310NoteHubOrigin(ctx, 0);"),
            self.discover.index("OpexAir0310NoteHubOrigin(ctx, 1);"),
        )

    def test_probe_counts_are_exclusive_and_gated(self):
        self.assertIn('resumeState.air0310HubCounts <- { discover = 0, reuse = 0, invalidate = 0 };', self.count)
        self.assertIn('if (kind == "discover") counts.discover++;', self.count)
        self.assertIn('else if (kind == "reuse") counts.reuse++;', self.count)
        self.assertIn('else if (kind == "invalidate") counts.invalidate++;', self.count)
        self.assertIn("if (PROBE_SPAN_TRACE || C56_TASK_TRACE)", self.count)
        self.assertIn(
            'OpexDecide("AIR0310_HUB_SNAPSHOT", "discover=" + counts.discover\n'
            '        + " reuse=" + counts.reuse\n'
            '        + " invalidate=" + counts.invalidate);',
            self.count,
        )
        self.assertIn("OpexAir0310HubSnapshotCount(ctx, hubSnapAction);", self.plans)

    def test_new_functions_parse_and_have_unique_locals(self):
        self.assertEqual(_brace_balance(self.planning), 0)
        names = (
            "OpexAir0310HubTopologySignature",
            "OpexAir0310NoteHubOrigin",
            "OpexAir0310CopyHubList",
            "OpexAir0310CopySiteList",
            "OpexAir0310CountStationRoutes",
            "OpexAir0310RefreshHubRoutes",
            "OpexAir0310RestoredHubUsable",
            "OpexAir0310RestoredSiteUsable",
            "OpexAir0310RememberPublishedHubPairs",
            "OpexAir0310SkipRestoredPair",
            "OpexAir0310HubSnapshotPrepare",
            "OpexAir0310HubSnapshotStore",
            "OpexAir0310HubSnapshotCount",
        )
        for name in names:
            signature = f"function {name}("
            body = _naive_body(self.planning, signature)
            self.assertEqual(_brace_balance(body), 0, name)
            locals_ = _explicit_locals(body)
            self.assertEqual(sorted(locals_), sorted(set(locals_)), name)
        plans = _naive_body(self.planning, "function OpexAirPlans(")
        self.assertIn("return finalPlan;", plans)
        self.assertEqual(plans.count("OpexAirPlansDiscoverHubs(ctx, combo, airport, plane);"), 1)
        self.assertEqual(plans.count("local spDisc"), 1)
        self.assertEqual(plans.count("local reuseHubs"), 1)
        self.assertEqual(plans.count("local hubSnapAction"), 1)

    def test_decision_model_reuses_or_resets_without_reordering_cursors(self):
        cursors = {"hubPhase": 1, "hubSiteI": 3, "hubSiteJ": 4, "hubHubI": 2, "hubHubJ": 5}
        snap = {"combo": 2, "sig": "4:6"}
        action, kept = _decide(snap, 2, "4:6", cursors)
        self.assertEqual(action, "reuse")
        self.assertEqual(kept, cursors)
        action, reset = _decide(snap, 2, "5:6", cursors)
        self.assertEqual(action, "invalidate")
        self.assertEqual(reset["hubPhase"], 0)
        self.assertEqual(reset["hubSiteI"], 0)
        self.assertEqual(reset["hubSiteJ"], 0)
        self.assertEqual(reset["hubHubI"], 0)
        self.assertEqual(reset["hubHubJ"], 1)
        action, kept = _decide(snap, 3, "5:6", cursors)
        self.assertEqual(action, "discover")
        self.assertEqual(kept, cursors)
        action, kept = _decide(None, 2, "4:6", cursors)
        self.assertEqual(action, "discover")
        self.assertEqual(kept["hubHubJ"], 5)

    def test_route_refresh_and_publish_key_model(self):
        hubs = [
            {"stationId": 10, "routes": 2, "anchor": 1},
            {"stationId": 11, "routes": 0, "anchor": 2},
            {"stationId": 12, "routes": 9, "anchor": 3},
        ]
        refreshed = _refresh_routes(hubs, [0, 1, 0], {10: 4, 12: 1})
        self.assertEqual([hub["routes"] for hub in refreshed], [4, 0, 1])
        self.assertEqual(hubs[0]["routes"], 2)
        self.assertEqual(_signature(
            [{"mode": "air"}, {"mode": "air", "deadStreak": 2}, {"mode": "rail", "deadStreak": 0}],
            3,
        ), "1:3")
        published = {_skip_key("hubhub", 7, 30, 10)}
        self.assertIn(_skip_key("hubhub", 7, 10, 30), published)
        self.assertNotIn(_skip_key("hubsite", 7, 10, 30), published)
        self.assertNotIn(_skip_key("hubhub", 8, 10, 30), published)
        self.assertNotIn("plane", _skip_key("hubhub", 7, 10, 30))


if __name__ == "__main__":
    unittest.main()
