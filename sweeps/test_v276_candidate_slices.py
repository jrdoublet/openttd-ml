"""V276: contrats du chemin optionnel et modeles des curseurs.

Ces tests ne compilent pas Squirrel et ne certifient pas le cout d'un atome
economique/publication. Ce cout demande un decoupage supplementaire ou le moteur.
"""
from itertools import combinations, product
from math import sqrt
from pathlib import Path
import random
import re
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def freight_order(mode, incomes, productions, pax):
    """Oracle du classement annuel des cargos (hors voyageurs)."""
    scores = {cargo: income * (sum(productions[cargo]) if mode == 2 else 1)
              for cargo, income in incomes.items()
              if cargo != pax and productions[cargo]}
    return sorted(scores, key=scores.get, reverse=True)


class Grid:
    """Modele de OpexSpatialGrid, indices conserves et voisinage 3x3."""

    def __init__(self, destinations, maximum):
        self.size = max(1, maximum)
        self.cells = {}
        for i, (x, y, *_) in enumerate(destinations):
            self.cells.setdefault((x // self.size, y // self.size), []).append(i)

    def neighbors(self, source, minimum=-1):
        x, y = source[:2]
        cx, cy = x // self.size, y // self.size
        return [i for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                for i in self.cells.get((cx + dx, cy + dy), []) if i > minimum]


def freight_pairs(sources, sinks, low, high, target_source=-1, target_sink=-1, targeted=False):
    grid = Grid(sinks, high)
    for a, src in enumerate(sources):
        neighbors = (grid.neighbors(src) if not targeted or a == target_source
                     else ([target_sink] if target_sink >= 0 else []))
        for b in neighbors:
            dst = sinks[b]
            distance = abs(src[0] - dst[0]) + abs(src[1] - dst[1])
            if low <= distance <= high and src[:2] != dst[:2]:
                yield a, b


class Cursor:
    """Enumeration geometrique, puis file native de priorite (modele)."""

    def __init__(self, towns, target=None, low=0, high=2048, cap=None, every=50):
        self.towns = towns
        self.target = target
        self.a, self.b = 0, 0
        self.grid = Grid(towns, high)
        self.neighbors = None
        self.low, self.high, self.cap, self.every = low, high, cap, every
        self.publications = []
        self.last_published = -1
        self.pairs = {}
        self.output = []
        self.phase = "enumerate"

    def step(self):
        n = len(self.towns)
        outer = n if self.target is None else 1
        if self.phase == "enumerate":
            if self.a >= outer:
                self.phase = "evaluate"
                return
            a = self.a if self.target is None else self.target
            if self.neighbors is None:
                self.neighbors = self.grid.neighbors(self.towns[a], a if self.target is None else -1)
            if self.b >= len(self.neighbors):
                self.a += 1
                self.b = 0
                self.neighbors = None
                return
            b = self.neighbors[self.b]
            self.b += 1
            if a == b:
                return
            x, y = self.towns[a], self.towns[b]
            d = abs(x[0] - y[0]) + abs(x[1] - y[1])
            if self.low <= d <= self.high:
                self.pairs[a * n + b] = int(x[2] * y[2] * sqrt(d))
        elif self.phase == "publish":
            if self.last_published != len(self.output):
                self.publications.append(tuple(self.output))
                self.last_published = len(self.output)
            self.phase = ("evaluate" if self.pairs and (self.cap is None or len(self.output) < self.cap)
                          else "done")
        elif self.pairs and (self.cap is None or len(self.output) < self.cap):
            key = max(self.pairs, key=lambda k: (self.pairs[k], -k))
            score = self.pairs.pop(key)
            self.output.append((key // n, key % n, score))
            if len(self.output) % self.every == 0:
                self.phase = "publish"
        else:
            self.phase = "publish"

    def slice(self, budget):
        used = 0
        while self.phase != "done" and used < budget:
            self.step()
            used += 1
        return used


class Models(unittest.TestCase):
    def test_freight_order_unit_income_or_total_production(self):
        incomes = {0: 10000, 1: 100, 2: 80, 3: 200, 4: 500}
        # Deux sources du cargo 2 : leur somme inverse l'ordre 1/2.
        productions = {0: [10000], 1: [10], 2: [7, 8], 3: [0], 4: []}
        self.assertEqual(freight_order(1, incomes, productions, pax=0), [3, 1, 2])
        self.assertEqual(freight_order(2, incomes, productions, pax=0), [2, 1, 3])

    def setUp(self):
        rng = random.Random(276)
        self.towns = [(rng.randrange(1024), rng.randrange(1024), rng.randrange(50, 5000))
                      for _ in range(35)]

    def test_exact_cursor_at_every_possible_small_slice(self):
        expected = set(combinations(range(len(self.towns)), 2))
        oracle = None
        for budget in range(1, 24):
            cursor = Cursor(self.towns)
            turns = 0
            while cursor.phase != "done":
                self.assertLessEqual(cursor.slice(budget), budget)
                turns += 1
                self.assertLess(turns, 3000)
            self.assertEqual({(a, b) for a, b, _ in cursor.output}, expected)
            self.assertEqual(len(cursor.output), len(expected))
            if oracle is None:
                oracle = cursor.output
            self.assertEqual(cursor.output, oracle)

    def test_score_descending_against_independent_oracle(self):
        cursor = Cursor(self.towns)
        while cursor.phase != "done":
            cursor.slice(7)
        scores = [score for _, _, score in cursor.output]
        expected = []
        for a, b in combinations(self.towns, 2):
            expected.append(int(a[2] * b[2] * sqrt(abs(a[0] - b[0]) + abs(a[1] - b[1]))))
        self.assertEqual(scores, sorted(expected, reverse=True))

    def test_target_first_middle_last_exact_linear_set(self):
        for target in (0, 17, 34):
            cursor = Cursor(self.towns, target)
            steps = 0
            while cursor.phase != "done":
                steps += cursor.slice(1)
            expected = {(target, i) for i in range(35) if i != target}
            self.assertEqual({(a, b) for a, b, _ in cursor.output}, expected)
            self.assertLess(steps, 4 * len(self.towns) + 6)

    def test_empty_and_singleton_finish(self):
        for towns in ([], [(0, 0, 100)]):
            cursor = Cursor(towns)
            for _ in range(8):
                cursor.slice(1)
            self.assertEqual(cursor.phase, "done")
            self.assertEqual(cursor.output, [])

    def test_distance_bands_partition_including_equal_bounds(self):
        for overlap in (7, 80, 160):
            short = {d for d in range(2049) if 7 <= d < overlap}
            shared = {d for d in range(2049) if overlap <= d <= 160}
            self.assertFalse(short & shared)
            self.assertEqual(short | shared, set(range(7, 161)))

    def test_target_freight_set_without_cartesian_filter(self):
        sources, sinks = list(range(80)), list(range(40, 120))
        for target in (0, 50, 119, 999):
            actual = set()
            examined = 0
            for source in sources:
                row = sinks if source == target else ([target] if target in sinks else [])
                for sink in row:
                    examined += 1
                    if source != sink:
                        actual.add((source, sink))
            expected = {(a, b) for a, b in product(sources, sinks)
                        if a != b and target in (a, b)}
            self.assertEqual(actual, expected)
            self.assertLessEqual(examined, len(sources) + len(sinks))

    def test_incremental_publication_preserves_unfinished_units(self):
        batches = {"freight": ["old_f"], "pax": ["old_p"]}
        batches["freight"] = ["new_f"]
        self.assertEqual([c for batch in batches.values() for c in batch], ["new_f", "old_p"])
        batches["pax"] = ["new_p"]
        self.assertEqual([c for batch in batches.values() for c in batch], ["new_f", "new_p"])

    def test_ack_never_consumes_late_revisions(self):
        consumed = {"towns": 3, "lines": 4}
        snapshot = {"towns": 5, "lines": 4}
        current = {"towns": 6, "lines": 8}
        for layer in consumed:
            consumed[layer] = max(consumed[layer], snapshot[layer])
        self.assertEqual(consumed, snapshot)
        self.assertTrue(all(consumed[k] < current[k] for k in current))

    def test_worker_uses_remainder_every_tick_without_moving_queue(self):
        queue = ["catalog", "projects", "air_scan"]
        visits, worker_ticks = [], []
        costs = [1000, 9800, 5000, 6900, 0, 8500] * 12
        for tick, cost in enumerate(costs):
            visits.append(queue[tick % len(queue)])
            remaining = 10000 - cost - 2000
            if remaining > 1000:
                worker_ticks.append((tick, min(6000, remaining)))
        self.assertEqual(visits, queue * 24)
        self.assertEqual(len(worker_ticks), 48)
        self.assertTrue(all(budget <= 10000 - costs[tick] - 2000 for tick, budget in worker_ticks))

    def test_grid_equals_complete_filtered_pax_including_boundaries_and_targets(self):
        towns = self.towns + [(0, 0, 100), (80, 0, 100), (79, 1, 100), (81, 0, 100)]
        for low, high in ((0, 0), (7, 79), (80, 160), (0, 2048)):
            for target in (None, 0, 36):
                cursor = Cursor(towns, target, low, high)
                while cursor.phase != "done":
                    cursor.slice(3)
                candidates = (combinations(range(len(towns)), 2) if target is None
                              else ((target, b) for b in range(len(towns)) if b != target))
                expected = {(a, b) for a, b in candidates
                            if low <= abs(towns[a][0] - towns[b][0]) + abs(towns[a][1] - towns[b][1]) <= high}
                self.assertEqual({(a, b) for a, b, _ in cursor.output}, expected)

    def test_grid_freight_oriented_sinks_and_targeted_rows_columns(self):
        # Puits industriels et urbains partagent le meme index plat.
        sources = [(0, 0), (80, 0), (400, 300), (1023, 1023)]
        sinks = [(0, 0), (79, 1), (80, 0), (81, 0), (401, 301), (1023, 943)]
        for low, high in ((0, 0), (1, 80), (80, 160), (0, 2048)):
            for targeted, a_target, b_target in ((False, -1, -1), (True, 1, 2),
                                                  (True, -1, 5), (True, 2, -1), (True, -1, -1)):
                expected = {(a, b) for a, b in product(range(len(sources)), range(len(sinks)))
                            if (not targeted or a == a_target or b == b_target)
                            and sources[a] != sinks[b]
                            and low <= abs(sources[a][0] - sinks[b][0]) + abs(sources[a][1] - sinks[b][1]) <= high}
                self.assertEqual(set(freight_pairs(sources, sinks, low, high, a_target, b_target, targeted)), expected)

    def test_publication_frequency_cap_and_resume_at_all_boundaries(self):
        for size, expected in ((0, [0]), (1, [0]), (10, [45]), (11, [50, 55]), (40, list(range(50, 501, 50)))):
            towns = [(i, i * 2, 100 + i) for i in range(size)]
            oracle = None
            for budget in (1, 2, 7, 49, 50, 51, 5000):
                cursor = Cursor(towns, cap=500)
                while cursor.phase != "done":
                    cursor.slice(budget)
                self.assertEqual([len(p) for p in cursor.publications], expected)
                self.assertEqual(len(cursor.output), min(500, size * (size - 1) // 2))
                self.assertEqual(len({(a, b) for a, b, _ in cursor.output}), len(cursor.output))
                if oracle is None:
                    oracle = cursor.output
                self.assertEqual(cursor.output, oracle)

    def test_next_scan_restarts_at_new_score_head_and_next_unit_is_not_starved(self):
        towns = [(i, i * 2, 100 + i) for i in range(40)]
        first = Cursor(towns, cap=500)
        while first.phase != "done":
            first.slice(7)
        towns[0] = (0, 0, 1000000)
        second = Cursor(towns, cap=500)
        following = Cursor(towns[:3], cap=500)
        for cursor in (second, following):
            while cursor.phase != "done":
                cursor.slice(1)
        expected = sorted((int(a[2] * b[2] * sqrt(abs(a[0] - b[0]) + abs(a[1] - b[1])))
                           for a, b in combinations(towns, 2)), reverse=True)[:500]
        self.assertEqual([score for _, _, score in second.output], expected)
        self.assertNotEqual(first.output[0], second.output[0])
        self.assertEqual(len(following.output), 3)


class Contracts(unittest.TestCase):
    def test_setting_four_zero_defaults_and_current_ceiling(self):
        info = read("info.nut")
        block = re.search(r'AddSetting\(\{\s*name = "v276_cand_slices".*?\}\);', info, re.S)[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 0", block)
        self.assertIn("min_value = 0, max_value = 2", block)
        self.assertLessEqual(info.count("AddSetting("), 100)
        self.assertIn('V276_CAND_SLICES = AIController.GetSetting("v276_cand_slices");',
                      read("settings.nut"))
        self.assertIn('V276_CAND_SLICES <- 0;', read("candidates_v276.nut"))

    def test_production_weight_is_freight_only_and_cached_annually(self):
        src = read("candidates_v276.nut")
        order = src[src.index('function OpexV276CargoOrder'):src.index('function OpexV276Request')]
        self.assertLess(order.index('V276_CARGO_YEAR == year'), order.index('foreach (cargo, sources'))
        self.assertLess(order.index('cargo == catalog.paxCargo || sources.len() == 0) continue'),
                        order.index('local score = AICargo.GetCargoIncome(cargo, 80, days);'))
        self.assertRegex(order, r'if \(V276_CAND_SLICES == 2\) \{\s*/\*.*?\*/\s*'
                         r'local monthly = 0;\s*foreach \(source in sources\)\s*'
                         r'monthly \+= AIIndustry.GetLastMonthProduction\('
                         r'catalog.industries\[source\].id, cargo\);\s*score \*= monthly;\s*\}')
        self.assertIn('ranked.AddItem(cargo, score);', order)
        self.assertEqual(src.count('AIIndustry.GetLastMonthProduction('), 1)
        self.assertIn('V276_CARGO_ORDER = result;', order)

    def test_slice_activation_accepts_both_positive_values(self):
        for path in AI.glob('*.nut'):
            for line in path.read_text(encoding="utf-8").splitlines():
                if 'V276_CAND_SLICES' in line and path.name not in ('settings.nut', 'candidates_v276.nut'):
                    self.assertRegex(line, r'V276_CAND_SLICES (?:> 0|<= 0)')

    def test_legacy_rail_early_guard(self):
        src = read("candidates.nut")
        guard = src.index('if (V276_CAND_SLICES > 0) return OpexV276Published')
        self.assertLess(guard, src.index('  ::OpexSitableCache = {};', guard))
        self.assertIn('if (V276_CAND_SLICES > 0 && !v276Pair)', src)

    def test_unit_order_depends_on_air(self):
        src = read("candidates_v276.nut")
        self.assertLess(src.index('OpexV276AddUnits(units, catalog, !MODE_AIR);'),
                        src.index('OpexV276AddUnits(units, catalog, MODE_AIR);'))
        self.assertLess(src.index('OpexV276AddUnits(units, catalog, MODE_AIR);'),
                        src.index('if (MODE_ROAD && ROAD_BUILD_ENABLED)'))

    def test_no_squirrel_pair_sort(self):
        src = read("candidates_v276.nut")
        self.assertNotIn('.sort(', src)
        self.assertIn('s.pairs.Sort(AIList.SORT_BY_VALUE, false)', src)
        self.assertIn('src.pop.tofloat() * dst.pop * sqrt(distance.tofloat())', src)
        self.assertIn('V276_CARGO_YEAR == year', src)
        self.assertIn('AICargo.GetCargoIncome(cargo, 80, days)', src)

    def test_budget_tick_remaining_and_pre_advanced_cursor(self):
        src = read("candidates_v276.nut")
        for guard in ('OpexOpsMeasureEnd(mark) >= opsBudget',
                      'AIController.GetTick() != startTick',
                      'AIController.GetTick() >= deadlineTick',
                      'AIController.GetOpsTillSuspend() < 2000'):
            self.assertIn(guard, src)
        self.assertLess(src.index('s.pairs.RemoveItem(key)'),
                        src.index('local evaluated = OpexV276Evaluate('))

    def test_task_and_load_transaction_contract(self):
        main = read("main.nut")
        self.assertNotIn('name = "v276_candidates"', main)
        self.assertNotIn('task.name == "v276_candidates"', read("scheduler.nut"))
        tick = main.index('if (V276_CAND_SLICES > 0) OpexV276Tick(this);')
        self.assertLess(main.rindex('this._runOrchestratorTick();'), tick)
        self.assertLess(main.rindex('this._advanceRailSearchThroughput();'), tick)
        self.assertLess(tick, main.index('AIController.Sleep(1);', tick))
        persist = read("persist.nut")
        for key in ('v276', 'v276Request', 'v276Rail', 'v276Road', 'v276Batches'):
            self.assertIn('delete task.' + key, persist)
        save = persist[persist.index('function OpexAI::Save'):persist.index('function OpexAI::Load')]
        self.assertNotIn('v276', save)

    def test_grid_invariants_batched_enumeration_and_observable_cap(self):
        src = read("candidates_v276.nut")
        for marker in ('const V276_PUBLISH_EVERY = 50;', 'const V276_EVAL_CAP = 500;',
                       's.unitEvaluated >= V276_EVAL_CAP', 's.unitEvaluated % V276_PUBLISH_EVERY == 0',
                       's.lastPublished != s.unitEvaluated', 'grid.Build(destinations, maxDistance)',
                       'bounds.railAirOverlapMin - 1', 'c.grid.GetCandidatesAt(src.tile',
                       'enumerated=" + s.enumerated', 'evaluated=" + s.evaluated',
                       'publications=" + s.publications', 'evaluated=" + s.unitEvaluated'):
            self.assertIn(marker, src)
        enumeration = src[src.index('function OpexV276Enumerate'):src.index('function OpexV276Continue')]
        self.assertIn('while (OpexOpsMeasureEnd(mark) < opsBudget', enumeration)
        self.assertLess(enumeration.index('local n = c.n;'), enumeration.index('while ('))
        self.assertNotIn('s.catalog.producers[u.cargo]', enumeration)
        grid = read("spatial.nut")
        self.assertIn('return this.GetCandidatesAt(this._towns[townIndex].tile, townIndex);', grid)
        self.assertIn('if (idx > minIndex) out.append(idx);', grid)

    def test_publication_snapshot_and_existing_mode_application(self):
        src = read("candidates_v276.nut")
        for marker in ('OpexAC06CaptureRevisionNumbers(owner)',
                       'OpexV276Acknowledge(owner, s.revisions)',
                       'OpexApplyGeneratedModeProjects(owner._projects',
                       's.batches.rawset(key, batch)', 'OpexTopK(s.unitBest, TOP_K)'):
            self.assertIn(marker, src)
        self.assertNotIn('OpexBuildCandidates(', re.sub(r'/\*.*?\*/', '', src, flags=re.S))

    def test_atomic_boundary_is_explicit_not_a_false_strict_budget_claim(self):
        src = read("candidates_v276.nut")
        self.assertIn('Les helpers economiques d\'une paire et la publication restent atomiques.', src)
        self.assertIn('OpexPaxCandidates(catalog, lines, out', src)
        self.assertIn('OpexFreightCandidates(catalog, lines, out', src)


if __name__ == '__main__':
    unittest.main()
