"""AC-02 : contrats de curseurs et modèle de reprise des sites AIR.

La fixture simule les décisions des API NoAI sur un état figé ; elle n'exécute
pas le Squirrel et n'établit donc aucune neutralité économique ou opcode.
Les assertions sur le corps Squirrel lient le modèle aux checkpoints réels.
"""

import unittest
from dataclasses import dataclass, field
from pathlib import Path


AIR = (Path(__file__).resolve().parents[1] / "ai/OpexAI/air_planning.nut").read_text(
    encoding="utf-8"
)


def function_body(signature):
    start = AIR.index(signature)
    brace = AIR.index("{", start)
    depth = 0
    for i in range(brace, len(AIR)):
        if AIR[i] == "{":
            depth += 1
        elif AIR[i] == "}":
            depth -= 1
            if depth == 0:
                return AIR[start:i + 1]
    raise AssertionError(f"Function not closed: {signature}")


PREPARE = function_body("function OpexAirPlansPrepare(")
FIND = function_body("function OpexAirPlansFindSites(")
PIPELINE = function_body("function OpexAirPlans(")


@dataclass
class SiteState:
    scan_index: int = 0
    scan_sites: list = field(default_factory=list)
    rank_index: int = 0
    rank_sites: list = field(default_factory=list)
    sites: object = None
    probes: int = 0
    scan_seen: list = field(default_factory=list)
    ranked_seen: list = field(default_factory=list)


def sorted_towns(towns, target=None, dirty_order=False):
    """L'entrée de FindSites après Prepare : le classement est figé à la tranche 1."""
    ranked = sorted(towns, key=lambda t: (-t["pop"], t["id"]))
    if target is not None:
        return [t for t in ranked if t["id"] == target] + [t for t in ranked if t["id"] != target]
    if dirty_order:
        return sorted(ranked, key=lambda t: (not t.get("dirty", False), -t["pop"], t["id"]))
    return ranked


def step(state, towns, limit, budget, *, target=None, c83_fixes=False, kind="large",
         v93=False, min_pop=100, max_probes=99):
    """Modèle des deux boucles de FindSites (1 coût-unité par itération).

    Les callbacks déterministes ``found``, ``valid``, ``served`` et ``slot``
    représentent un monde figé et le résultat de OpexAirFindSite/StillBuildable.
    """
    if state.sites is not None:
        return True
    used = 0
    scan_end = limit
    if c83_fixes and target is not None:
        scan_end = state.scan_index
        for i in range(state.scan_index, limit):
            if towns[i]["id"] == target:
                scan_end = i + 1
                break
    for i in range(state.scan_index, scan_end):
        town = towns[i]
        state.scan_seen.append(town["id"])
        eligible = not town.get("retry", False) and not town.get("station_limit", False)
        eligible = eligible and (not town.get("served", False) or town.get("slot", False))
        eligible = eligible and (v93 and town["pop"] >= min_pop or
                                 not v93 and (kind != "large" or town["pop"] >= 600))
        if eligible and state.probes < max_probes:
            state.probes += 1
            if town.get("found", False):
                state.scan_sites.append(town["id"])
        state.scan_index = i + 1
        used += 1
        if used >= budget:
            return False
    for rank_index in range(state.rank_index, len(state.scan_sites)):
        town_id = state.scan_sites[rank_index]
        state.ranked_seen.append(town_id)
        town = next(t for t in towns if t["id"] == town_id)
        if town.get("valid", True):
            state.rank_sites.append(town_id)
        state.rank_index = rank_index + 1
        used += 1
        if used >= budget:
            return False
    state.sites = list(state.rank_sites)
    state.scan_index = 0
    state.scan_sites.clear()
    state.rank_index = 0
    state.rank_sites.clear()
    return True


def run(towns, *, budget, target=None, c83_fixes=False, kind="large", v93=False,
        max_probes=99, dirty_order=False):
    ordered = sorted_towns(towns, target=target, dirty_order=dirty_order)
    state = SiteState()
    for calls in range(1, 500):
        if step(state, ordered, len(ordered), budget, target=target,
                c83_fixes=c83_fixes, kind=kind, v93=v93, max_probes=max_probes):
            return state, calls, ordered
    raise AssertionError("FindSites model did not finish")


class AC02AirSiteResumeTests(unittest.TestCase):
    def test_source_checkpoints_and_order_are_tied_to_model(self):
        for term in (
            'resumeState.scanIndex <- 0;', 'resumeState.scanSites <- [];',
            'resumeState.rankIndex <- 0;', 'resumeState.rankSites <- [];',
            'sliced && resumeState.towns != null',
            'sliced && resumeState.combos != null',
            'if (sliced) resumeState.towns = towns;',
            'if (sliced) resumeState.townLimit = limit;',
        ):
            self.assertIn(term, PREPARE)
        for term in (
            'local scanStart = sliced ? resumeState.scanIndex : 0;',
            'for (local i = scanStart; i < scanEnd; i++)',
            'resumeState.scanIndex = i + 1;',
            'resumeState.scanSites = scanSites;',
            'resumeState.scanProbes = probes;',
            'local rankStart = sliced ? resumeState.rankIndex : 0;',
            'for (local rankIndex = rankStart; rankIndex < scanSites.len(); rankIndex++)',
            'resumeState.rankIndex = rankIndex + 1;',
            'resumeState.rankSites = rankableSites;',
            'resumeState.sites = sites;',
            'resumeState.scanIndex = 0;',
            'resumeState.rankIndex = 0;',
            'if (!sliced || !resumingCombo)',
        ):
            self.assertIn(term, FIND)
        self.assertLess(FIND.index('resumeState.scanIndex = i + 1;'),
                        FIND.index('if ((opsBudget > 0 && scanSliceOps >= opsBudget)'))
        self.assertLess(FIND.index('resumeState.rankIndex = rankIndex + 1;'),
                        FIND.index('if ((opsBudget > 0 && rankSliceOps >= opsBudget)'))
        self.assertLess(FIND.index('resumeState.sites = sites;'),
                        FIND.index('resumeState.scanSites = [];'))
        self.assertIn('ctx.resumeState.scanIndex = 0;', PIPELINE)
        self.assertIn('ctx.resumeState.rankIndex = 0;', PIPELINE)
        self.assertIn('ctx.resumeState.sites = null;', PIPELINE)

    def test_site_probe_state_is_shared_and_never_reinitialised_on_resume(self):
        self.assertIn('sliced && resumeState.scanProbes != null', FIND)
        self.assertIn('resumeState.scanProbes = probes;', FIND)
        self.assertIn('resumeState.scanProbes = null;', FIND)
        self.assertIn('local foundBefore = scanSites.len();', FIND)
        self.assertIn('perfSitesFound += scanSites.len() - foundBefore;', FIND)
        self.assertIn('OpexAirSiteStillBuildable(site, airport, plane, false, stationLimitedTowns)', FIND)
        self.assertIn('scanEnd = c83Scan + 1;', FIND)
        self.assertIn('if (C83_FIXES && targetTownId >= 0)', FIND)

    def test_frozen_normal_small_large_v93_dirty_and_c83_targeted(self):
        towns = [
            {"id": 8, "pop": 2400, "found": True, "dirty": False},
            {"id": 3, "pop": 1200, "found": False, "dirty": True},
            {"id": 12, "pop": 590, "found": True, "dirty": True},
            {"id": 5, "pop": 610, "found": True, "valid": False},
            {"id": 7, "pop": 2000, "served": True, "found": True},
            {"id": 6, "pop": 1700, "served": True, "slot": True, "found": True},
            {"id": 14, "pop": 800, "retry": True, "found": True},
            {"id": 1, "pop": 750, "station_limit": True, "found": True},
        ]
        for kind in ("large", "small"):
            for v93 in (False, True):
                for dirty in (False, True):
                    for max_probes in (0, 1, 3, 99):
                        for target, c83 in ((None, False), (12, True), (999, True)):
                            with self.subTest(kind=kind, v93=v93, dirty=dirty, target=target,
                                              probes=max_probes):
                                expected, _, _ = run(towns, budget=999, kind=kind, v93=v93,
                                                     dirty_order=dirty, target=target,
                                                     c83_fixes=c83, max_probes=max_probes)
                                for budget in (1, 2, 3, 5, 9):
                                    actual, slices, _ = run(towns, budget=budget, kind=kind,
                                                           v93=v93, dirty_order=dirty,
                                                           target=target, c83_fixes=c83,
                                                           max_probes=max_probes)
                                    self.assertEqual(actual.sites, expected.sites)
                                    self.assertEqual(actual.scan_seen, expected.scan_seen)
                                    self.assertEqual(actual.ranked_seen, expected.ranked_seen)
                                    self.assertEqual(actual.probes, expected.probes)
                                    self.assertEqual(actual.scan_index, 0)
                                    self.assertEqual(actual.rank_index, 0)
                                    self.assertEqual(actual.scan_sites, [])
                                    self.assertEqual(actual.rank_sites, [])
                                    self.assertEqual(len(actual.scan_seen),
                                                     len(set(actual.scan_seen)))
                                    self.assertEqual(len(actual.ranked_seen),
                                                     len(set(actual.ranked_seen)))
                                    if budget == 1 and expected.scan_seen:
                                        self.assertGreater(slices, 1)

    def test_last_scan_and_last_rank_also_resume_without_duplicate(self):
        towns = [{"id": n, "pop": 1200 + n, "found": True} for n in range(4)]
        ordered = sorted_towns(towns)
        state = SiteState()
        self.assertFalse(step(state, ordered, 4, 4))  # coupe APRES la dernière ville
        self.assertEqual(state.scan_index, 4)
        self.assertEqual(state.scan_sites, [3, 2, 1, 0])
        self.assertEqual(state.rank_index, 0)
        self.assertFalse(step(state, ordered, 4, 4))  # coupe APRES la dernière revalidation
        self.assertEqual(state.rank_index, 4)
        self.assertEqual(state.rank_sites, [3, 2, 1, 0])
        self.assertTrue(step(state, ordered, 4, 4))  # consolide sans re-sonder
        self.assertEqual(state.sites, [3, 2, 1, 0])
        self.assertEqual(state.scan_seen, [3, 2, 1, 0])
        self.assertEqual(state.ranked_seen, [3, 2, 1, 0])


if __name__ == "__main__":
    unittest.main()
