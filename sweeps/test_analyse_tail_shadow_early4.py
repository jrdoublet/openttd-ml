import tempfile
import unittest
from pathlib import Path

from analyse_tail_shadow_early4 import read_log


class TailShadowReaderTests(unittest.TestCase):
    def test_annual_hook_cost_and_readiness_reconciliation(self):
        content = '\n'.join([
            '[script:4] [0] [I] LOOP_OPS y=1970 post=sleep_left n=3 ops=15000 tk=0 max=9000',
            '[script:4] [0] [I] LOOP_OPS y=1970 post=sleep_cap3k_none n=2 ops=7000 tk=0 max=4000',
            '[script:4] [0] [I] LOOP_OPS y=1970 post=tail_shadow n=3 ops=330 tk=1 max=170',
            '[script:4] [0] [I] TAIL_SHADOW y=1970 kind=total high=2 low=1 crosses=0 guard_ops=150 guard_max=100 before_cap=7000 after_cap=6500 unknown=1 other=0',
            '[script:4] [0] [I] TAIL_SHADOW y=1970 kind=bucket state=none|rail_none|rq_no|c67_off n=1 cap=4000 cap_after=3600 guard_ops=100 crosses=0 rq_sum=0 rq_max=0',
            '[script:4] [0] [I] TAIL_SHADOW y=1970 kind=bucket state=regen n=1 cap=3000 cap_after=2900 guard_ops=50 crosses=0 rq_sum=0 rq_max=0',
        ])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'log.txt'
            path.write_text(content,encoding='utf8')
            data, duplicate = read_log(path)
        year = data['1970']
        self.assertEqual(duplicate,0)
        self.assertEqual(year['shadow_ops'],330)
        self.assertEqual(year['shadow_ticks_crossed'],1)
        self.assertEqual(year['raw_cap'],7000)
        self.assertEqual(year['total']['after_cap'],6500)
        self.assertEqual(year['unknown_after_cap'],2900)
        self.assertEqual(year['none_after_cap'],3600)
        self.assertTrue(year['valid_sample_accounting'])


if __name__ == '__main__':
    unittest.main()
