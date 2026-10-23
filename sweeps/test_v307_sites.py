"""V307 1.8 : contrats des sites de gare disperses par octant.

La transcription Python de la selection controle l'ordre et les quotas independamment
des journaux OpenTTD, sans lancer Docker.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import unittest

from sweeps.diag_v307_sites import autopsy, iso_state, parse_logs, summarise


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(file):
    return (AI / file).read_text(encoding="utf-8")


def octant(dx, dy):
    """Transcription de OpexV307Octant, axes E, SE, S, SW, W, NW, N, NE."""
    if dx == 0 and dy == 0:
        return -1
    ax, ay = abs(dx), abs(dy)
    if ax > 2 * ay:
        return 0 if dx > 0 else 4
    if ay > 2 * ax:
        return 2 if dy > 0 else 6
    if dx > 0:
        return 1 if dy > 0 else 7
    return 3 if dy > 0 else 5


def octant_round_robin(candidates, total=12, per_octant=3):
    """Candidates = (x, y, distance, admissible), sorted near-first per octant."""
    buckets = {i: [] for i in range(8)}
    for x, y, dist, admissible in candidates:
        if admissible:
            side = octant(x, y)
            if side >= 0:
                buckets[side].append((dist, x, y))
    for side in buckets:
        buckets[side].sort()
    selected = []
    depth = 0
    while len(selected) < total and depth < per_octant:
        any_remaining = False
        for side in range(8):
            if depth < len(buckets[side]):
                any_remaining = True
                selected.append((side, buckets[side][depth]))
                if len(selected) == total:
                    break
        if not any_remaining:
            break
        depth += 1
    return selected


def hybrid_octants(spiral, native, maximum=12):
    """Python contract model of v307_sites=2; inputs are unique-anchor (x,y) plans."""
    plans = list(spiral)
    original = set(octant(*p) for p in spiral)
    seen = set(plans)
    for site in native:
        target = octant(*site)
        if site in seen or target in original or target < 0:
            continue
        current = Counter(octant(*p) for p in plans)
        if current[target]:
            continue
        if len(plans) < maximum:
            plans.append(site)
            seen.add(site)
            continue
        candidates = [(n, -side, side) for side, n in current.items() if n > 1]
        if not candidates:
            continue
        most = max(candidates)[2]
        index = max(i for i, p in enumerate(plans) if octant(*p) == most)
        seen.remove(plans[index])
        plans[index] = site
        seen.add(site)
    return plans


def ring_tiles(r):
    """Ordre de la spirale historique : dx croissant, puis dy croissant, perimetre seul."""
    return [(dx, dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)
            if abs(dx) == r or abs(dy) == r]


SEGMENTS = [(7, 0, 1), (3, 2, 1), (5, 4, 3), (5, 6, 7)]


def edge_tiles(r):
    """Transcription des segments de OpexV307SpiralContinue : (octant annonce, dx, dy)."""
    out = []
    half = (r - 1) // 2
    for e in range(4):
        corner = r if e in (0, 2) else r - 1
        for seg in range(3):
            t0 = -corner if seg == 0 else (-half if seg == 1 else half + 1)
            t1 = -half - 1 if seg == 0 else (half if seg == 1 else corner)
            for t in range(t0, t1 + 1):
                dx = r if e == 0 else (-r if e == 2 else t)
                dy = r if e == 1 else (-r if e == 3 else t)
                out.append((SEGMENTS[e][seg], dx, dy))
    return out


def spiral(admissible, radius, limit):
    """Plans (un par orientation admise) et anneau d'arret, comme la copie V307S."""
    plans, last = [], radius + 1
    for r in range(radius + 1):
        if len(plans) >= limit:
            break
        last = r
        for tile in ring_tiles(r):
            for orientation in admissible.get(tile, ()):
                plans.append((tile, orientation))
                if len(plans) >= limit:
                    break
            if len(plans) >= limit:
                break
    stop = last if len(plans) >= limit else radius + 1
    return plans, stop


def continue_spiral(admissible, start, max_ring, wanted):
    found = {}
    for r in range(max(start, 1), max_ring + 1):
        for _, dx, dy in edge_tiles(r):
            side = octant(dx, dy)
            if side in wanted and side not in found and admissible.get((dx, dy)):
                found[side] = (dx, dy)
        if len(found) == len(wanted):
            break
    return found


class TestV307Sites(unittest.TestCase):
    def test_octant_axes_and_diagonals(self):
        self.assertEqual([octant(*xy) for xy in
                          [(4, 0), (3, 3), (0, 4), (-3, 3), (-4, 0),
                           (-3, -3), (0, -4), (3, -3)]], list(range(8)))
        self.assertEqual(octant(0, 0), -1)

    def test_round_robin_prefers_spread_and_nearest(self):
        # Two opposite octants supply many closer plans; they cannot evict other octants.
        points = [(3 + i, 0, i + 1, True) for i in range(10)]
        points += [(0, 3 + i, i + 2, True) for i in range(10)]
        points += [(-3 - i, 0, i + 3, True) for i in range(10)]
        points += [(0, -3 - i, i + 4, True) for i in range(10)]
        selected = octant_round_robin(points)
        counts = Counter(side for side, _ in selected)
        self.assertEqual(len(selected), 12)
        self.assertTrue(all(n <= 3 for n in counts.values()))
        self.assertEqual(set(counts), {0, 2, 4, 6})
        for side, count in counts.items():
            depths = [value[0] for s, value in selected if s == side]
            self.assertEqual(depths, sorted(depths))

    def test_option_off_on_all_difficulties(self):
        info = source("info.nut")
        setting = re.search(r'name = "v307_sites",(.*?)\}\);', info, re.S)
        self.assertIsNotNone(setting)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf'{level}_value\s*=\s*0\b')
        self.assertRegex(setting.group(1), r'max_value\s*=\s*3\b')
        self.assertEqual(source("settings.nut").count('GetSetting("v307_sites")'), 1)
        self.assertIn("V307_SITES <- 0;", source("globals_pre.nut"))

    def test_two_adds_uncovered_octants_without_evicting_spiral_count(self):
        baseline = [(x, 0) for x in range(1, 13)]
        alternatives = [(0, 6), (-6, 0), (0, -6), (7, 7), (8, 0)]
        combined = hybrid_octants(baseline, alternatives)
        self.assertEqual(len(combined), len(baseline))
        self.assertEqual(len(set(combined)), len(combined))
        self.assertLessEqual(len(combined), 12)
        self.assertEqual({octant(*p) for p in combined}, {0, 1, 2, 4, 6})
        self.assertEqual(hybrid_octants(baseline, [], 12), baseline)

    def test_two_never_drops_spiral_when_no_native_candidate_qualifies(self):
        baseline = [(2, 0), (3, 0), (0, 4)]
        self.assertEqual(hybrid_octants(baseline, [(7, 0), (0, 5)]), baseline)
        self.assertEqual(len(hybrid_octants(baseline, [(-6, 0)])), 4)

    def test_two_code_uses_historical_spiral_and_silent_native_helper(self):
        rail = source("builder_rail.nut")
        self.assertIn("function OpexV307HybridStationPlans", rail)
        self.assertIn("OpexV307SpiralPlanCandidates(center, radius, length, maxPlans,", rail)
        self.assertIn("rankPct = 0)", rail)
        self.assertIn("if (V307_SITES == 2)", rail)
        self.assertIn("if (V307_SITES > 0)", rail)
        self.assertIn('" native_added=" + added', rail)

    def test_native_industry_tile_sources_and_octant_caps(self):
        rail = source("builder_rail.nut")
        self.assertIn("AITileList_IndustryAccepting", rail)
        self.assertIn("AITileList_IndustryProducing", rail)
        self.assertIn("OpexV307SiteOctant", rail)
        self.assertIn("V307S_PLANS", rail)
        self.assertIn("OpexOpsClock()", rail)
        self.assertIn("OpexStationPlans", rail)
        self.assertNotIn(".find(", rail)

    def test_reader_empty_probe_preserves_unknown_ops(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "reference_seed42_r0.log"
            file.write_text("[0] [I] OPEX 1971-1-2 RAIL_ATTEMPT kind=freight reason=ABND\n",
                            encoding="utf-8")
            report = summarise(parse_logs([file]))
        self.assertEqual(report["reference"]["reasons"]["ABND"], 1)
        self.assertEqual(report["reference"]["sites"], 0)
        self.assertIsNone(report["reference"]["real_profit"])

    def test_autopsy_counts_year_type_side_without_inventing_stage(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "v307s_seed42_r0.log"
            file.write_text("[0] [I] OPEX 1973-1-2 V307S_PLANS mode=freight side=B "
                            "center=17 oct_n=0 plans=0 ops=55 v=1\n"
                            "[0] [I] OPEX 1973-2-2 V307S_PLANS mode=pax side=A "
                            "center=20 oct_n=1 plans=2 ops=75 v=1\n", encoding="utf-8")
            detail = autopsy(parse_logs([file]))
        self.assertIn("| v307s | 1973 | B | freight | 1 | 1 | 100.0% |", detail)
        self.assertIn("étape inconnue (anciens logs sans compteurs)", detail)

    def test_three_edges_cover_each_ring_tile_once_with_declared_octants(self):
        for r in range(1, 31):
            tiles = edge_tiles(r)
            self.assertEqual(sorted((dx, dy) for _, dx, dy in tiles), sorted(ring_tiles(r)))
            for announced, dx, dy in tiles:
                self.assertEqual(octant(dx, dy), announced)

    def test_three_skipping_inner_rings_loses_no_site(self):
        """Exactitude : sous la limite atteinte a l'anneau s, tout site admissible d'un
        octant absent est a un anneau >= s ; repartir de s retrouve le premier."""
        import random
        rng = random.Random(307)
        for _ in range(400):
            radius = rng.randint(3, 12)
            density = rng.choice((0.05, 0.15, 0.4))
            admissible = {}
            for r in range(radius + 1):
                for tile in ring_tiles(r):
                    if rng.random() < density:
                        admissible[tile] = tuple(range(rng.randint(1, 4)))
            plans, stop = spiral(admissible, radius, 12)
            covered = {octant(*tile) for tile, _ in plans}
            wanted = set(range(8)) - covered
            fast = continue_spiral(admissible, stop, radius, wanted)
            full = continue_spiral(admissible, 1, radius, wanted)
            self.assertEqual(set(fast), set(full))
            for side, tile in fast.items():
                self.assertEqual(max(abs(tile[0]), abs(tile[1])),
                                 max(abs(full[side][0]), abs(full[side][1])))
            if len(plans) < 12:
                self.assertEqual(stop, radius + 1)
                self.assertEqual(fast, {})

    def test_three_reader_reports_iso_state_ratio(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "v307s3_seed42_r0.log"
            file.write_text(
                "[0] [I] OPEX 1972-1-2 V307S_PLANS mode=freight side=B center=17 oct_n=2 "
                "plans=12 ops=1300 v=3 spiral=12 native_added=1 spiral_ops=1000 "
                "extra_ops=300 stop_ring=3 max_ring=9 wanted=6\n"
                "[0] [I] OPEX 1972-2-2 V307S_PLANS mode=freight side=A center=18 oct_n=3 "
                "plans=5 ops=2000 v=3 spiral=5 native_added=0 spiral_ops=2000 "
                "extra_ops=0 stop_ring=31 max_ring=-1 wanted=5\n", encoding="utf-8")
            table = iso_state(parse_logs([file]))
        self.assertIn("| v307s3 | 2 | 1 | 1 | 1 | 1.150 | 1.300 | 1.300 |", table)

    def test_three_code_contracts(self):
        rail = source("builder_rail.nut")
        self.assertIn("const V307S3_BUDGET_PCT = 60;", rail)
        self.assertIn("function OpexV307TargetedStationPlans", rail)
        self.assertIn("function OpexV307SpiralContinue", rail)
        dispatch = rail[rail.index("function OpexStationPlans("):]
        self.assertLess(dispatch.index("if (V307_SITES == 3)"), dispatch.index("if (V307_SITES == 2)"))
        self.assertLess(dispatch.index("if (V307_SITES == 2)"), dispatch.index("if (V307_SITES > 0)"))
        self.assertIn("requireDouble, rankPct,\n                                       scan = null)", rail)
        self.assertIn("if (scan != null) scan.stopRing <-", rail)
        self.assertIn("if (nWanted > 0 && scan.stopRing <= radius)", rail)
        self.assertIn("tiles.Valuate(AIMap.DistanceMax, center);", rail)
        for field in ('" v=3 spiral="', '" spiral_ops="', '" extra_ops="', '" stop_ring="',
                      '" max_ring="', '" wanted="'):
            self.assertIn(field, rail)
        body = rail[rail.index("function OpexV307SpiralContinue"):
                    rail.index("function OpexV307TargetedStationPlans")]
        self.assertIn("local edges = [[7, 0, 1], [3, 2, 1], [5, 4, 3], [5, 6, 7]];", body)
        self.assertIn("if (scan != null && (!AITile.IsBuildable(tile)", rail)
        self.assertIn("if (OpexOpsClock() - mark + worstTry > budget) { out.budgetStop = 1; return found; }", body)
        self.assertIn("if (aoct < 0 || !open[aoct]) continue;", body)
        self.assertIn("!open[(oct + 1) % 8] && !open[(oct + 7) % 8]", body)
        self.assertIn("if (spiralOps <= 0) maxRing = -1;", rail)
        self.assertIn("V307S3_REACH[key] <- [indType, coverage, reach];", rail)
        self.assertNotIn("function(", body)
        settings = source("settings.nut")
        self.assertIn("v307Sites == 3", settings)


if __name__ == "__main__":
    unittest.main()
