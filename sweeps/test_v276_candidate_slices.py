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


class Cursor:
    """Enumeration geometrique, puis file native de priorite (modele)."""

    def __init__(self, towns, target=None):
        self.towns = towns
        self.target = target
        self.a, self.b = 0, 1 if target is None else 0
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
            if self.b >= n:
                self.a += 1
                self.b = self.a + 1 if self.target is None else 0
                return
            a = self.a if self.target is None else self.target
            b = self.b
            self.b += 1
            if a == b:
                return
            x, y = self.towns[a], self.towns[b]
            d = abs(x[0] - y[0]) + abs(x[1] - y[1])
            self.pairs[a * n + b] = int(x[2] * y[2] * sqrt(d))
        elif self.pairs:
            key = max(self.pairs, key=lambda k: (self.pairs[k], -k))
            score = self.pairs.pop(key)
            self.output.append((key // n, key % n, score))
        else:
            self.phase = "done"

    def slice(self, budget):
        used = 0
        while self.phase != "done" and used < budget:
            self.step()
            used += 1
        return used


class Models(unittest.TestCase):
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
            self.assertLess(steps, 3 * len(self.towns) + 6)

    def test_empty_and_singleton_finish(self):
        for towns in ([], [(0, 0, 100)]):
            cursor = Cursor(towns)
            for _ in range(6):
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

    def test_round_robin_no_famine_with_permanent_air_activity(self):
        queue = ["catalog", "projects", "air_scan", "v276_candidates"]
        remaining = 71
        air_visits = project_visits = 0
        for task in queue * 71:
            if task == "air_scan":
                air_visits += 1
            if task == "projects":
                project_visits += 1
            if task == "v276_candidates" and remaining:
                remaining -= 1
        self.assertEqual(remaining, 0)
        self.assertEqual(air_visits, 71)
        self.assertEqual(project_visits, 71)


class Contracts(unittest.TestCase):
    def test_setting_four_zero_defaults_and_current_ceiling(self):
        info = read("info.nut")
        block = re.search(r'AddSetting\(\{\s*name = "v276_cand_slices".*?\}\);', info, re.S)[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 0", block)
        self.assertIn("min_value = 0, max_value = 1", block)
        self.assertLessEqual(info.count("AddSetting("), 100)
        self.assertIn('GetSetting("v276_cand_slices")', read("settings.nut"))

    def test_legacy_rail_early_guard(self):
        src = read("candidates.nut")
        guard = src.index('if (V276_CAND_SLICES) return OpexV276Published')
        self.assertLess(guard, src.index('  ::OpexSitableCache = {};', guard))
        self.assertIn('if (V276_CAND_SLICES && !v276Pair)', src)

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
        self.assertIn('if (V276_CAND_SLICES)\n      this._taskQueue.append({ name = "v276_candidates"', main)
        self.assertIn('task.name == "v276_candidates"', read("scheduler.nut"))
        persist = read("persist.nut")
        for key in ('v276', 'v276Request', 'v276Rail', 'v276Road', 'v276Batches'):
            self.assertIn('delete task.' + key, persist)
        save = persist[persist.index('function OpexAI::Save'):persist.index('function OpexAI::Load')]
        self.assertNotIn('v276', save)

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
