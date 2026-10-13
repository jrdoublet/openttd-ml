"""P4 flip probe: host-only, source contracts and independent order fixtures.

These tests do not execute Squirrel. A Docker smoke is required for runtime
compilation, exact head reconciliation and opcode impact before interpreting logs.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def fn(text, name):
    match = re.search(r"^function " + re.escape(name) + r"\([^\n]*\)\s*\{", text, re.M)
    if match is None:
        raise AssertionError(name)
    # The functions under test have no braces inside quoted strings except this
    # simple scan's irrelevant comments. Stop at the next top-level function.
    following = re.search(r"^function [A-Za-z_]", text[match.end():], re.M)
    end = len(text) if following is None else match.end() + following.start()
    return text[match.start():end]


def rank_fixture(rows, *, stable, bonus=0, dedup=False, limit=64):
    """Small independent contract model: (C77+V88, fundScore, revenue, stable tie)."""
    accepted = []
    pair_best = {}
    for pos, item in enumerate(rows):
        if not item["affordable"] or not item["floor"]:
            continue
        k = item["stable"] if stable else item["legacy"]
        profit = item["profit"] if item.get("observed") or item.get("engine") else item["profit"] * k
        score = max(0.0, profit * 1000 / item["denom"]) if item["denom"] > 0 else 0.0
        if item["mode"] == "air":
            score *= 1 + bonus / 100
        tier = item["tier"] + (1000 if item.get("forced") else 0)
        entry = (tier, score, item["revenue"], -pos, item["key"])
        if dedup and item["mode"] == "air":
            pair = item["pair"]
            if pair in pair_best and pair_best[pair] >= entry:
                continue
            pair_best[pair] = entry
        else:
            accepted.append(entry)
    if dedup:
        accepted.extend(pair_best.values())
    return [entry[4] for entry in sorted(accepted, reverse=True)[:limit]]


def candidate(key, mode, profit, *, tier=0, denom=100, revenue=10000,
              legacy=1.0, stable=1.0, pair=None, affordable=True,
              floor=True, observed=False, engine=False, forced=False):
    return dict(key=key, mode=mode, profit=profit, tier=tier, denom=denom,
                revenue=revenue, legacy=legacy, stable=stable,
                pair=pair or key, affordable=affordable, floor=floor,
                observed=observed, engine=engine, forced=forced)


class FlipShadowContracts(unittest.TestCase):
    def test_off_four_difficulties_and_one_settings_gate(self):
        block = source("info.nut").split('name = "score_p4_flip_shadow"', 1)[1].split("});", 1)[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{difficulty}_value = 0", block)
        settings = source("settings.nut")
        self.assertIn('SCORE_P4_FLIP_SHADOW = AIController.GetSetting("score_p4_flip_shadow") != 0;', settings)
        self.assertIn('SCORE_C70_COHORT_LOG || SCORE_C70_STABLE_COHORT || SCORE_P4_FLIP_SHADOW', settings)
        self.assertIn('SCORE_P4_FLIP_SHADOW <- false;', source("globals_pre.nut"))

    def test_exact_post_cash_floor_fallback_buffer(self):
        body = fn(source("projects_selection.nut"), "OpexProjectSelectAffordable")
        self.assertIn('p4FlipEligible = (SCORE_P4_FLIP_SHADOW && realSelection && C70_MODE_CALIBRATION)', body)
        first_cash = body.index('if (financeCapital > capitalBudget) {')
        first_floor = body.index('if (project.profitAnnual < c121DefensiveFloor')
        first_append = body.index('p4FlipEligible.append(')
        self.assertLess(first_cash, first_floor)
        self.assertLess(first_floor, first_append)
        self.assertIn('if (p4FlipEligible != null) p4FlipEligible.clear();', body)
        self.assertEqual(body.count('p4FlipEligible.append('), 2)
        self.assertLess(body.index('p4FlipEligible.clear()'), body.rindex('p4FlipEligible.append('))
        self.assertIn('OpexP4FlipObserve(p4FlipEligible, affordable, capitalBudget, limit, kDec)', body)

    def test_clones_and_native_tie_break_and_od_dedup(self):
        body = fn(source("projects_selection.nut"), "OpexP4FlipRank")
        for fragment in ('clone row.project', 'project._bsStamp = -1',
                         'OpexProjectInsertDefensive(', 'OpexProjectPairKey(',
                         'AIR_EFFICIENCY_DEDUPE', 'AIR_EARLY_SLOT', 'row.denom',
                         '_p4Ordinal'):
            self.assertIn(fragment, body)
        self.assertNotIn('row.project.fundScore =', body)
        insert = fn(source("projects_selection.nut"), "OpexProjectInsertDefensive")
        self.assertIn('OpexProjectDefensiveAirPriority(', insert)
        self.assertIn('OpexProjectIsForcedChain(', insert)
        self.assertIn('prior.revenueAnnual >= project.revenueAnnual', insert)

    def test_c70_c82_bypasses_and_exact_budget_denominator(self):
        models = fn(source("projects_selection.nut"), "OpexP4FlipCalibratedProfit")
        for key in ('profitIsObserved', 'AIR_P0_DIRECT_REALIZATION_ACTIVE',
                    'OpexC121ProjectHasRealization', 'v161Calibrate',
                    'C82_ENGINE_CALIBRATION', 'OpexC82ProjectEngine',
                    'OpexC82EngineFactor', 'C70_MODE_CALIBRATION'):
            self.assertIn(key, models)
        self.assertLess(models.index('C82_ENGINE_CALIBRATION'), models.index('return project.profitAnnual * k;'))
        body = fn(source("projects_selection.nut"), "OpexProjectSelectAffordable")
        self.assertGreaterEqual(body.count('scoreDecisionFinanceCapital'), 4)
        self.assertEqual(body.count('p4FlipEligible.append('), 2)
        self.assertIn('? kDec : scoreDecisionFinanceCapital', body)

    def test_report_and_reload_capture_both_k_without_mutating_scoring_for_shadow(self):
        report = source("task_report.nut")
        model = fn(source("projects_models.nut"), "OpexC70RecomputeFactors")
        for key in ('SCORE_P4_FLIP_LEGACY_K[mode] = legacyK',
                    'SCORE_P4_FLIP_STABLE_K[mode] = stableK'):
            self.assertIn(key, report)
        self.assertIn('P4_FLIP_FACTOR exercise=', report)
        self.assertIn('candidate_n=', report)
        for key in ('SCORE_P4_FLIP_LEGACY_K[m]', 'SCORE_P4_FLIP_STABLE_K[m]',
                    'if (SCORE_C70_STABLE_COHORT)'):
            self.assertIn(key, model)
        self.assertIn('OpexC70RecomputeFactors(this._lines)', source("persist.nut"))

    def test_only_head_flip_log_and_actual_attempt_tag(self):
        observe = fn(source("projects_selection.nut"), "OpexP4FlipObserve")
        self.assertIn('selected[0] != actual', observe)
        self.assertIn('if (lh == sh)', observe)
        self.assertIn('if (lt != st || OpexProjectIsForcedChain(lh)', observe)
        self.assertIn('P4_FLIP_HEAD id=', observe)
        self.assertIn('legacy_denom=', observe)
        projects = source("task_projects.nut")
        mark = projects.index('P4_FLIP_ATTEMPT id=')
        self.assertLess(projects.index('if (C80_MARGINAL_FLOOR)'), mark)
        self.assertLess(mark, projects.index('local mode = project.mode;', mark))
        self.assertIn('!SCORE_P4_FLIP_LAST.attempted', projects)
        self.assertIn('OpexC82ProjectEngine(p)', fn(source('projects_selection.nut'), 'OpexP4FlipProjectKey'))

    def test_bounded_annual_coverage_and_mismatch_are_visible(self):
        report = source('task_report.nut')
        self.assertIn('P4_FLIP_SUMMARY report_year=', report)
        for field in ('selects=', 'verified=', 'skipped=', 'mismatch=', 'head_changes=', 'attempts='):
            self.assertIn(field, report)
        observe = fn(source('projects_selection.nut'), 'OpexP4FlipObserve')
        self.assertIn('SCORE_P4_FLIP_SELECTS++', observe)
        self.assertIn('SCORE_P4_FLIP_MISMATCHES++', observe)
        self.assertIn('P4_FLIP_CONTRACT mismatch=active_head', observe)

    def test_possible_flip_between_same_tier_affordable(self):
        rows = [candidate('rail', 'rail', 100, stable=2, legacy=.5),
                candidate('air', 'air', 100, stable=.5, legacy=2)]
        self.assertEqual(rank_fixture(rows, stable=False)[0], 'air')
        self.assertEqual(rank_fixture(rows, stable=True)[0], 'rail')

    def test_c77_overrides_scores_and_v88_override(self):
        rows = [candidate('rail', 'rail', 1000, tier=0),
                candidate('defensive', 'air', 10, tier=2)]
        self.assertEqual(rank_fixture(rows, stable=False)[0], 'defensive')
        rows.append(candidate('chain', 'rail', 5, tier=0, forced=True))
        self.assertEqual(rank_fixture(rows, stable=False)[0], 'chain')

    def test_early_slot_bonus_and_revenue_tie_break(self):
        rows = [candidate('air', 'air', 95), candidate('rail', 'rail', 100)]
        self.assertEqual(rank_fixture(rows, stable=False)[0], 'rail')
        self.assertEqual(rank_fixture(rows, stable=False, bonus=10)[0], 'air')
        tied = [candidate('low', 'rail', 100, revenue=10), candidate('high', 'rail', 100, revenue=20)]
        self.assertEqual(rank_fixture(tied, stable=False)[0], 'high')

    def test_od_dedup_cash_floor_and_zero_profits(self):
        rows = [candidate('cheap', 'air', 100, pair='OD', denom=100),
                candidate('expensive', 'air', 110, pair='OD', denom=150),
                candidate('cash', 'rail', 10000, affordable=False),
                candidate('floor', 'rail', 10000, floor=False)]
        self.assertEqual(rank_fixture(rows, stable=False, dedup=True), ['cheap'])
        self.assertEqual(rank_fixture([candidate('bad', 'rail', -100)], stable=False), ['bad'])

    def test_observed_and_engine_bypass_p4(self):
        rows = [candidate('observed', 'air', 100, legacy=.1, stable=10, observed=True),
                candidate('engine', 'air', 100, legacy=.1, stable=10, engine=True)]
        self.assertEqual(rank_fixture(rows, stable=False), rank_fixture(rows, stable=True))


if __name__ == '__main__':
    unittest.main()
