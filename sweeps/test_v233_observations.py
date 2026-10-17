"""E2 static contracts: monthly sampling and the optional integer-only save schema."""
import unittest
from test_v233_contracts import AI
from test_c45_subsidy_persistence import function_body


class GoodsObservations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (AI / "goods_v233.nut").read_text()
        cls.persist = (AI / "persist.nut").read_text()

    def test_zero_duplicate_missing_month_and_threshold_contracts(self):
        sample = function_body(self.text, 'function OpexV233Sample(row, month, quantity)')
        self.assertLess(sample.index('if (row.lastMonth == month) return false;'),
                        sample.index('row.count ='))
        self.assertIn('if (row.lastMonth != month - 1)', sample)
        self.assertIn('row.count = 0;', sample)
        self.assertIn('row.q0 = quantity;', sample)
        self.assertNotIn('quantity > 0', sample)
        eligible = function_body(self.text, 'function OpexV233Quantity(row, month)')
        self.assertIn('row.count != 3 || row.lastMonth != month', eligible)
        for token in ('row.q0', 'row.q1', 'row.q2', 'q >= V233_GOODS_MIN_MONTHLY'):
            self.assertIn(token, eligible)
        self.assertIn('const V233_GOODS_MIN_MONTHLY = 64;', (AI / 'globals_pre.nut').read_text())

    def test_bounded_independent_monthly_observation(self):
        self.assertIn('work.month != month', self.text)
        self.assertIn('n < 8 && work.lineCursor < this._lines.len()', self.text)
        self.assertEqual(self.text.count('AIIndustry.GetLastMonthProduction('), 1)
        self.assertIn('work.keys[work.cursor++]', self.text)
        for banned in ('predCarried', 'OpexMakeCandidate(', 'OpexProjectRememberAll('):
            self.assertNotIn(banned, self.text)
        self.assertIn('global_output=', self.text)
        self.assertIn('AICargo.TE_GOODS', self.text)

    def test_identity_and_station_coverage_not_tile_as_id(self):
        support = function_body(self.text, 'function OpexV233Support(line)')
        for token in ('OpexLineStationId(line, "B")', 'AIIndustry.IsValidIndustry',
                      'AICompany.IsMine', 'AICargoList_StationAccepting', 'line.scrapping'):
            self.assertIn(token, support)
        self.assertIn('OpexV207PlatformUnionValue(support.line.platformB, cargo', self.text)
        self.assertIn('saved.factoryTile == support.factoryTile && saved.stationTile == support.stationTile', self.text)

    def test_short_full_save_and_legacy_load_without_api(self):
        save = function_body(self.persist, 'function OpexAI::Save()')
        for obj in ('shortSave', 'saveObj'):
            self.assertIn(f'{obj}.v233GoodsObservations <- OpexV233SaveObservations', save)
        load = function_body(self.persist, 'function OpexAI::Load(version, data)')
        self.assertIn('if ("v233GoodsObservations" in data)', load)
        codec = function_body(self.text, 'function OpexV233LoadObservations(data)')
        self.assertNotIn('AIIndustry.', codec)
        self.assertNotIn('AIStation.', codec)
        self.assertIn('tuple.len() != 10', codec)
        self.assertIn('typeof value != "integer"', codec)
        self.assertIn('tuple[9] < 1 || tuple[9] > 3', codec)
        self.assertIn('data.version != 1', codec)
        reconcile = function_body(self.persist, 'function OpexAI::_reconcileAfterLoad()')
        self.assertLess(reconcile.index('this._lines = liveLines;'),
                        reconcile.index('this._v233GoodsWork = null;'))
        self.assertIn('this._lines.len() == 0) this._v233GoodsObservations = null;', reconcile)


if __name__ == '__main__':
    unittest.main()
