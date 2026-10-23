"""AC-05 : parité du parcours non orienté hub→hub.

Transcription déterministe des curseurs, filtres et reprises ; les gains/couts
restent fictifs et ne prouvent ni Squirrel/NoAI ni une neutralité économique.
"""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
import tempfile
import unittest

from sweeps.analyse_ac05_hubhub_cost import analyse

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "ai/OpexAI/air_planning.nut").read_text(encoding="utf-8")


def body(signature):
    begin = SOURCE.index(signature)
    brace = SOURCE.index("{", begin)
    depth = 0
    for i in range(brace, len(SOURCE)):
        if SOURCE[i] == "{":
            depth += 1
        elif SOURCE[i] == "}":
            depth -= 1
            if not depth:
                return SOURCE[begin:i + 1]
    raise AssertionError(f"missing closing brace {signature}")


HUB_HUB = body("function OpexAirPlansHubToHub(")
PIPELINE = body("function OpexAirPlans(")
PREPARE = body("function OpexAir0310HubSnapshotPrepare(")
HUB_INDEX = body("function OpexAirPlansPrepare(")
SKIP = body("function OpexAir0310SkipRestoredPair(")


@dataclass
class State:
    i: int = 0
    j: int = 1
    done: bool = False
    calls: int = 0
    visited: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    admitted: list = field(default_factory=list)
    pair_work: int = 0
    setup_work: int = 0


def decision(i, j, hubs, target, mask, connected, published):
    """Choix de rejet figés, dans l'ordre du .nut ; pas d'API économique."""
    if mask & 1 and (i + 2 * j) % 7 == 0:
        return "v133"
    if (i, j) in published:
        return "snapshot"
    if target is not None and target not in (hubs[i], hubs[j]):
        return "target"
    if mask & 2 and (i + j) % 11 == 0:
        return "prefilter"
    if frozenset((i, j)) in connected:
        return "already_connected"
    if mask & 4 and (i * 3 + j) % 5 == 0:
        return "distance"
    if mask & 8 and (i * 5 + j) % 6 == 1:
        return "band"
    if mask & 2 and (i + j) % 9 == 1:
        return "abandoned"
    if mask & 4 and (i * 7 + j) % 6 == 3:
        return "economics"
    return "admitted"


def advance(st, hubs, budget, cost, *, target=None, mask=0,
            connected=frozenset(), published=frozenset(), setup=0,
            deadline_pairs=None):
    """Une invocation : coût de pré-calcul payé même si n(n-1)/2 est déjà fini."""
    st.calls += 1
    st.setup_work += setup
    progressed = False
    spent = 0
    processed = 0
    n = len(hubs)
    for i in range(st.i, n):
        for j in range(st.j if i == st.i else i + 1, n):
            if progressed and ((budget > 0 and spent >= budget)
                               or (deadline_pairs is not None
                                   and processed >= deadline_pairs)):
                st.i, st.j = i, j
                return False
            progressed = True
            pair = (i, j)
            st.visited.append(pair)
            work = cost(i, j)
            st.pair_work += work
            spent += work
            processed += 1
            outcome = decision(i, j, hubs, target, mask, connected, published)
            if outcome == "admitted":
                st.admitted.append(pair)
            else:
                st.rejected.append((pair, outcome))
    st.i, st.j = n, 0
    st.done = True
    return True


def run(hubs, budget=0, cost=lambda i, j: 1, **kwargs):
    st = State()
    for _ in range(len(hubs) * (len(hubs) - 1) // 2 + 3):
        if advance(st, hubs, budget, cost, **kwargs):
            return st
    raise AssertionError("livelock")


class AC05HubHubTests(unittest.TestCase):
    def test_cursor_and_checkpoint_source_contract(self):
        needles = (
            'local resumeI = incrementalSlice && ("hubHubI" in ctx.resumeState)',
            'local resumeJ = incrementalSlice && ("hubHubJ" in ctx.resumeState)',
            'local progressed = false;',
            'for (local i = resumeI; i < hubs.len(); i++)',
            'for (local j = i == resumeI ? resumeJ : i + 1; j < hubs.len(); j++)',
            'if (progressed && ((ctx.opsBudget > 0 && used >= ctx.opsBudget)',
            'ctx.resumeState.hubHubI <- i;',
            'ctx.resumeState.hubHubJ <- j;',
            'ctx.bestPlan = bestPlan;',
            'return false;',
            'progressed = true;',
            'local hub1 = hubs[i];',
            'local hub2 = hubs[j];',
            'ctx.resumeState.hubHubI <- hubs.len();',
            'ctx.resumeState.hubHubJ <- 0;',
            'return true;',
        )
        for needle in needles:
            self.assertIn(needle, HUB_HUB)
        self.assertLess(HUB_HUB.index('ctx.resumeState.hubHubJ <- j;'),
                        HUB_HUB.index('local hub1 = hubs[i];'))
        self.assertLess(HUB_HUB.index('progressed = true;'),
                        HUB_HUB.index('OpexAir0310SkipRestoredPair(ctx'))
        self.assertNotIn('V133_AIR_BUILD_RETRY', HUB_HUB)
        self.assertLess(HUB_HUB.index('OpexAir0310SkipRestoredPair(ctx'),
                        HUB_HUB.index('CATALOG_COST_ACTIVE.airHubHubPairs++'))
        closing = body('function OpexAirPlansCompleteCombo(')
        self.assertIn('OpexAirPlansCompleteCombo(ctx, comboIndex, combo)', PIPELINE)
        self.assertIn('ctx.resumeState.hubHubI <- 0;', closing)
        self.assertIn('ctx.resumeState.hubHubJ <- 1;', closing)
        self.assertIn('resumeState.hubHubI <- 0;', PREPARE)
        self.assertIn('resumeState.hubHubJ <- 1;', PREPARE)

    def test_unordered_pairs_and_sliced_admission_matrix(self):
        # 6 tailles × 5 cibles × 4 coûts × 4 rejets × 6 budgets = 2880.
        cases = 0
        for n in (0, 1, 2, 3, 5, 9):
            hubs = [100 + i for i in range(n)]
            for target in (None, 100, 100 + n // 2, 100 + n - 1, 9999):
                for cost in (
                    lambda i, j: 1,
                    lambda i, j: 1 + (i * 7 + j * 13) % 17,
                    lambda i, j: 500 if i == 0 and j == 1 else 1,
                    lambda i, j: 500 if (i, j) == (n - 2, n - 1) else 1,
                ):
                    for mask in (0, 1, 3, 15):
                        connected = frozenset(frozenset((i, j)) for i in range(n)
                                              for j in range(i + 1, n) if (i + j) % 5 == 0)
                        published = frozenset((i, j) for i in range(n)
                                              for j in range(i + 1, n) if (2 * i + j) % 7 == 3)
                        opts = dict(cost=cost, target=target, mask=mask, connected=connected,
                                    published=published)
                        expected = run(hubs, **opts)
                        for budget in (0, 1, 2, 19, 125, 2000):
                            actual = run(hubs, budget=budget, **opts)
                            with self.subTest(n=n, target=target, mask=mask, budget=budget):
                                self.assertEqual(actual.visited, expected.visited)
                                self.assertEqual(actual.rejected, expected.rejected)
                                self.assertEqual(actual.admitted, expected.admitted)
                                self.assertEqual(actual.pair_work, expected.pair_work)
                                self.assertEqual(len(actual.visited), n * (n - 1) // 2)
                                self.assertEqual(len(actual.visited), len(set(actual.visited)))
                                self.assertTrue(all(i < j for i, j in actual.visited))
                                self.assertEqual((actual.i, actual.j, actual.done), (n, 0, True))
                            cases += 1
        self.assertEqual(cases, 2880)

    def test_last_pair_and_first_pair_after_row(self):
        hubs = list(range(5))
        st = State()
        # Quatre paires (0,1..4), puis reprise sur (1,2).
        self.assertFalse(advance(st, hubs, 4, lambda i, j: 1))
        self.assertEqual(st.visited, [(0, 1), (0, 2), (0, 3), (0, 4)])
        self.assertEqual((st.i, st.j), (1, 2))
        last = run(hubs, budget=11,
                   cost=lambda i, j: 500 if (i, j) == (3, 4) else 1)
        self.assertEqual(last.calls, 1)
        self.assertEqual(last.pair_work, 509)
        self.assertEqual(last.visited[-1], (3, 4))

    def test_tiny_budget_all_rejects_eventually_finishes(self):
        hubs = list(range(8))
        st = run(hubs, budget=1, cost=lambda i, j: 500, target=999)
        self.assertEqual(st.calls, 28)
        self.assertEqual(len(st.visited), 28)
        self.assertEqual(len(st.rejected), 28)
        self.assertEqual(len(st.admitted), 0)

    def test_deadline_after_single_pair_no_replay(self):
        hubs = list(range(7))
        actual = run(hubs, budget=0, deadline_pairs=1)
        reference = run(hubs)
        self.assertEqual(actual.visited, reference.visited)
        self.assertEqual(actual.calls, 21)

    def test_connected_is_symmetric_in_index_and_fallback(self):
        for needle in (
            'hubIndex.pairs.rawset(oA + "|" + oB, true);',
            'hubIndex.pairs.rawset(oB + "|" + oA, true);',
            'alreadyConnected = (st1 + "|" + st2) in hubIndex.pairs;',
            'if ((oA == st1 && oB == st2) || (oA == st2 && oB == st1))',
        ):
            self.assertIn(needle, SOURCE)
        edge = frozenset((1, 4))
        self.assertEqual(edge, frozenset((4, 1)))
        hubs = list(range(6))
        actual = run(hubs, connected=frozenset((edge,)))
        self.assertIn(((1, 4), "already_connected"), actual.rejected)
        self.assertNotIn((1, 4), actual.admitted)

    def test_repeated_marginal_precalc_is_overhead_not_pair_replay(self):
        hubs = list(range(7))
        reference = run(hubs, setup=100)
        sliced = run(hubs, budget=1, setup=100)
        self.assertEqual(sliced.visited, reference.visited)
        self.assertEqual(sliced.pair_work, reference.pair_work)
        self.assertGreater(sliced.setup_work, reference.setup_work)
        self.assertEqual(sliced.setup_work, 21 * 100)
        # Ce surcout est conditionnel au réglage marginal, pas une mesure VM.

    def test_marginal_precalc_is_unused_under_c121(self):
        # V222 purge : air_hubhub_marginal et hubAvgIncome sont retirés sous C121.
        info = (ROOT / "ai/OpexAI/info.nut").read_text(encoding="utf-8")
        self.assertNotIn('name = "air_hubhub_marginal"', info)
        self.assertNotIn("hubAvgIncome", HUB_HUB)
        self.assertNotIn("AIR_HUBHUB_MARGINAL", HUB_HUB)

    def test_cost_parser_does_not_divide_phase_by_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.log"
            path.write_text(
                "OPEX 1972-1-1 AIR_LIGHT v=1 edge=exit reason=hub_hub_yield "
                "hub_hub_ops=75 hub_hub_calls=1 hub_hub_ticks=2 hub_hub_days=1\n"
                "OPEX 1972-1-2 AIR_LIGHT v=1 edge=exit reason=done "
                "hub_hub_ops=25 hub_hub_calls=1 hub_hub_ticks=0 hub_hub_days=0\n"
                "OPEX 1972-1-3 CATALOG_COST reason=full air_hub_hub_pairs=5\n",
                encoding="utf-8",
            )
            result = analyse(path)
        row = result["years"]["1972"]
        self.assertEqual(row["hub_hub_phase_ops"], 100)
        self.assertEqual(row["hub_hub_phase_calls"], 2)
        self.assertEqual(row["hub_hub_yields"], 1)
        self.assertEqual(row["catalog_hub_hub_pairs"], 5)
        self.assertIsNone(result["per_pair_opcode_cost"])

    def test_snap_invalidation_intentionally_restarts_only_its_new_snapshot(self):
        old = list(range(5))
        first = run(old)
        # Signature différente -> (0,1) et phase0 ; paires publiées sautées.
        self.assertIn('resumeState.hubHubI <- 0;', PREPARE)
        self.assertIn('resumeState.hubHubJ <- 1;', PREPARE)
        published = frozenset(first.admitted)
        fresh = run(list(range(6)), published=published)
        self.assertEqual(len(fresh.visited), 15)
        self.assertEqual(len(fresh.admitted), 5)
        self.assertEqual(Counter(reason for _, reason in fresh.rejected)["snapshot"], 10)


if __name__ == "__main__":
    unittest.main()
