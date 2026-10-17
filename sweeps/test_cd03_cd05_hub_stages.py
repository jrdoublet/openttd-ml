"""CD03-CD05: source contracts and frozen state transitions for AIR hub stages.

These tests verify the mechanical extraction of discovery, hub->site and combo
closure. No Squirrel VM runs here; test budgets/ops are NOT game opcode counts.
"""

from dataclasses import dataclass, field
from pathlib import Path
import unittest


AIR = (Path(__file__).resolve().parents[1] /
       "ai/OpexAI/air_planning.nut").read_text(encoding="utf-8")


def fn(name):
    start = AIR.index("function " + name + "(")
    brace = AIR.index("{", start)
    depth = 0
    for pos in range(brace, len(AIR)):
        depth += (AIR[pos] == "{") - (AIR[pos] == "}")
        if depth == 0:
            return AIR[start:pos + 1]
    raise AssertionError("unclosed Squirrel function " + name)


DISCOVERY = fn("OpexAirPlansHubDiscoveryPhase")
HUB_SITE = fn("OpexAirPlansHubToSitePhase")
CLOSE = fn("OpexAirPlansCompleteCombo")
DRIVER = fn("OpexAirPlans")


def discovery_step(snapshot, signature, *, sliced=True, feature=True):
    """Immutable stub for a frozen snapshot. Rediscovery is not a suspension."""
    actions = []
    if sliced and feature:
        if snapshot is not None and snapshot["signature"] == signature:
            actions.append("reuse")
        elif snapshot is not None:
            actions.append("invalidate")
        else:
            actions.append("discover")
    else:
        actions.append("feature_off")
    reuse = actions == ["reuse"]
    if not reuse:
        actions.extend(["clear_orphans", "discover_hubs", "store_snapshot"])
    actions.append("post73_probe")
    return actions


def hub_site_step(*, sliced, incremental, hub_phase, builder_done):
    """Only store phase=1 after builder success; on retry skip completed work."""
    call_builder = not sliced or not incremental or hub_phase is None or hub_phase < 1
    if call_builder and not builder_done:
        return False, hub_phase, True
    if call_builder and sliced and incremental:
        hub_phase = 1
    return True, hub_phase, call_builder


def next_small(combos, index):
    for n in range(index + 1, len(combos)):
        if combos[n] == "small":
            return n
    return -1


@dataclass
class ComboCursor:
    combo: int = 0
    a: int = 9
    b: int = 8
    sites: object = field(default_factory=lambda: [1, 2])
    scanIndex: int = 7
    scanSites: list = field(default_factory=lambda: [1, 2])
    scanProbes: object = field(default_factory=lambda: {"left": 3})
    rankIndex: int = 2
    rankSites: list = field(default_factory=lambda: [2])
    hubPhase: int = 2
    hubSiteI: int = 3
    hubSiteJ: int = 4
    hubHubI: int = 5
    hubHubJ: int = 6
    air0310HubSnap: object = field(default_factory=lambda: {"sig": "old"})
    air0310HubSkip: object = field(default_factory=lambda: {"p": 1})
    bestPlan: object = None
    stationLimitedTowns: object = None
    perfOpsSites: int = 0
    perfOpsEval: int = 0
    perfProbesCount: int = 0
    perfCheapSkip: int = 0
    perfSitesFound: int = 0


def complete_combo(cursor, index, kind, kinds, *, big_winner, v93,
                   sliced=True, incremental=True, snapshots=True):
    """Model of the CD05 helper's return-index protocol."""
    if sliced:
        cursor.combo = index + 1
        cursor.a, cursor.b = 0, 1
        cursor.sites = None
        cursor.scanIndex, cursor.rankIndex = 0, 0
        cursor.scanSites, cursor.scanProbes, cursor.rankSites = [], None, []
        if incremental:
            cursor.hubPhase = 0
            cursor.hubSiteI, cursor.hubSiteJ = 0, 0
            cursor.hubHubI, cursor.hubHubJ = 0, 1
        if snapshots:
            cursor.air0310HubSnap = None
            cursor.air0310HubSkip = None
    if big_winner:
        if not v93:
            return -1
        if kind != "small":
            next_index = next_small(kinds, index)
            if next_index < 0:
                return -1
            if sliced:
                cursor.combo = next_index
            return next_index
    return index + 1


def legacy_complete_combo(cursor, index, kinds, *, big_winner, v93):
    """Independent transcription of the old inline block (loop-index protocol)."""
    cursor.combo = index + 1
    cursor.a = 0
    cursor.b = 1
    cursor.sites = None
    cursor.scanIndex = 0
    cursor.scanSites = []
    cursor.scanProbes = None
    cursor.rankIndex = 0
    cursor.rankSites = []
    cursor.hubPhase = 0
    cursor.hubSiteI = 0
    cursor.hubSiteJ = 0
    cursor.hubHubI = 0
    cursor.hubHubJ = 1
    cursor.air0310HubSnap = None
    cursor.air0310HubSkip = None
    if big_winner:
        if not v93:
            return None
        if kinds[index] != "small":
            n = index + 1
            while n < len(kinds) and kinds[n] != "small":
                n += 1
            if n == len(kinds):
                return None
            cursor.combo = n
            # Old loop assigns comboIndex = n - 1; then for-loop increments.
            return n - 1
    return index


def run_combos(kinds, big_winner_at, *, v93):
    """Compare the two historical loop-index conventions on one fixed world."""
    original = []
    cursor_original = ComboCursor()
    cursor_stage = ComboCursor()
    original_i = 0
    while original_i < len(kinds):
        original.append(original_i)
        big_winner = original_i >= big_winner_at
        last_index = legacy_complete_combo(cursor_original, original_i,
                                           kinds, big_winner=big_winner, v93=v93)
        if last_index is None:
            break
        original_i = last_index + 1

    staged = []
    index = 0
    while index < len(kinds):
        staged.append(index)
        following = complete_combo(cursor_stage, index, kinds[index], kinds,
                                   big_winner=index >= big_winner_at, v93=v93)
        if following < 0:
            break
        index = following  # staged code: comboIndex=following-1, loop ++
    return original, staged, cursor_original, cursor_stage


class CD03CD05HubStageTests(unittest.TestCase):
    def test_driver_orders_phases_and_never_closes_after_yield(self):
        steps = (
            "OpexAirPlansStepNewPairs(ctx", "if (!pairsOk)",
            "OpexAirPlansHubDiscoveryPhase(ctx", "OpexAirPlansHubToSitePhase(ctx",
            "if (!OpexAirPlansHubToSitePhase(ctx", "OpexAirPlansHubToHub(ctx",
            "if (!hubsOk)", "OpexAirPlansCompleteCombo(ctx",
            "OpexAirPlansFinalize(ctx",
        )
        # The CD04 invocation contains the condition, so assert distinct
        # ordering around the phase once, not two separate invocations.
        ordered = [DRIVER.index(s) for s in steps if s != "OpexAirPlansHubToSitePhase(ctx"]
        self.assertEqual(ordered, sorted(ordered))
        self.assertIn("OpexAirPlansNewPairs(ctx",
                      fn("OpexAirPlansStepNewPairs"))
        for name in ("OpexAirPlansHubDiscoveryPhase(",
                     "OpexAirPlansHubToSitePhase(",
                     "OpexAirPlansCompleteCombo("):
            self.assertEqual(DRIVER.count(name), 1)
        for yield_reason in ("sites_yield", "pairs_yield", "hub_site_yield",
                             "hub_hub_yield"):
            self.assertIn(f'"{yield_reason}"', DRIVER)
        self.assertLess(DRIVER.index("if (nextCombo < 0) break;"),
                        DRIVER.index("comboIndex = nextCombo - 1;"))
        self.assertIn("return ctx.bestPlan;", DRIVER)

    def test_cd03_snapshot_is_scoped_and_span_excludes_reuse(self):
        self.assertIn("local lightMark = null;", DISCOVERY)
        self.assertIn("local reuseHubs = false;", DISCOVERY)
        self.assertIn('if (ctx.sliced)', DISCOVERY)
        self.assertLess(DISCOVERY.index("OpexAir0310HubSnapshotPrepare("),
                        DISCOVERY.index("if (!reuseHubs) {"))
        if_block = DISCOVERY[DISCOVERY.index("if (!reuseHubs) {"):]
        events = (
            "ctx.air0310HubOrphan <- [];",
            'OpexSpanBegin("air.hub_discover")',
            "OpexAirPlansDiscoverHubs(ctx, combo, airport, plane)",
            "if (spDisc != null) OpexSpanEnd(spDisc)",
            "OpexAir0310HubSnapshotStore(ctx, comboIndex)",
        )
        indices = [if_block.index(event) for event in events]
        self.assertEqual(indices, sorted(indices))
        self.assertEqual(DISCOVERY.count("OpexAir0310HubSnapshotCount("), 1)
        self.assertEqual(DISCOVERY.count('OpexAirLightPhaseEnd(light, "hub_discover", lightMark)'), 1)
        self.assertLess(DISCOVERY.index('OpexC56TaskLog("STAGE_EXIT", "air_hub_discover"'),
                        DISCOVERY.index("OpexAirV95Post73Probe(ctx"))
        self.assertNotIn("resumeState.hubPhase <- 1", DISCOVERY)
        for signature in ("stable", "changed"):
            for sliced in (False, True):
                for feature in (False, True):
                    snap = {"signature": "stable"}
                    trace = discovery_step(snap, signature, sliced=sliced,
                                           feature=feature)
                    if signature == "stable" and sliced and feature:
                        self.assertEqual(trace, ["reuse", "post73_probe"])
                    else:
                        self.assertEqual(trace.count("discover_hubs"), 1)
                        self.assertEqual(trace.count("store_snapshot"), 1)
                        self.assertEqual(trace[-1], "post73_probe")

    def test_cd04_hub_phase_writes_only_on_success(self):
        self.assertIn('!("hubPhase" in ctx.resumeState)', HUB_SITE)
        self.assertLess(HUB_SITE.index("if (!OpexAirPlansHubToSite(ctx"),
                        HUB_SITE.index("ctx.resumeState.hubPhase <- 1;"))
        self.assertIn("if (!OpexAirPlansHubToSite(ctx, combo, airport, plane)) return false;", HUB_SITE)
        self.assertIn('if (ctx.sliced)', HUB_SITE)
        self.assertIn('OpexAirLightEnd(light, false, "hub_site_yield")', DRIVER)
        self.assertNotIn("Sleep(", HUB_SITE)
        for sliced in (False, True):
            for incremental in (False, True):
                for phase in (None, 0, 1, 2):
                    for completed in (False, True):
                        ok, new_phase, called = hub_site_step(
                            sliced=sliced, incremental=incremental,
                            hub_phase=phase, builder_done=completed)
                        should_call = not sliced or not incremental or phase is None or phase < 1
                        self.assertEqual(called, should_call)
                        self.assertEqual(ok, not should_call or completed)
                        self.assertEqual(new_phase, 1 if should_call and completed
                                         and sliced and incremental else phase)

    def test_cd05_resets_exact_fields_before_skip_and_isolated_scope(self):
        self.assertIn("local bestPlan = ctx.bestPlan;", CLOSE)
        self.assertIn("if (ctx.sliced)", CLOSE)
        for field in ("combo = comboIndex + 1", "a = 0", "b = 1",
                      "sites = null", "scanIndex = 0", "scanSites = []",
                      "scanProbes = null", "rankIndex = 0", "rankSites = []",
                      "hubPhase <- 0", "hubSiteI <- 0", "hubSiteJ <- 0",
                      "hubHubI <- 0", "hubHubJ <- 1",
                      "bestPlan = ctx.bestPlan", "stationLimitedTowns = ctx.stationLimitedTowns",
                      "perfOpsSites = ctx.perfOpsSites", "perfOpsEval = ctx.perfOpsEval",
                      "perfProbesCount = ctx.perfProbesCount",
                      "perfCheapSkip = ctx.perfCheapSkip", "perfSitesFound = ctx.perfSitesFound"):
            self.assertIn("ctx.resumeState." + field, CLOSE)
        for field in ("air0310HubSnap", "air0310HubSkip"):
            self.assertIn("delete ctx.resumeState." + field, CLOSE)
        self.assertLess(CLOSE.index("ctx.resumeState.perfSitesFound = ctx.perfSitesFound;"),
                        CLOSE.index("if (bestPlan != null && bestPlan.airport.allowBig)"))
        self.assertLess(CLOSE.index("if (!V93_AIRPORT_NO_POP_FLOOR) return -1;"),
                        CLOSE.index("OpexAirV93NextSmallCombo(ctx.combos, comboIndex)"))
        self.assertIn("if (ctx.sliced) ctx.resumeState.combo = nextSmall;", CLOSE)
        self.assertIn("return comboIndex + 1;", CLOSE)

    def test_v93_large_winner_small_follows_but_next_large_is_visited(self):
        kinds = ["large", "large", "small", "large", "small", "large"]
        for v93 in (False, True):
            for winner_at in (-1, 0, 1, 2, 3, 4, 99):
                previous, staged, pc, sc = run_combos(kinds, winner_at, v93=v93)
                self.assertEqual(staged, previous)
                self.assertEqual(sc, pc)
        visit, _, _, _ = run_combos(kinds, 0, v93=True)
        self.assertEqual(visit, [0, 2, 3, 4, 5])
        visit_off, _, _, _ = run_combos(kinds, 0, v93=False)
        self.assertEqual(visit_off, [0])
        for length in range(1, 9):
            kinds = ["small" if i % 3 == 1 else "large" for i in range(length)]
            for winner_at in range(-1, length + 2):
                for v93 in (False, True):
                    old, new, old_cursor, new_cursor = run_combos(
                        kinds, winner_at, v93=v93)
                    self.assertEqual(new, old)
                    self.assertEqual(new_cursor, old_cursor)


if __name__ == "__main__":
    unittest.main()
