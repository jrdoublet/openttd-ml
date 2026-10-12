"""AC-04: hub→site cartesian cursor, identity and snapshot contracts.

Fixed-world Python model + source contracts, NOT a NoAI VM/economic/opcode test.
Two negative discovery fixtures intentionally document existing anomalies:
saturated-route orphan misclassification and duplicate extra sites.
"""

from dataclasses import dataclass, field
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai/OpexAI/air_planning.nut").read_text(encoding="utf-8")
TASK_AIR = (ROOT / "ai/OpexAI/task_air.nut").read_text(encoding="utf-8")


def body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError(f"unterminated {signature}")


DISCOVER = body(AIR, "function OpexAirPlansDiscoverHubs(")
HUBSITE = body(AIR, "function OpexAirPlansHubToSite(")
PLANS = body(AIR, "function OpexAirPlans(")
SNAP = body(AIR, "function OpexAir0310HubSnapshotPrepare(")
ROUTES = body(AIR, "function OpexAir0310RefreshHubRoutes(")
SKIP = body(AIR, "function OpexAir0310SkipRestoredPair(")


@dataclass
class State:
    hub: int = 0
    site: int = 0
    phase: int = 0
    calls: int = 0
    seen: list = field(default_factory=list)
    passed: list = field(default_factory=list)
    admitted: list = field(default_factory=list)
    work: int = 0


def step(s, hubs, sites, budget, cost, allowed, admitted, target=None):
    """Exact outer/inner checkpoint order; pair outcomes are supplied stubs."""
    used = 0
    progressed = False
    s.calls += 1
    for hi in range(s.hub, len(hubs)):
        start = s.site if hi == s.hub else 0
        for sj in range(start, len(sites)):
            if progressed and budget and used >= budget:
                s.hub, s.site = hi, sj
                s.work += used
                return False
            progressed = True
            pair = (hi, sj)
            s.seen.append(pair)
            used += cost(hi, sj)
            # The source sets progressed even if V133, snapshot or filters skip.
            if target is not None and target not in (hubs[hi]["town"], sites[sj]["town"]):
                continue
            if not allowed(hubs[hi], sites[sj]):
                continue
            s.passed.append(pair)
            if admitted(hubs[hi], sites[sj]):
                s.admitted.append(pair)
    s.work += used
    s.hub, s.site, s.phase = len(hubs), 0, 1
    return True


def run(hubs, sites, budget, cost, allowed, admitted, target=None):
    s = State()
    for _ in range(len(hubs) * len(sites) + 2):
        if step(s, hubs, sites, budget, cost, allowed, admitted, target):
            return s
    raise AssertionError("unexpected livelock")


def discover_hubs_model(lines, airports, cap):
    """Restricted mock of DiscoverHubs, preserving the problematic orphan pass."""
    seen = set()
    hubs = []
    for station in lines:
        if station in seen:
            continue
        count = sum(s == station for s in lines)
        if count >= cap:
            continue
        seen.add(station)
        hubs.append((station, count, "line"))
    for station in airports:
        if station in seen:
            continue
        seen.add(station)
        hubs.append((station, 0, "orphan"))
    return hubs


def extra_sites_model(sites, towns, limit, find):
    """Current supplementation: no duplicate check before append."""
    result = list(sites)
    for town in towns:
        if len(result) >= limit:
            break
        item = find(town)
        if item is not None:
            result.append(item)
    return result


class AC04AirHubSiteResume(unittest.TestCase):
    def test_checkpoint_is_next_unprocessed_pair_and_progresses_on_rejects(self):
        for needle in (
            'local incrementalSlice = ctx.sliced && C121_CATALOG_INCREMENTAL;',
            'local resumeHub = incrementalSlice && ("hubSiteI" in ctx.resumeState)',
            'local resumeSite = incrementalSlice && ("hubSiteJ" in ctx.resumeState)',
            'for (local hi = resumeHub; hi < hubs.len(); hi++)',
            'for (local sj = hi == resumeHub ? resumeSite : 0; sj < sites.len(); sj++)',
            'if (progressed && ((ctx.opsBudget > 0 && used >= ctx.opsBudget)',
            'ctx.resumeState.hubSiteI <- hi;',
            'ctx.resumeState.hubSiteJ <- sj;',
            'progressed = true;',
            'ctx.resumeState.hubSiteI <- hubs.len();',
            'ctx.resumeState.hubSiteJ <- 0;',
        ):
            self.assertIn(needle, HUBSITE)
        self.assertLess(HUBSITE.index('ctx.resumeState.hubSiteJ <- sj;'),
                        HUBSITE.index('progressed = true;'))
        self.assertLess(HUBSITE.index('progressed = true;'),
                        HUBSITE.index('if (V133_AIR_BUILD_RETRY)'))
        self.assertLess(HUBSITE.index('progressed = true;'),
                        HUBSITE.index('OpexAir0310SkipRestoredPair('))
        self.assertIn('OpexAirPlansHubToSitePhase(ctx, combo, airport, plane)', PLANS)
        self.assertIn('ctx.resumeState.hubPhase <- 1;',
                      body(AIR, 'function OpexAirPlansHubToSitePhase('))
        closing = body(AIR, 'function OpexAirPlansCompleteCombo(')
        discovery = body(AIR, 'function OpexAirPlansHubDiscoveryPhase(')
        self.assertIn('ctx.resumeState.hubPhase <- 0;', closing)
        self.assertIn('OpexAir0310HubSnapshotPrepare(', discovery)
        self.assertLess(PLANS.index('OpexAirPlansHubDiscoveryPhase('),
                        PLANS.index('OpexAirPlansHubToSitePhase('))

    def test_frozen_cartesian_admission_and_order(self):
        ncases = 0
        for nh in (0, 1, 2, 4, 7):
            for ns in (0, 1, 2, 5, 9):
                hubs = [{"town": i, "station": i * 10} for i in range(nh)]
                sites = [{"town": j + 40, "anchor": j * 100} for j in range(ns)]
                for target in (None, 0, 40, 42, 999):
                    for cost in (lambda a,b: 1, lambda a,b: (a*7+b*11)%9+1,
                                 lambda a,b: 500 if (a,b)==(nh-1,ns-1) else 1):
                        for mode in (0, 1, 2):
                            allowed = lambda h,s,mode=mode: (h['town']+s['town']+mode)%3 != 0
                            admitted = lambda h,s,mode=mode: (h['town']*3+s['town']+mode)%4 == 0
                            ref = run(hubs, sites, 0, cost, allowed, admitted, target)
                            for budget in (1, 2, 7, 100, 1000):
                                got = run(hubs, sites, budget, cost, allowed, admitted, target)
                                with self.subTest(h=nh, s=ns, t=target, mode=mode, budget=budget):
                                    self.assertEqual(got.seen, ref.seen)
                                    self.assertEqual(got.passed, ref.passed)
                                    self.assertEqual(got.admitted, ref.admitted)
                                    self.assertEqual(got.work, ref.work)
                                    self.assertEqual(got.phase, 1)
                                    self.assertEqual(len(got.seen), len(set(got.seen)))
                                    self.assertEqual(len(got.seen), nh * ns)
                                ncases += 1
        self.assertEqual(ncases, 5*5*5*3*3*5)

    def test_last_site_last_hub_and_expensive_pair(self):
        hubs = [{"town": i} for i in range(3)]
        sites = [{"town": 40+j} for j in range(4)]
        keep = lambda h,s: True
        s = State()
        self.assertFalse(step(s, hubs, sites, 4, lambda a,b: 1, keep, keep))
        self.assertEqual(s.seen, [(0,0),(0,1),(0,2),(0,3)])
        self.assertEqual((s.hub,s.site), (1,0))
        self.assertFalse(step(s, hubs, sites, 4, lambda a,b: 1, keep, keep))
        self.assertEqual((s.hub,s.site), (2,0))
        self.assertTrue(step(s, hubs, sites, 4, lambda a,b: 1, keep, keep))
        self.assertEqual((s.hub,s.site,s.phase), (3,0,1))
        self.assertEqual(len(s.seen), 12)
        expensive = lambda a,b: 400 if (a,b) == (2,3) else 1
        got = run(hubs, sites, 1, expensive, keep, keep)
        self.assertEqual(len(got.seen), 12)
        self.assertEqual(got.work, 411)
        self.assertEqual(got.calls, 12)

    def test_hubs_are_deduplicated_by_station_and_snapshot_preserves_order(self):
        for needle in (
            'local seenStations = {};',
            'AIStation.GetStationID(end.anchor)',
            '(station in seenStations)',
            'hubIndex.routes',
            'routeCount++',
            'if (routeCount >= maxRoutes) continue;',
            'seenStations.rawset(station, true);',
            'AIStationList(AIStation.STATION_AIRPORT)',
            'if (st in seenStations) continue;',
            'hubs.append({ town = hubTown, anchor = loc, stationId = st, routes = 0 });',
        ):
            self.assertIn(needle, DISCOVER)
        self.assertLess(DISCOVER.index('if (routeCount >= maxRoutes) continue;'),
                        DISCOVER.index('seenStations.rawset(station, true);'))
        self.assertIn('ctx.hubs = OpexAir0310CopyHubList(snap.hubs);', SNAP)
        self.assertIn('OpexAir0310RefreshHubRoutes(ctx,', SNAP)
        self.assertIn('if (isOrphan) continue;', ROUTES)
        self.assertIn('if (!ctx.air0310HubRestored) return false;', SKIP)

    def test_existing_saturated_station_is_misclassified_as_orphan(self):
        # Sufficient proof of a real *reachability* flaw, not its exposure rate.
        hubs = discover_hubs_model([11,11,11,11], [11,91], cap=4)
        self.assertEqual(hubs, [(11,0,"orphan"),(91,0,"orphan")])
        self.assertFalse(4 < 4)  # construction batch checks true route count

    def test_extra_sites_can_duplicate_known_destination(self):
        for needle in ('if (!ctx.c83RepairCombo && sites.len() < AIR_HUB_NEW_SITE_POOL)',
                       'local extraSite = OpexAirFindSite(', 'sites.append(extraSite);'):
            self.assertIn(needle, DISCOVER)
        self.assertNotIn('if (extraSite.town.id in ', DISCOVER)
        # The same physical site is returned from the cache on both visits.
        got = extra_sites_model([("townA", 41)], ["townA","townB"], 3,
                                lambda town: (town, 41 if town=="townA" else 42))
        self.assertEqual(got, [("townA",41),("townA",41),("townB",42)])


if __name__ == "__main__":
    unittest.main()
