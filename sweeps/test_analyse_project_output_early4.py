import unittest

from analyse_project_output_early4 import parse


class ProjectOutputTests(unittest.TestCase):
    def test_does_not_double_count_search_replays(self):
        events = [
            '[script:4] [0] [I] OPEX 1973-5-2 P5_RAIL_SEARCH id=1 ops=1500 days=2 outcome=OK result=found',
            '[script:4] [0] [I] OPEX 1973-5-3 P5_RAIL_SEARCH id=2 ops=0 days=0 outcome=OK result=found',
            '[script:4] [0] [I] OPEX 1973-5-4 P5_BUILD_LINE id=10 mode=rail src=12 dst=13',
            '[script:4] [0] [I] OPEX 1973-5-5 P5_BUILD_LINE id=10 mode=rail src=13 dst=14',
        ]
        stats = parse(events)['1973']
        self.assertEqual(stats['search_calls'], 2)
        self.assertEqual(stats['search_paid_calls'], 1)
        self.assertEqual(stats['search_window_ops'], 1500)
        self.assertEqual(stats['lines_by_mode']['rail'], 2)
        self.assertEqual(stats['unique_mode_src_dst'], 2)
        self.assertEqual(stats['lines_by_month']['5']['rail'], 2)


if __name__ == '__main__':
    unittest.main()
