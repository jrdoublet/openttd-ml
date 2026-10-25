"""Offline guardrails; synthetic fixtures, no economic qualification."""
import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest

import analyze_v216 as a


def rail():
    return {'role': 'ranked', 'rank': 0, 'key': 'rail', 'affordable': 1,
            'tier': 0, 'p.mode': 'rail', 'p.kind': 'pax', 'p.revenueAnnual': 100,
            'p.profitAnnual': 20, 'fund_profit': 10, 'select_score': 40,
            'g.a_gain_pct': 50, 'g.b_gain_pct': 50}


def game(rows=None, count=2):
    air = {'role': 'ranked', 'rank': 1, 'key': 'air', 'affordable': 1,
           'tier': 0, 'p.mode': 'air', 'p.kind': 'pax', 'fund_profit': 5,
           'select_score': 15}
    return {'name': 'fixture', 'select': {1: {'date': '1971-1-1', 'ranked': count}},
            'decomp': {1: [rail(), air] if rows is None else rows}}


class TestFixedCostShadow(unittest.TestCase):
    def test_costs_do_not_disappear_with_demand(self):
        result = a.rail_pax_fixed_cost_shadow(rail())
        self.assertEqual(result['revenue'], 50)
        self.assertEqual(result['costs'], 80)
        self.assertEqual(result['raw_profit'], -30)
        self.assertEqual(result['fund_profit'], -15)  # calibration 0.5 retained
        self.assertEqual(result['score'], 0)

    def test_identity_and_zero_revenue(self):
        r = rail()
        r.update({'g.a_gain_pct': 100, 'g.b_gain_pct': 100})
        s = a.rail_pax_fixed_cost_shadow(r)
        self.assertEqual((s['raw_profit'], s['fund_profit'], s['score']), (20, 10, 40))
        r.update({'g.a_gain_pct': 0, 'g.b_gain_pct': 0})
        self.assertEqual(a.rail_pax_fixed_cost_shadow(r)['raw_profit'], -80)

    def test_positive_margin_score_scales_after_costs(self):
        r = rail()
        r.update({'g.a_gain_pct': 90, 'g.b_gain_pct': 90})
        s = a.rail_pax_fixed_cost_shadow(r)
        self.assertEqual((s['raw_profit'], s['fund_profit'], s['score']), (10, 5, 20))

    def test_missing_and_nonfinite_are_unknown(self):
        for key in ('p.revenueAnnual', 'p.profitAnnual', 'fund_profit', 'select_score',
                    'g.a_gain_pct', 'g.b_gain_pct'):
            for bad in (None, float('nan'), float('inf'), 'absent', True):
                with self.subTest(key=key, bad=bad):
                    r = rail()
                    r[key] = bad
                    self.assertIsNone(a.rail_pax_fixed_cost_shadow(r))
            r = rail()
            del r[key]
            self.assertIsNone(a.rail_pax_fixed_cost_shadow(r))

    def test_unsupported_cases_are_unknown(self):
        for key, value in (('c.revenue2', 10), ('c.carried2', 1),
                           ('p.revenueAnnual', 19), ('p.profitAnnual', 0),
                           ('g.a_gain_pct', 101), ('g.b_gain_pct', -1)):
            with self.subTest(key=key):
                r = rail()
                r[key] = value
                self.assertIsNone(a.rail_pax_fixed_cost_shadow(r))


class TestRankSensitivity(unittest.TestCase):
    def test_negative_margin_removes_rail_without_mutation(self):
        g = game()
        before = copy.deepcopy(g)
        result = a.fixed_cost_rank_sensitivity([g])
        self.assertEqual(g, before)
        self.assertEqual(result['total_selections'], 1)
        self.assertEqual(result['changed_selections'], 1)
        self.assertEqual(result['replacements'], {('rail/pax', 'air/pax'): 1})
        change = result['detailed_changes'][0]
        self.assertEqual((change['orig_score'], change['new_score']), (40, 15))
        self.assertFalse(result['purchase_replay_complete'])

    def test_no_replacement_can_be_reported(self):
        result = a.fixed_cost_rank_sensitivity([game([rail()], 1)])
        self.assertEqual(result['replacements'], {('rail/pax', 'none'): 1})

    def test_truncated_unknown_not_unchanged(self):
        g = game(count=3)
        result = a.fixed_cost_rank_sensitivity([g])
        self.assertEqual(result['observed_selections'], 1)
        self.assertEqual(result['total_selections'], 0)
        self.assertEqual(len(result['unknown_selections']), 1)
        g['select'][1].pop('ranked')
        self.assertEqual(len(a.fixed_cost_rank_sensitivity([g])['unknown_selections']), 1)

    def test_missing_ghost_blocks_whole_selection(self):
        g = game()
        del g['decomp'][1][0]['g.b_gain_pct']
        r = a.fixed_cost_rank_sensitivity([g])
        self.assertEqual(r['total_selections'], 0)
        self.assertEqual(r['unknown_selections'][0]['reason'], 'missing_or_unsupported_economics')

    def test_unranked_affordable_not_promoted(self):
        g = game()
        extra = dict(rail(), role='affordable', rank=-1, key='unadmitted', select_score=99999)
        g['decomp'][1].append(extra)
        self.assertEqual(a.fixed_cost_rank_sensitivity([g])['detailed_changes'][0]['new_key'], 'air')

    def test_duplicate_rank_is_unknown(self):
        g = game()
        g['decomp'][1][1]['rank'] = 0
        self.assertEqual(a.fixed_cost_rank_sensitivity([g])['total_selections'], 0)

    def test_baseline_mismatch_is_not_a_correction_gain(self):
        g = game()
        g['decomp'][1][1]['select_score'] = 100
        r = a.fixed_cost_rank_sensitivity([g])
        self.assertEqual(r['total_selections'], 0)
        self.assertEqual(r['unknown_selections'][0]['reason'], 'baseline_order_not_reproduced')

    def test_new_top_tie_is_indeterminate(self):
        g = game()
        g['decomp'][1][0].update({'g.a_gain_pct': 87, 'g.b_gain_pct': 88})
        r = a.fixed_cost_rank_sensitivity([g])
        self.assertEqual(r['total_selections'], 0)
        self.assertEqual(r['unknown_selections'][0]['reason'], 'ambiguous_top_tie')

    def test_cli_labels_analysis_as_conditional(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = game()
            pre = '[test] OPEX 1971-1-1 '
            lines = [pre + 'V216_SELECT seq=1 ranked=2']
            lines += [pre + 'V216_DECOMP seq=1 ' + ' '.join(f'{k}={v}' for k, v in r.items())
                      for r in g['decomp'][1]]
            (Path(tmp) / 'ref_seed42_r0.log').write_text('\n'.join(lines), encoding='utf-8')
            # Existing argument parser supports relative paths on Windows.
            import os
            previous = os.getcwd()
            try:
                os.chdir(tmp)
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    a.main(['.', 'ref'])
            finally:
                os.chdir(previous)
        output = stream.getvalue()
        self.assertIn('hors rejeu des achats', output)
        self.assertIn('sélections calculables : 1', output)
        self.assertIn('INCOMPLETE', output)


if __name__ == '__main__':
    unittest.main()
