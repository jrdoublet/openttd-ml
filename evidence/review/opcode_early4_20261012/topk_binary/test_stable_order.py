"""Top-K order contract: transitive default comparator with stable ties.

This test deliberately uses a stable reference sorting oracle rather than
translating the historical insertion loop into Python.
"""
from pathlib import Path
import random
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def insert_upper_bound(items, row, limit):
    lo, hi = 0, len(items)
    key = (row[0], row[1], row[2])
    while lo < hi:
        mid = (lo + hi) // 2
        if items[mid][:3] >= key:
            lo = mid + 1
        else:
            hi = mid
    items.insert(lo, row)
    if len(items) > limit:
        items.pop()


class TopKContractTests(unittest.TestCase):
    def test_binary_preserves_stable_order_and_tail_truncation(self):
        rng = random.Random(121)
        for limit in (1, 3, 20, 64):
            for n in (0, 1, 3, 20, 100, 800):
                stream = [(rng.randrange(4), rng.randrange(13) / 4.0,
                           rng.randrange(11), i) for i in range(n)]
                actual = []
                for x in stream:
                    insert_upper_bound(actual, x, limit)
                expected = sorted(stream, key=lambda a: a[:3], reverse=True)[:limit]
                self.assertEqual(actual, expected, (limit, n))

    def test_source_guard_and_settings(self):
        ai = ROOT/'ai'/'OpexAI'
        info = (ai/'info.nut').read_text(encoding='utf8')
        settings = (ai/'settings.nut').read_text(encoding='utf8')
        globals_pre = (ai/'globals_pre.nut').read_text(encoding='utf8')
        selection = (ai/'projects_selection.nut').read_text(encoding='utf8')
        for setting in ('p0_topk_binary', 'p0_topk_binary_check'):
            declaration = info[info.index('name = "'+setting+'"'):]
            self.assertRegex(declaration[:300], r'easy_value = 0, medium_value = 0, hard_value = 0')
            self.assertIn('custom_value = 0', declaration[:300])
            self.assertIn('GetSetting("'+setting+'")', settings)
        self.assertIn('P0_TOPK_BINARY <- false', globals_pre)
        self.assertIn('P0_TOPK_BINARY_CHECK <- false', globals_pre)
        candidate = selection[selection.index('function OpexP0TopKInsert('):]
        for special in ('C118_AIR_TERRITORIAL_EXPANSION',
                        'C122_AIR_REGIME_PRIORITY', 'C122_AIR_REGIME_SHADOW',
                        'AIR_EFFICIENCY_DEDUPE', 'PROBE_SELECT_REJECT'):
            self.assertIn(special, candidate[:1150])
        self.assertIn('return; /* check force TOUJOURS le resultat historique */', candidate)
        # Outside the select.full fallback, no post-score reordering changed.
        self.assertEqual(len(re.findall(r'OpexP0TopKInsert\(affordable, project, scoreKey',selection)), 2)


if __name__ == '__main__':
    unittest.main()
