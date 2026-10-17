"""AC-03 : parcours `(a,b)` AIR sur un état de sites et de choix figé.

Ce modèle teste les checkpoints et les suspensions de NewPairs ; il ne lance
pas Squirrel/NoAI et n'établit aucune neutralité économique ou opcode.
Les contrats textuels lient chaque transition au code de production courant.
"""

from dataclasses import dataclass, field
from pathlib import Path
import unittest


AIR = (Path(__file__).resolve().parents[1] / "ai/OpexAI/air_planning.nut").read_text(
    encoding="utf-8"
)


def body(signature):
    start = AIR.index(signature)
    brace = AIR.index("{", start)
    depth = 0
    for pos in range(brace, len(AIR)):
        if AIR[pos] == "{":
            depth += 1
        elif AIR[pos] == "}":
            depth -= 1
            if depth == 0:
                return AIR[start : pos + 1]
    raise AssertionError(f"missing closing brace: {signature}")


PREPARE = body("function OpexAirPlansPrepare(")
FIND_SITES = body("function OpexAirPlansFindSites(")
NEW_PAIRS = body("function OpexAirPlansNewPairs(")
PIPELINE = body("function OpexAirPlans(")
CLOSE = body("function OpexAirPlansCompleteCombo(")


@dataclass
class Cursor:
    combo: int = 0
    a: int = 0
    b: int = 1
    visited: list = field(default_factory=list)
    eligible: list = field(default_factory=list)
    admitted: list = field(default_factory=list)
    total_ops: int = 0
    calls: int = 0


def step(cursor, sites, target, budget, cost, admit, combo=0):
    """Transcription de la boucle de contrôle, hors moteurs/API/score.

    Le contrôle de budget se fait AVANT la paire suivante, mais seulement
    après qu'au moins une paire a été consommée dans cette invocation.
    Le curseur est placé sur la suivante AVANT les filtres et le choix.
    """
    n = len(sites)
    target_index = next((i for i, town in enumerate(sites) if town == target), -1)
    outer_limit = n
    if target is not None and target_index < 0:
        outer_limit = 0
    elif target is not None and target_index == 0:
        outer_limit = 1
    start_a = cursor.a if cursor.combo == combo else 0
    progressed = False
    used = 0
    cursor.calls += 1
    for a in range(start_a, outer_limit):
        start_b = cursor.b if cursor.combo == combo and a == start_a else a + 1
        for b in range(start_b, n):
            if progressed and budget > 0 and used >= budget:
                cursor.total_ops += used
                return False
            cursor.combo = combo
            next_a, next_b = a, b + 1
            if next_b >= n:
                next_a, next_b = a + 1, a + 2
            cursor.a, cursor.b = next_a, next_b
            progressed = True
            pair = (a, b)
            cursor.visited.append(pair)
            used += cost(a, b)
            if target is not None and target not in (sites[a], sites[b]):
                continue
            cursor.eligible.append(pair)
            if admit(a, b):
                cursor.admitted.append(pair)
    cursor.a = n
    cursor.b = n
    cursor.total_ops += used
    if budget > 0 and used >= budget:
        return False
    return True


def run(sites, target=None, budget=10**9, *, cost=lambda a, b: 1,
        admit=lambda a, b: True, combo=0):
    cursor = Cursor(combo=combo)
    limit = len(sites) * (len(sites) - 1) // 2 + 4
    for _ in range(limit):
        if step(cursor, sites, target, budget, cost, admit, combo):
            return cursor
    raise AssertionError("possible livelock: scan did not finish")


class AC03AirNewPairsResumeTests(unittest.TestCase):
    def test_real_code_checkpoint_precedes_all_pair_filters(self):
        for part in (
            "local pairOuterLimit = sites.len();",
            "if (targetTownId >= 0 && targetSiteIndex < 0) pairOuterLimit = 0;",
            "else if (targetTownId >= 0 && targetSiteIndex == 0) pairOuterLimit = 1;",
            "local startA = sliced && resumeState.combo == comboIndex ? resumeState.a : 0;",
            "local pairProgress = false;",
            "local startB = sliced && resumeState.combo == comboIndex && a == startA",
            "if (pairProgress && ((opsBudget > 0 && sliceOps >= opsBudget)",
            "resumeState.combo = comboIndex;",
            "resumeState.sites = sites;",
            "local nextB = b + 1;",
            "if (nextB >= sites.len())",
            "nextA = a + 1;",
            "nextB = nextA + 1;",
            "resumeState.a = nextA;",
            "resumeState.b = nextB;",
            "pairProgress = true;",
            "resumeState.a = sites.len();",
            "resumeState.b = sites.len();",
            "resumeState.bestPlan = bestPlan;",
        ):
            self.assertIn(part, NEW_PAIRS)
        self.assertLess(NEW_PAIRS.index("if (pairProgress &&"),
                        NEW_PAIRS.index("resumeState.a = nextA;"))
        self.assertLess(NEW_PAIRS.index("resumeState.a = nextA;"),
                        NEW_PAIRS.index("if (resumingCombo)"))
        self.assertLess(NEW_PAIRS.index("resumeState.b = nextB;"),
                        NEW_PAIRS.index("if (V133_AIR_BUILD_RETRY)"))
        self.assertLess(NEW_PAIRS.index("resumeState.a = nextA;"),
                        NEW_PAIRS.index("OpexAirStoreRoutePlan("))
        self.assertIn("resumeState.a <- 0;", PREPARE)
        self.assertIn("resumeState.b <- 1;", PREPARE)
        self.assertIn("resumeState.a = 0;", FIND_SITES)
        self.assertIn("resumeState.b = 1;", FIND_SITES)
        self.assertIn("OpexAirPlansCompleteCombo(ctx, comboIndex, combo)", PIPELINE)
        self.assertLess(PIPELINE.index("if (!pairsOk)"),
                        PIPELINE.index("OpexAirPlansCompleteCombo(ctx, comboIndex, combo)"))
        self.assertIn("ctx.resumeState.a = 0;", CLOSE)
        self.assertIn("ctx.resumeState.b = 1;", CLOSE)

    def test_filters_and_admission_are_inside_pair_loop(self):
        ordered = (
            "if (V133_AIR_BUILD_RETRY)",
            "CATALOG_COST_ACTIVE.airPairs++",
            "if (targetTownId >= 0\n          && sites[a].town.id != targetTownId",
            "OpexAirTownCentersLinked(",
            "AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile)",
            "OpexAirPairInBand(",
            "OpexAirPairIsAbandoned(",
            "local plan = {",
            "local routeChoice = OpexC121CatalogChoice",
            "admissionEconomics.profitAnnual <= 0",
            "OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan)",
        )
        positions = [NEW_PAIRS.index(part) for part in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("if (!siteValidity[keyA]) continue;", NEW_PAIRS)
        self.assertIn("if (!siteValidity[keyB]) continue;", NEW_PAIRS)
        self.assertIn("resumeState.perfOpsEval = perfOpsEval + _calcDeltaOps(tEval0, lEval0);", NEW_PAIRS)
        self.assertIn("resumeState.totalOps += sliceOps;", NEW_PAIRS)
        self.assertIn("resumeState.totalOps += pairSliceOps;", NEW_PAIRS)

    def test_exhaustive_frozen_pairs_and_admission_parity(self):
        # 7 tailles × 5 cibles × 4 profils de coûts × 6 budgets × 3
        # filtres déterministes = 2 520 scénarios de reprise.
        cases = 0
        for n in (0, 1, 2, 3, 5, 9, 15):
            sites = [100 + i for i in range(n)]
            first = sites[0] if n else None
            mid = sites[n // 2] if n else None
            last = sites[-1] if n else None
            for target in (None, first, mid, last, 9999):
                for cost in (
                    lambda a, b: 1,
                    lambda a, b: 1 + (a * 3 + b * 5) % 7,
                    lambda a, b: 50 if (a + b) % 4 == 0 else 1,
                    lambda a, b: 300,
                ):
                    for admit in (
                        lambda a, b: True,
                        lambda a, b: (a + b) % 2 == 0,
                        lambda a, b: ((a * 7 + b * 11) % 5) in (1, 4),
                    ):
                        reference = run(sites, target, cost=cost, admit=admit)
                        for budget in (1, 2, 7, 29, 100, 1000):
                            with self.subTest(n=n, target=target, budget=budget):
                                actual = run(sites, target, budget, cost=cost, admit=admit)
                                self.assertEqual(actual.visited, reference.visited)
                                self.assertEqual(actual.eligible, reference.eligible)
                                self.assertEqual(actual.admitted, reference.admitted)
                                self.assertEqual(actual.total_ops, reference.total_ops)
                                self.assertEqual(len(actual.visited), len(set(actual.visited)))
                                self.assertEqual(actual.a, n)
                                self.assertEqual(actual.b, n)
                            cases += 1
        self.assertEqual(cases, 7 * 5 * 4 * 3 * 6)

    def test_all_pairs_traversed_once_even_when_rejected(self):
        sites = list(range(8))
        expected = [(a, b) for a in range(8) for b in range(a + 1, 8)]
        cursor = run(sites, budget=1, cost=lambda a, b: 500,
                     admit=lambda a, b: False)
        self.assertEqual(cursor.visited, expected)
        self.assertEqual(cursor.eligible, expected)
        self.assertEqual(cursor.admitted, [])
        self.assertEqual(cursor.calls, len(expected) + 1)

    def test_target_first_middle_last_and_missing(self):
        sites = [10, 20, 30, 40]
        normal = run(sites).visited
        for target in sites:
            actual = run(sites, target, budget=1)
            wanted = [pair for pair in normal if target in (sites[pair[0]], sites[pair[1]])]
            self.assertEqual(actual.eligible, wanted)
            self.assertEqual(actual.admitted, wanted)
            self.assertEqual(len(actual.eligible), len(sites) - 1)
        self.assertEqual(run(sites, target=10).visited, [(0, 1), (0, 2), (0, 3)])
        self.assertEqual(run(sites, target=30).visited, normal)
        self.assertEqual(run(sites, target=9999, budget=1).visited, [])

    def test_cut_after_row_and_after_final_expensive_pair(self):
        sites = [10, 20, 30, 40]
        cursor = Cursor()
        self.assertFalse(step(cursor, sites, None, 3, lambda a, b: 1,
                              lambda a, b: True))
        self.assertEqual(cursor.visited, [(0, 1), (0, 2), (0, 3)])
        self.assertEqual((cursor.a, cursor.b), (1, 2))
        self.assertFalse(step(cursor, sites, None, 3, lambda a, b: 1,
                              lambda a, b: True))
        self.assertEqual(cursor.visited[-3:], [(1, 2), (1, 3), (2, 3)])
        self.assertEqual((cursor.a, cursor.b), (4, 4))
        self.assertTrue(step(cursor, sites, None, 3, lambda a, b: 1,
                             lambda a, b: True))
        self.assertEqual(len(cursor.visited), 6)
        self.assertEqual(len(set(cursor.visited)), 6)

        # La dernière paire est très coûteuse, puis le code sort par la
        # branche de budget de fin de boucle : pas de réévaluation au rappel.
        expensive = lambda a, b: 20 if (a, b) == (2, 3) else 1
        last = Cursor()
        self.assertFalse(step(last, sites, None, 25, expensive, lambda a, b: True))
        self.assertEqual((last.a, last.b), (4, 4))
        self.assertEqual(last.total_ops, 25)
        self.assertTrue(step(last, sites, None, 25, expensive, lambda a, b: True))
        self.assertEqual(last.total_ops, 25)
        self.assertEqual(len(last.admitted), 6)


if __name__ == "__main__":
    unittest.main()
