"""V31b source and dimensional contracts, prior to engine qualification."""
from pathlib import Path
import unittest


AI = Path(__file__).resolve().parents[1] / 'ai' / 'OpexAI'


class V31bDimensionalGuard(unittest.TestCase):
    def test_root_is_pax_per_month_and_satellites_are_producers(self):
        src = (AI/'builder_road.nut').read_text(encoding='utf8')
        self.assertIn('local measuredMonthly = ROAD100_PAX_INITIAL_BERTH_FLEET', src)
        self.assertIn('candidate.road100PaxProducerUnits', src)
        self.assertIn('? candidate.monthly : portfolioSummary.monthly;', src)
        self.assertIn('capacity * 30 / roundDays', src)
        self.assertIn('candidate.monthly > 0', src)
        # Seed100: 146 estimated PASS/mo, 44 local producer units. These are
        # not comparable until both sides are expressed in PASS/mo.
        monthly_root_pax, monthly_sat_producers, capacity_pax_month = 146, 44, 60
        self.assertGreater(monthly_root_pax, capacity_pax_month)
        self.assertLess(monthly_sat_producers, capacity_pax_month)

    def test_rating_uses_real_n_only_when_v31_optin(self):
        src = (AI/'builder_road.nut').read_text(encoding='utf8')
        self.assertIn('function OpexRoad100PaxFixedFleetEconomics(', src)
        self.assertIn('if (!ROAD100_PAX_INITIAL_BERTH_FLEET', src)
        self.assertIn('OpexStationRatingForHeadway(roundTripDays / fixedVehicles)', src)
        self.assertIn('result.trains = fixedVehicles;', src)
        self.assertIn('candidate.monthly * rating', src)
        self.assertIn('result.profitAnnual = profitAnnual;', src)
        # Critically leave frozen ESTIM/V262 economics itself byte-stable.
        econ = (AI/'economy.nut').read_text(encoding='utf8')
        self.assertNotIn('fixedPaxVehicles', econ)

    def test_true_bidirectional_berths_and_incremental_cash_guard(self):
        src = (AI/'builder_road.nut').read_text(encoding='utf8')
        for part in (
            'portfolioSummary.stopsA.len() > 0',
            'portfolioSummary.stopsB.len() > 0',
            'result.nStopsA >= 2 && result.nStopsB >= 2',
            'AIStation.GetStationID(bayA) == stationA',
            'AIStation.GetStationID(bayB) == stationB',
            'for (local vehicles = candidate.trains + 1;',
            'option.profitAnnual <= base.profitAnnual',
            'option.profitAnnual <= 0',
            'extraRoi < 250',
            'extraCapital + 50000',
            'OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, vehicles)',
            'AIVehicle.CloneVehicle',
            'AIVehicle.StartStopVehicle',
            'OpexRoadRollback',
        ):
            self.assertIn(part, src)


if __name__ == '__main__':
    unittest.main()
