"""Adversarial, engine-free parity oracle for the isolated P0 Top-K stage.

The Python reference below independently transliterates the *historical*
right-to-left insertion, not the binary algorithm.  The third oracle is
Python's stable sorted(..., reverse=True).  Comparisons use object identity,
not dataclass value equality, to catch permutations of tied projects.

This is not a Squirrel VM test and never establishes a global opcode saving.
"""

from dataclasses import dataclass, replace
from itertools import product
from pathlib import Path
import math
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
LIMITS = (1, 8, 20, 64, 128)


@dataclass(eq=False)
class Project:
    ident: int
    mode: str = "air"
    profit: float = 100.0
    competitor: int = 0
    own: int = 0
    preempt: int = 0
    chain: bool = False
    score: float = 0.0
    bonus: float = 0.0
    revenue: float = 0.0


def defensive_tier(row, c83_preempt=False):
    """OpexProjectDefensiveAirPriority: profit gate and C77 precedence."""
    if row.mode != "air" or row.profit <= 0:
        return 0
    if row.competitor > 0 or (c83_preempt and row.preempt > 0):
        return 2
    if row.own > 0:
        return 1
    return 0


def priority(row, *, chain_force=False, early_slot=False, c83_preempt=False):
    tier = defensive_tier(row, c83_preempt)
    if chain_force and row.chain:
        tier += 1000
    score = row.score
    if early_slot and row.mode == "air" and row.bonus > 0:
        score *= (100.0 + float(row.bonus)) / 100.0
    return tier, score, row.revenue


def historic_insert(best, incoming, limit, *, chain_force=False,
                    early_slot=False, c83_preempt=False):
    """Independent translation of OpexProjectInsertDefensive, C118/C122 off."""
    target_tier, target_score, target_revenue = priority(
        incoming, chain_force=chain_force, early_slot=early_slot,
        c83_preempt=c83_preempt
    )
    index = len(best)
    while index > 0:
        previous = best[index - 1]
        old_tier, old_score, old_revenue = priority(
            previous, chain_force=chain_force, early_slot=early_slot,
            c83_preempt=c83_preempt
        )
        if old_tier > target_tier:
            break
        if old_tier < target_tier:
            index -= 1
            continue
        if old_score > target_score:
            break
        if old_score == target_score and old_revenue >= target_revenue:
            break
        index -= 1
    best.insert(index, incoming)
    if len(best) > limit:
        best.pop()
    return index


def binary_insert(best, incoming, limit, *, chain_force=False,
                  early_slot=False, c83_preempt=False):
    """Translation of the staged Squirrel binary branch, not the oracle."""
    target = priority(incoming, chain_force=chain_force,
                      early_slot=early_slot, c83_preempt=c83_preempt)
    lo, hi = 0, len(best)
    while lo < hi:
        mid = (lo + hi) // 2
        prior = priority(best[mid], chain_force=chain_force,
                         early_slot=early_slot, c83_preempt=c83_preempt)
        if (prior[0] > target[0]
                or (prior[0] == target[0]
                    and (prior[1] > target[1]
                         or (prior[1] == target[1]
                             and prior[2] >= target[2])))):
            lo = mid + 1
        else:
            hi = mid
    best.insert(lo, incoming)
    if len(best) > limit:
        best.pop()
    return lo


def same_references(testcase, actual, expected, context):
    testcase.assertEqual(len(actual), len(expected), context)
    for rank, (left, right) in enumerate(zip(actual, expected)):
        testcase.assertIs(left, right, (context, rank, left.ident, right.ident))


def assert_stream(testcase, stream, limit, *, check_prefix=True, **settings):
    """Three independent results: historic insertion, binary, stable sort."""
    historical = []
    binary = []
    prefix = []
    for i, row in enumerate(stream):
        old_index = historic_insert(historical, row, limit, **settings)
        binary_index = binary_insert(binary, row, limit, **settings)
        prefix.append(row)
        context = (limit, i, settings, [p.ident for p in stream])
        testcase.assertEqual(old_index, binary_index, context)
        same_references(testcase, binary, historical, context)
        if check_prefix:
            oracle = sorted(
                prefix, key=lambda x: priority(x, **settings), reverse=True
            )[:limit]
            same_references(testcase, historical, oracle, context)
    if not check_prefix:
        oracle = sorted(
            prefix, key=lambda x: priority(x, **settings), reverse=True
        )[:limit]
        same_references(testcase, historical, oracle, (limit, settings))


def function_body(source, function):
    """Select an entire top-level Squirrel function, including nested braces."""
    match = re.search(
        r"(?m)^function\s+" + re.escape(function) + r"\([^\n]*\)\s*\{",
        source,
    )
    if match is None:
        raise AssertionError("Missing Squirrel function " + function)
    # Function-closing brace is unindented in these source files.
    end = re.search(r"(?m)^\}\s*$", source[match.end():])
    if end is None:
        raise AssertionError("Unclosed Squirrel function " + function)
    return source[match.end():match.end() + end.start()]


class AdversarialTopK(unittest.TestCase):
    def test_exhaustive_pair_grid_every_limit_and_flags(self):
        # Exhaust every ordered pair from the C77-tier x chain x signed-score
        # x signed-revenue x early bonus grid, plus non-AIR / zero-profit rows.
        samples = []
        for tier, chain, score, revenue, bonus in product(
                (0, 1, 2), (False, True), (-1.5, -0.0, 2.25),
                (-3.0, 0.0, 5.0), (0.0, 50.0)):
            samples.append(Project(
                ident=len(samples), competitor=int(tier == 2),
                own=int(tier == 1), chain=chain, score=score,
                revenue=revenue, bonus=bonus,
            ))
        for mode, profit, chain, bonus in product(
                ("air", "rail"), (-1.0, 0.0), (False, True),
                (0.0, 50.0)):
            samples.append(Project(
                ident=len(samples), mode=mode, profit=profit,
                competitor=1, own=1, chain=chain, score=-2.5,
                bonus=bonus, revenue=-4.0,
            ))
        self.assertGreaterEqual(len(samples), 120)
        for chain_force, early_slot in product((False, True), repeat=2):
            settings = dict(chain_force=chain_force, early_slot=early_slot)
            for limit in LIMITS:
                for a in samples:
                    for b in samples:
                        assert_stream(self, (a, b), limit, **settings)

    def test_exhaustive_four_step_streams_with_equal_keys_and_truncation(self):
        # Exhaustive temporal order over a small adversarial alphabet:
        # 12**4 streams and all K, with repeated references allowed.
        alphabet = [
            Project(0, competitor=1, score=-3.0, revenue=0),
            Project(1, competitor=1, score=-3.0, revenue=0),
            Project(2, own=1, chain=True, score=-1.5, bonus=50, revenue=-1),
            Project(3, own=1, chain=False, score=-1.5, bonus=50, revenue=-1),
            Project(4, own=1, score=-1.0, revenue=1),
            Project(5, score=-0.0, revenue=0),
            Project(6, score=0.0, revenue=0),
            Project(7, mode="rail", chain=True, score=-2.0, revenue=2),
            Project(8, mode="rail", score=2.0, revenue=-2),
            Project(9, profit=0.0, competitor=1, score=1.0, bonus=50, revenue=0),
            Project(10, preempt=1, own=1, score=-3.0, revenue=1),
            Project(11, score=2.0, bonus=50, revenue=0),
        ]
        for indices in product(range(len(alphabet)), repeat=4):
            stream = [alphabet[x] for x in indices]
            for limit in LIMITS:
                assert_stream(
                    self, stream, limit, chain_force=True,
                    early_slot=True, c83_preempt=True,
                )

    def test_long_full_k_and_truncation_at_every_supported_limit(self):
        for limit in LIMITS:
            for order in ("ascending", "descending", "alternating", "all_equal"):
                stream = []
                for i in range(2 * limit + 13):
                    score = (
                        float(i) if order == "ascending"
                        else -float(i) if order == "descending"
                        else float((-1) ** i * i) if order == "alternating"
                        else -2.5
                    )
                    stream.append(Project(
                        ident=i, competitor=int(i % 13 == 0), own=int(i % 7 == 0),
                        chain=(i % 3 == 0), mode="rail" if i % 9 == 0 else "air",
                        score=score, bonus=50 if i % 4 == 0 else 0,
                        revenue=float(i % 4) - 3.0,
                    ))
                assert_stream(
                    self, stream, limit, check_prefix=False,
                    chain_force=True, early_slot=True,
                )

    def test_tie_stability_exact_revenue_and_negative_zero(self):
        for limit in LIMITS:
            rows = [
                Project(i, score=0.0 if i % 2 else -0.0, revenue=-5.0)
                for i in range(2 * limit + 4)
            ]
            assert_stream(self, rows, limit, early_slot=True)
            self.assertTrue(all(math.isfinite(r.score) for r in rows))

    def test_aliased_reference_without_mutation_is_not_a_counterexample(self):
        duplicate = Project(99, score=5.0, revenue=2.0)
        stream = [
            Project(0, score=10.0), duplicate, duplicate,
            Project(1, score=4.0), duplicate, Project(2, score=0.0),
        ]
        for limit in LIMITS:
            assert_stream(self, stream, limit)

    def test_mutated_aliased_key_is_a_documented_nonparity_not_a_false_failure(self):
        # With mutable projects already inside best, even *one* modification
        # can destroy the sorted invariant required by the binary search.
        shared = Project(2, score=6.0)
        original = [
            Project(0, score=10.0), Project(1, score=8.0),
            shared, shared, Project(3, score=4.0),
        ]
        incoming = Project(4, score=3.0)
        old = list(original)
        new = list(original)
        shared.score = 0.0  # both aliases mutate; best is now nonmonotone
        old_index = historic_insert(old, incoming, 8)
        new_index = binary_insert(new, incoming, 8)
        self.assertEqual((old_index, new_index), (5, 2))
        self.assertIs(old[5], incoming)
        self.assertIs(new[2], incoming)
        self.assertEqual(
            [x.score for x in original], [10.0, 8.0, 0.0, 0.0, 4.0]
        )

    def test_nan_key_is_an_explicit_unordered_diagnostic(self):
        # NaN is outside the strict total-order premise. This demonstrates
        # *possible* disagreement; neither behavior is asserted correct.
        previous = [
            Project(0, score=10.0), Project(1, score=8.0),
            Project(2, score=math.nan), Project(3, score=4.0),
        ]
        old = list(previous)
        new = list(previous)
        incoming = Project(4, score=3.0)
        self.assertEqual(historic_insert(old, incoming, 8), 4)
        self.assertEqual(binary_insert(new, incoming, 8), 2)
        self.assertTrue(math.isnan(previous[2].score))

    def test_squirrel_source_order_comparison_limits_and_special_fallbacks(self):
        source = (AI / "projects_selection.nut").read_text(encoding="utf-8")
        legacy = function_body(source, "OpexProjectInsertDefensive")
        binary = function_body(source, "OpexP0TopKBinaryInsert")
        dispatch = function_body(source, "OpexP0TopKInsert")
        selection = function_body(source, "OpexProjectSelectAffordable")

        # This test guards the actual Squirrel branch: a Python-only oracle
        # could still pass after an accidental change in projects_selection.
        for code in (legacy, binary):
            for fragment in (
                "OpexProjectDefensiveAirPriority(project)",
                "OpexProjectDefensiveAirPriority(prior)",
                "V88_CHAIN_FORCE && OpexProjectIsForcedChain(project)",
                "V88_CHAIN_FORCE && OpexProjectIsForcedChain(prior)",
                "OpexProjectSelectionScore(project, field)",
                "OpexProjectSelectionScore(prior, field)",
                "prior.revenueAnnual >= project.revenueAnnual",
            ):
                self.assertIn(fragment, code)
        self.assertIn("if (priorTier > projectTier) break;", legacy)
        self.assertIn("if (priorTier < projectTier)", legacy)
        self.assertIn("if (priorScore > projectScore) break;", legacy)
        self.assertIn("best.insert(pos, project);", legacy)
        self.assertIn("best.insert(lo, project);", binary)
        self.assertIn("if (best.len() > limit) best.pop();", binary)
        for fragment in (
            "local lo = 0, hi = best.len();",
            "while (lo < hi)",
            "local mid = (lo + hi) / 2;",
            "oldTier > newTier", "oldTier == newTier",
            "oldScore > newScore", "oldScore == newScore",
            "lo = mid + 1;", "else hi = mid;",
        ):
            self.assertIn(fragment, binary)

        for guard in (
            "C118_AIR_TERRITORIAL_EXPANSION",
            "C118_AIR_PROJECT_SNAPSHOT != null",
            "C118_AIR_PROJECT_SNAPSHOT.active",
            "C122_AIR_REGIME_PRIORITY",
            "C122_AIR_REGIME_SHADOW",
            "AIR_EFFICIENCY_DEDUPE",
            "PROBE_SELECT_REJECT",
        ):
            self.assertIn(guard, dispatch)
        self.assertRegex(
            dispatch, r"if \(c118 \|\| C122_AIR_REGIME_PRIORITY \|\| "
            r"C122_AIR_REGIME_SHADOW\s*\|\| AIR_EFFICIENCY_DEDUPE "
            r"\|\| PROBE_SELECT_REJECT\)\s*\{\s*"
            r"OpexProjectInsertDefensive\(best, project, field, limit, applyEarlySlot\);\s*return;",
        )
        self.assertIn("if (!P0_TOPK_BINARY && !P0_TOPK_BINARY_CHECK)", dispatch)
        self.assertIn("OpexProjectInsertDefensive(best, project, field, limit, applyEarlySlot);", dispatch)
        self.assertIn("OpexP0TopKBinaryInsert(best, project, field, limit, applyEarlySlot);", dispatch)
        self.assertLess(dispatch.index("if (P0_TOPK_BINARY_CHECK)"),
                        dispatch.rindex("OpexP0TopKBinaryInsert("))
        self.assertIn("foreach (prior in best) copyBest.append(prior);", dispatch)
        self.assertIn("OpexProjectInsertDefensive(best, project, field, limit, applyEarlySlot);", dispatch)
        self.assertIn("if (best[i] != copyBest[i])", dispatch)
        self.assertIn("return; /* check force TOUJOURS le resultat historique */", dispatch)

        # Normal/floor-fallback passes only. C69, dedupe-pair and C121
        # diagnostics remain on the legacy helper.
        self.assertEqual(selection.count(
            "OpexP0TopKInsert(affordable, project, scoreKey, limit, AIR_EARLY_SLOT);"), 2)
        for unchanged in (
            "OpexProjectInsertDefensive(c69Affordable",
            "OpexProjectInsertDefensive(pairBest",
            "OpexProjectInsertDefensive(affordable, pairBest[0]",
        ):
            self.assertIn(unchanged, selection)
        self.assertLess(selection.index("OpexP0TopKInsert("),
                        selection.index("OpexC120ReorderAffordableAir(affordable);"))
        self.assertIn("OpexProjectInsertDefensive(shadowOrder", source)

    def test_squirrel_setting_defaults_and_no_new_save_load_fields(self):
        info = (AI / "info.nut").read_text(encoding="utf-8")
        settings = (AI / "settings.nut").read_text(encoding="utf-8")
        globals_pre = (AI / "globals_pre.nut").read_text(encoding="utf-8")
        persist = (AI / "persist.nut").read_text(encoding="utf-8")
        for flag, state in (
            ("p0_topk_binary", "P0_TOPK_BINARY"),
            ("p0_topk_binary_check", "P0_TOPK_BINARY_CHECK"),
        ):
            declaration = re.search(
                r"AddSetting\(\{\s*name = \"" + re.escape(flag)
                + r"\",(.*?)\}\);", info, flags=re.S,
            )
            self.assertIsNotNone(declaration, flag)
            for difficulty in ("easy", "medium", "hard", "custom"):
                self.assertRegex(
                    declaration.group(1), rf"\b{difficulty}_value\s*=\s*0\b"
                )
            self.assertIn(f'AIController.GetSetting("{flag}")', settings)
            self.assertIn(f"{state} <- false;", globals_pre)
            self.assertNotIn(state, persist)
        self.assertIn("P0_TOPK_BINARY_PROF = null;", settings)
        self.assertNotIn("P0_TOPK_BINARY_PROF", persist)


if __name__ == "__main__":
    unittest.main()
