import unittest

from analyse_project_admission_early4 import inspect


class AdmissionTests(unittest.TestCase):
    def test_p2_vs_p5_exposes_post_dispatch_snapshot(self):
        lines = [
            '[script:4] [0] [I] OPEX 1972-2-3 P2_PASS pass=1 in_best=0 n_built=0 stop=empty_pool post_best=0',
            '[script:4] [0] [I] OPEX 1972-2-3 P5_RAIL_PASS pass=1 alts=12 rail_alts=9 rail_aff=1 rail_in_best=0 rail_built=0',
            '[script:4] [0] [I] OPEX 1972-3-3 P2_PASS pass=2 in_best=3 n_built=1 stop=list_end post_best=0',
            '[script:4] [0] [I] OPEX 1972-3-3 P5_WAIT_START id=1 alts=20 n_rail=8',
            '[script:4] [0] [I] OPEX 1973-1-1 P2_RESOLVE id=1 days=290 ret_reason=catalog_fresh ret_task=catalog funded=2',
        ]
        x = inspect(lines)
        self.assertEqual(x['1972']['passes'], 2)
        self.assertEqual(x['1972']['post_empty'], 2)
        self.assertEqual(x['1972']['rail_fundable_after'], 1)
        self.assertEqual(x['1972']['wait_started'], 1)
        self.assertEqual(x['1973']['wait_resolved'], 1)
        self.assertEqual(x['1973']['wait_days_total'], 290)


if __name__ == '__main__':
    unittest.main()
