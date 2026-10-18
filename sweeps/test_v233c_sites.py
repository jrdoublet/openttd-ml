"""SITEB source contracts and read-only log fixtures; no Squirrel execution."""
import unittest

from analyze_v233_sites import analyze_sites
from test_v233b_exposure import body


class SiteLogs(unittest.TestCase):
    def test_result_is_not_always_a_build_and_missing_fields_stay_missing(self):
        result = analyze_sites([
            'OPEX 1971-1-1 V233_GRAFT state=result built=0 reason=SITEB error=0',
            'OPEX 1971-1-1 V233_GRAFT state=result built=1 reason=OK error=0',
            'OPEX 1971-1-1 V233_GRAFT state=site_rejected clearB=100 commandB=0',
            'OPEX 1971-1-1 V233_DELIVERY state=first_observed_since_load factory=2',
        ])
        self.assertEqual(result['counts']['result'], 2)
        self.assertEqual(result['counts']['built'], 1)
        self.assertEqual(result['rejections'][0]['line'], 3)
        self.assertNotIn('cargoB', result['rejections'][0])
        self.assertNotIn('best_acceptanceB', result['rejections'][0])
        self.assertEqual(len(result['deliveries']), 1)

    def test_site_details_survive_parsing(self):
        result = analyze_sites(['OPEX 1971-1-1 V233_GRAFT state=site_rejected '
                                'tilesB=100 triedB=400 cargoB=0 lastB=acceptance '
                                'best_acceptanceB=7 errorB=0'])
        self.assertEqual(result['rejections'][0]['best_acceptanceB'], '7')
        self.assertEqual(result['rejections'][0]['lastB'], 'acceptance')


class SiteContracts(unittest.TestCase):
    def test_full_rectangle_instead_of_max_or_sum_of_overlapping_catchments(self):
        acceptance = body('goods_v233.nut', 'function OpexV233TownAcceptance(')
        self.assertIn('horizontal ? p.length : 1, horizontal ? 1 : p.length, coverage', acceptance)
        self.assertEqual(acceptance.count('GetCargoAcceptance('), 1)
        self.assertNotIn('for (', acceptance)
        finder = body('goods_v233.nut', 'function OpexV233TownPlans(')
        for token in ('local radius = STATION_SEARCH_RADIUS', 'r <= radius', 'AIRail.RAILTRACK_NE_SW',
                      'AIRail.RAILTRACK_NW_SE', 'sign += 2', 'SLOPE_FLAT',
                      '!joining && acceptance < 8', 'stationId != AIStation.STATION_NEW', 'AITestMode()',
                      'AIAccounting()', 'AIError.GetLastError()', 'stats.nCargo++',
                      'stats.bestAcceptance = acceptance', 'AIMap.DistanceManhattan'):
            self.assertIn(token, finder)
        self.assertLess(finder.index('acceptance < 8'), finder.index('AIRail.BuildRailStation('))
        self.assertIn('if (DECISION_LOG && !joining) unionOnly = OpexRailPlatformCargoValue', finder)
        self.assertIn('if (DECISION_LOG && unionOnly) OpexDecide("V233_SITE"', finder)
        self.assertGreater(finder.index('state=union_recovered'), finder.index('if (!ok)'))

    def test_validation_matches_search_only_for_mode_two_graft_destination(self):
        validate = body('task_rail.nut', 'function OpexV131PlatformCargoOk(')
        self.assertIn('V233_GOODS_GRAFT && (V233_GOODS_POLICY == 2 || V233_GOODS_POLICY == 3) && OpexV233IsGraft(candidate) && !wantProduction', validate)
        self.assertIn('return OpexV233TownAcceptance(p, candidate.cargo, coverage) >= 8;', validate)
        self.assertIn('OpexRailPlatformCargoValue(', validate)
        for signature in ('function OpexV233SpendAllowed(', 'function OpexAI::_v233PlanStep('):
            # Both the sliced stock check and the final spending check keep the cargo guard.
            text = body('goods_v233.nut', signature)
            self.assertIn('OpexV131PlatformCargoOk(plan.planB', text)

    def test_rejection_has_attempts_acceptance_and_native_error(self):
        generate = body('goods_v233.nut', 'function OpexAI::_v233GraftStep(')
        for field in ('cargoB=', 'tilesB=', 'triedB=', 'lastB=', 'errorB=', 'best_acceptanceB='):
            self.assertIn(field, generate)


if __name__ == '__main__':
    unittest.main()
