import unittest

from analyse_air_fleet_reselect_early4 import parse


class AirFleetReselectAnalysisTests(unittest.TestCase):
    def test_reselect_is_attributed_to_closing_task_only(self):
        lines = [
            '[script:4] [0] [I] OPEX 1973-3-19 SELECTION_LIGHT path=reselect ops=100',
            '[script:4] [0] [I] OPEX 1973-3-19 SCHED_IDLE t=air_fleet w=0 r=air_fleet_no_work op=250',
            '[script:4] [0] [I] OPEX 1973-3-20 SELECTION_LIGHT path=reselect ops=150',
            '[script:4] [0] [I] OPEX 1973-3-20 SCHED_IDLE t=projects w=1 r=projects_useful op=400',
        ]
        result, leftovers = parse(lines)
        self.assertEqual(leftovers, 0)
        self.assertEqual(result['1973']['air_fleet']['reselect_ops'], 100)
        self.assertEqual(result['1973']['projects']['reselect_ops'], 150)
        self.assertEqual(result['1973']['air_fleet']['reselect_calls'], 1)

    def test_oversized_and_cross_year_are_not_hidden(self):
        lines = [
            '[script:4] [0] [I] OPEX 1972-12-31 SELECTION_LIGHT path=reselect ops=10',
            '[script:4] [0] [I] OPEX 1973-1-1 SELECTION_LIGHT path=reselect ops=200',
            '[script:4] [0] [I] OPEX 1973-1-1 SCHED_IDLE t=air_fleet w=0 op=100',
        ]
        report, left = parse(lines)
        self.assertEqual(left, 1)
        self.assertEqual(report['1973']['air_fleet']['oversized_attributions'], 1)


if __name__ == '__main__':
    unittest.main()
