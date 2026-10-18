"""Read-only log analysis fixtures and V233b source integration contracts."""
import unittest

from analyze_v233_exposure import analyze_lines
from test_v233_contracts import AI
from test_c45_subsidy_persistence import function_body


def body(file, name):
    return function_body((AI / file).read_text(), name)


class ExposureAnalysis(unittest.TestCase):
    def test_continuation_window_excludes_next_task_and_reference_causality(self):
        result = analyze_lines([
            'OPEX 1971-1-1 TASK name=projects',
            'OPEX 1971-1-1 V233_SEARCH state=continue mode=rail rank=0 built=0',
            'OPEX 1971-1-1 V233_BUILD mode=fleet rank=1 key=fleet|3',
            'OPEX 1971-1-1 TASK name=air_fleet',
            'OPEX 1971-1-1 V233_BUILD mode=air rank=2 key=air|4',
        ])
        self.assertEqual(result['counts']['continued_windows_with_build'], 1)
        self.assertEqual(result['counts']['continued_build_fleet'], 1)
        self.assertNotIn('continued_build_air', result['counts'])
        self.assertEqual(result['counts']['builds_rank_gt_zero'], 2)

    def test_failure_is_matched_to_pair_and_preserves_error(self):
        lines = ['OPEX 1971-1-1 RAIL_ATTEMPT src=10 dst=20 reason=SITEAB error=0',
                 'OPEX 1971-1-1 V233_DROP reason=build_failed key=freight|5|10|20|3 factory=7']
        result = analyze_lines(lines)
        self.assertEqual(result['failures'][0]['attempt']['reason'], 'SITEAB')
        self.assertEqual(result['failures'][0]['attempt']['error'], '0')
        lines[1] = lines[1].replace('|10|20|', '|11|20|')
        with self.assertRaises(ValueError):
            analyze_lines(lines)

    def test_real_zero_and_missing_month_and_low_but_positive_output(self):
        def obs(month, quantity, count):
            return (f'OPEX 1971-1-1 V233_OBS factory=1 cargo=5 station=3 month={month} '
                    f'global_output={quantity} count={count}')
        result = analyze_lines([obs(1, 0, 1), obs(2, 96, 2), obs(3, 96, 3),
                                obs(5, 300, 1), obs(6, 0, 2), obs(7, 0, 3)])
        self.assertEqual(result['counts']['full_windows'], 2)
        self.assertEqual(result['counts']['strict_windows'], 0)
        self.assertEqual(result['counts']['mean_windows'], 2)
        with self.assertRaises(ValueError):
            analyze_lines([obs(1, 0, 1), obs(1, 99, 1)])


class V233bContracts(unittest.TestCase):
    def test_mode_two_is_integer_default_off_and_not_an_extra_setting(self):
        setting = (AI / 'info.nut').read_text().split('name = "v233_goods_graft"', 1)[1].split('});', 1)[0]
        self.assertIn('max_value = 3', setting)
        self.assertNotIn('AICONFIG_BOOLEAN', setting)
        for level in ('easy', 'medium', 'hard', 'custom'):
            self.assertIn(f'{level}_value = 0', setting)
        settings = (AI / 'settings.nut').read_text()
        self.assertIn('V233_GOODS_POLICY = AIController.GetSetting("v233_goods_graft");', settings)
        quantity = body('goods_v233.nut', 'function OpexV233Quantity(')
        self.assertIn('row.count != 3 || row.lastMonth != month', quantity)
        self.assertIn('if (V233_GOODS_POLICY == 2) q = (row.q0 + row.q1 + row.q2) / 3;', quantity)
        self.assertIn('q >= V233_GOODS_MIN_MONTHLY', quantity)
        live = body('goods_v233.nut', 'function OpexAI::_v233CandidateLive(')
        self.assertIn('observedQuantity < candidate.monthly', live)

    def test_shorter_strict_join_and_feasible_town_before_preference(self):
        sites = body('goods_v233.nut', 'function OpexV233PlatformPlans(')
        for token in ('length--', 'OpexRailMinimumPlatformLength()', 'OpexJoinPlatformPlans(',
                      'OpexV233FactoryCovered(', 'p.stationId <- candidate.joinStationId',
                      'OpexV233TownPlans(candidate.dst', 'reason = OpexRailSiteReason'):
            self.assertIn(token, sites)
        self.assertNotIn('OpexStationPlans(candidate.src', sites)
        generate = body('goods_v233.nut', 'function OpexAI::_v233GraftStep(')
        self.assertLess(generate.index('sites.reason != "OK"'), generate.index('candidate.roi > state.preferred.roi'))
        builder = body('builder_rail.nut', 'function OpexRailPlatformPlans(')
        self.assertIn('V233_GOODS_GRAFT && (V233_GOODS_POLICY == 2 || V233_GOODS_POLICY == 3) && OpexV233IsGraft(candidate)', builder)

    def test_synchronous_search_cannot_bypass_stock_or_reprice_missing_entry(self):
        attempt = body('task_rail.nut', 'function OpexAI::_tryBuildRailProject(')
        sync = attempt.split('if (v233Graft && start.plan != null && start.plan.ok)', 1)[1].split('candidate.railPlan <- start.plan', 1)[0]
        self.assertIn('this._v233StorePlan(candidate, start.plan);', sync)
        self.assertIn('return { outcome = "rejected"', sync)
        self.assertNotIn('OpexBuildLine', sync)

    def test_graft_abandonment_uses_explicit_town_not_invalid_industry_sentinel(self):
        key = body('lines.nut', 'function OpexAbandonedPairKey(')
        self.assertIn('if (V233_GOODS_GRAFT && OpexV233IsGraft(candidate))', key)
        self.assertIn('candidate.v233FactoryId + "|t" + candidate.dstTown', key)
        self.assertLess(key.index('candidate.dstTown'), key.index('AIIndustry.GetIndustryID(candidate.dst)'))

    def test_conversion_and_delivery_logs_are_guarded_and_transient(self):
        task = body('task_projects.nut', 'function OpexAI::_tryBuildProjects(')
        self.assertEqual(task.count('if (DECISION_LOG && V233_PENDING_CONTINUE) OpexV233TraceAttempt'), 5)
        self.assertIn('slot_skipped=', task)
        self.assertIn('built_after=', task)
        delivery = body('goods_v233.nut', 'function OpexAI::_v233DeliveryStep(')
        for token in ('!DECISION_LOG || !V233_GOODS_GRAFT', 'AICargoList_StationAccepting',
                      'AIOrder.OF_TRANSFER', 'witness.loads[vehicle] > quantity',
                      'AIStation.GetStationID(tile) == station', 'AIVehicle.VS_AT_STATION',
                      'state=first_observed_since_load'):
            self.assertIn(token, delivery)
        self.assertNotIn('GetProfit', delivery)
        persist = (AI / 'persist.nut').read_text()
        self.assertIn('this._v233DeliveryProbe = null;', body('persist.nut', 'function OpexAI::Load('))
        self.assertNotIn('_v233DeliveryProbe', body('persist.nut', 'function OpexAI::Save('))


if __name__ == '__main__':
    unittest.main()
