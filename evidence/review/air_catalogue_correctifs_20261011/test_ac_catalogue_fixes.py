"""Four isolated catalogue fixes. Frozen-state Python models + source contracts.

NOT a Squirrel interpreter or an economic / opcode neutrality test.
The production flags are deliberately OFF until isolated validation.
"""

from dataclasses import dataclass, field
from pathlib import Path
import itertools
import unittest

ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai/OpexAI/air_planning.nut").read_text(encoding="utf-8")
SCHED = (ROOT / "ai/OpexAI/scheduler_tasks.nut").read_text(encoding="utf-8")
ORCH = (ROOT / "ai/OpexAI/orchestrator.nut").read_text(encoding="utf-8")
PRE = (ROOT / "ai/OpexAI/globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai/OpexAI/info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai/OpexAI/settings.nut").read_text(encoding="utf-8")
LAYERS = ("towns", "industries", "lines", "engines.rail", "engines.road",
          "engines.air", "engines.water")
DEPS = {"air": ("towns", "engines.air", "lines"),
        "rail_pax": ("towns", "engines.rail", "lines"),
        "rail_freight": ("industries", "engines.rail", "lines"),
        "road_pax": ("towns", "engines.road", "lines"),
        "road_freight": ("industries", "engines.road", "lines"),
        "water": ("towns", "engines.water", "lines"),
        "fleet": ("lines", "engines.rail", "engines.road", "engines.air", "engines.water"),
        "rail": ("towns", "industries", "engines.rail", "lines"),
        "road": ("towns", "industries", "engines.road", "lines")}


def function(source, needle):
    a = source.index(needle)
    b = source.index("{", a)
    depth = 0
    for c in range(b, len(source)):
        if source[c] == "{":
            depth += 1
        elif source[c] == "}":
            depth -= 1
            if depth == 0:
                return source[a:c+1]
    raise AssertionError(needle)


DISCOVER = function(AIR, "function OpexAirPlansDiscoverHubs(")
REFRESH_HUBS = function(AIR, "function OpexAir0310RefreshHubRoutes(")
SITES = function(AIR, "function OpexAC04ExtraSiteAlreadyKnown(")
COUNT = function(AIR, "function OpexAir0310CountStationRoutes(")
START = function(SCHED, "function OpexC78StartCatalogAirRebuild(")
CONTINUE = function(SCHED, "function OpexC78ContinueCatalogAirRebuild(")
ACK = function(ORCH, "function OpexAC06AcknowledgeSnapshot(")
SNAP = function(ORCH, "function OpexAC06SnapshotLayer(")


def discover_orphans_model(lines, airports, max_routes, *, fix):
    """Approximation de la boucle saturée suivie du fallback orphan."""
    hubs, seen = [], set()
    for station in lines:
        if station in seen:
            continue
        count = lines.count(station)
        if count >= max_routes[station]:
            continue
        seen.add(station)
        hubs.append((station, count, 0))
    for station in airports:
        if station in seen:
            continue
        count = lines.count(station) if fix else 0
        if fix and count >= max_routes[station]:
            continue
        seen.add(station)
        hubs.append((station, count, int(not fix or count == 0)))
    return hubs


def supplement_sites_model(initial, proposals, limit, *, fix):
    sites = list(initial)
    for proposal in proposals:
        if len(sites) >= limit:
            break
        if fix and any(s[1] == proposal[1] for s in sites):
            continue
        sites.append(proposal)
    return sites


@dataclass
class Revisions:
    current: dict = field(default_factory=lambda: {k: 0 for k in LAYERS})
    ack: dict = field(default_factory=lambda: {k: 0 for k in LAYERS})
    consumed: dict = field(default_factory=lambda: {m: {k: 0 for k in deps}
                                                    for m, deps in DEPS.items()})
    def bump(self, layer):
        self.current[layer] += 1
    def acknowledge(self, snapshot=None):
        # OFF: legacy ACK-all (consume whatever happened during C78).
        # ON: acknowledge no further than captured revision, but never
        # regress previous C77 mode-specific consumption.
        covered = self.current if snapshot is None else snapshot
        for key in LAYERS:
            self.ack[key] = max(self.ack[key], covered[key])
        for mode, deps in DEPS.items():
            for key in deps:
                self.consumed[mode][key] = max(self.consumed[mode][key], covered[key])
    def pending(self):
        return {key for key in LAYERS if self.current[key] > self.ack[key]}


class ACIsolatedFixes(unittest.TestCase):
    def test_three_flags_are_registered_and_off_by_default(self):
        for name in ("ac04_hub_route_fix", "ac04_extra_site_dedup",
                     "ac05_skip_unused_hub_income", "ac06_c76_snapshot_ack"):
            self.assertIn(f'name = "{name}"', INFO)
            self.assertIn(f'AIController.GetSetting("{name}")', SETTINGS)
            begin = INFO.index(f'name = "{name}"')
            end = INFO.index("});", begin)
            self.assertIn("easy_value = 0, medium_value = 0, hard_value = 0", INFO[begin:end])
        for var in ("AC04_HUB_ROUTE_FIX", "AC04_EXTRA_SITE_DEDUP",
                    "AC05_SKIP_UNUSED_HUB_INCOME", "AC06_C76_SNAPSHOT_ACK"):
            self.assertIn(var + " <- false;", PRE)

    def test_ac05_v86_precomputation_skipped_only_when_c121_ignores_it(self):
        hub_body = function(AIR, "function OpexAirPlansHubToHub(")
        self.assertIn("AIR_HUBHUB_MARGINAL && !(AC05_SKIP_UNUSED_HUB_INCOME && C121_AIR_ECONOMICS)", hub_body)
        self.assertIn("AIR_HUBHUB_MARGINAL && !C121_AIR_ECONOMICS", hub_body)
        self.assertIn("hubAvgIncome[i]", hub_body)
        self.assertIn("hubAvgIncome[j]", hub_body)
        # Every case in which V86 is actually read must still precompute it.
        for marginal, c121, toggle in itertools.product((False, True), repeat=3):
            computed = marginal and not (toggle and c121)
            read = marginal and not c121
            self.assertFalse(read and not computed)
            if not toggle:
                self.assertEqual(computed, marginal)

    def test_ac04a_rejects_saturated_lines_even_if_orphan_fallback_would_include(self):
        self.assertIn("OpexAir0310CountStationRoutes(ctx, st)", DISCOVER)
        self.assertIn("orphanRoutes >= OpexAirAirportMaxRoutes(existingType)", DISCOVER)
        self.assertIn("routes = orphanRoutes", DISCOVER)
        self.assertIn("AC04_HUB_ROUTE_FIX && orphanRoutes > 0 ? 0 : 1", DISCOVER)
        self.assertIn("if (isOrphan && !AC04_HUB_ROUTE_FIX) continue;", REFRESH_HUBS)
        self.assertIn("OpexAir0310CountStationRoutes(ctx, hubs[i].stationId)", REFRESH_HUBS)
        self.assertIn("if (stationId in hubIndex.routes) return hubIndex.routes[stationId];", COUNT)
        for count in (0, 1, 2, 3, 4, 7, 8, 9, 12):
            max_routes = {11: 8, 91: 8}
            lines = [11] * count
            old = discover_orphans_model(lines, [11, 91], max_routes, fix=False)
            new = discover_orphans_model(lines, [11, 91], max_routes, fix=True)
            if count >= 8:
                self.assertIn((11, 0, 1), old)
                self.assertNotIn(11, [h[0] for h in new])
            else:
                self.assertEqual([(h[0], h[1]) for h in new],
                                 [(11, count), (91, 0)])
            self.assertIn((91, 0, 1), new)

    def test_ac04b_dedups_anchor_not_town_and_only_under_flag(self):
        self.assertIn('site.anchor == candidate.anchor', SITES)
        self.assertIn("AC04_EXTRA_SITE_DEDUP && OpexAC04ExtraSiteAlreadyKnown(sites, extraSite)", DISCOVER)
        # Two physical anchors in the same town must BOTH remain valid.
        old = [(42, 100)]
        proposed = [(42, 100), (42, 200), (43, 300), (43, 300)]
        self.assertEqual(supplement_sites_model(old, proposed, 4, fix=True),
                         [(42, 100), (42, 200), (43, 300)])
        self.assertEqual(supplement_sites_model(old, proposed, 4, fix=False),
                         [(42, 100), (42, 100), (42, 200), (43, 300)])
        for n, budget in itertools.product(range(10), (0, 1, 2, 4, 8)):
            initial = [(n, n * 10)]
            proposals = [(t % 4, t * 10 % 37) for t in range(n)]
            got = supplement_sites_model(initial, proposals, budget, fix=True)
            anchors = [v for _, v in got]
            self.assertEqual(len(anchors), len(set(anchors)))
            self.assertTrue(len(got) <= max(1, budget))

    def test_ac06_records_snapshot_and_never_acks_late_event(self):
        self.assertIn("owner._c76SaveRevisions() : null", START)
        self.assertIn("OpexAC06AcknowledgeSnapshot(owner, s.c76StartRevisions);", CONTINUE)
        self.assertIn("owner._c76AcknowledgeAllLayers();", CONTINUE)
        for key in ("towns", "industries", "lines", "engines_rail", "engines_road",
                    "engines_air", "engines_water"):
            self.assertIn("snapshot." + key, SNAP + ACK)
        self.assertIn("local previous = layer in consumed ? consumed[layer] : 0;", ACK)
        rev = Revisions()
        rev.bump("towns")
        snapshot = dict(rev.current)  # after initial catalog.refresh
        for key in ("lines", "engines.air", "towns", "industries"):
            rev.bump(key)
        off = Revisions(current=dict(rev.current))
        off.acknowledge()
        self.assertEqual(off.pending(), set())
        rev.acknowledge(snapshot)
        self.assertEqual(rev.pending(), {"lines", "engines.air", "towns", "industries"})
        self.assertEqual(rev.ack["towns"], 1)
        self.assertEqual(rev.consumed["air"]["towns"], 1)

    def test_ac06_preserves_existing_mode_consumption_and_monotonic_counters(self):
        rev = Revisions()
        snap = dict(rev.current)
        for _ in range(3):
            rev.bump("engines.air")
        # Concurrent reactive C77 regeneration already consumed engine rev=3.
        rev.consumed["air"]["engines.air"] = 3
        rev.ack["engines.air"] = 1
        rev.acknowledge(snap)
        self.assertEqual(rev.consumed["air"]["engines.air"], 3)
        self.assertEqual(rev.ack["engines.air"], 1)
        self.assertEqual(rev.pending(), {"engines.air"})
        # Next completed regen captures latest and can consume it.
        rev.acknowledge(dict(rev.current))
        self.assertEqual(rev.pending(), set())
        self.assertEqual(rev.consumed["air"]["engines.air"], 3)

    def test_disabled_default_keeps_old_orphans_duplicates_and_ack(self):
        self.assertEqual(discover_orphans_model([11] * 8, [11], {11: 8}, fix=False),
                         [(11, 0, 1)])
        self.assertEqual(supplement_sites_model([(42, 100)], [(42, 100)], 2, fix=False),
                         [(42, 100), (42, 100)])
        rev = Revisions()
        captured = dict(rev.current)
        rev.bump("lines")
        rev.acknowledge()  # OFF ignores captured value
        self.assertNotEqual(rev.ack, captured)
        self.assertFalse(rev.pending())


if __name__ == "__main__":
    unittest.main()
