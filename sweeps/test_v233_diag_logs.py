import tempfile
from pathlib import Path
import unittest

from v233_diag_logs import audit, events, ratio


class OfflineLogTests(unittest.TestCase):
    def test_owner_and_physical_line_numbers(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'trace.log'
            path.write_text('[0] OPEX 1970-1-2 TEST n=9\n'
                            '[1] OPEX 1970-1-2 TEST n=10\n', encoding='utf-8')
            parsed = events(path)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['_line'], 1)
        self.assertEqual(parsed[0]['_date'], '1970-01-02')
        self.assertEqual(parsed[0]['n'], '9')

    def test_counterfactual_has_no_lookahead_and_unknown_stays_unknown(self):
        rows = [dict(_event='V233_YIELD', factory='3', cargo='5', air_yield='unknown'),
                dict(_event='V233_CHAIN', state='candidate', factory='3',
                     allowed='false', **{'yield': '0.8'}),
                dict(_event='B6_PORTFOLIO', actual_mode='air', actual_profit='50', actual_cap='100'),
                dict(_event='V233_CHAIN', state='candidate', factory='3',
                     allowed='false', **{'yield': '0.8'}),
                dict(_event='B6_PORTFOLIO', actual_mode='air', actual_profit='500', actual_cap='100')]
        result = audit(rows)
        self.assertIsNone(result['candidates'][0]['last_model'])
        self.assertEqual(result['counts']['last_model_covered'], 1)
        self.assertEqual(result['counts']['last_model_passes'], 1)
        self.assertEqual(result['candidates'][1]['last_model']['rate'], .5)
        self.assertEqual(result['candidates'][1]['best_model']['rate'], .5)

    def test_missing_or_zero_capital_is_not_a_zero_yield(self):
        self.assertIsNone(ratio({}, 'p', 'k'))
        self.assertIsNone(ratio(dict(p=5, k=0), 'p', 'k'))
        self.assertEqual(ratio(dict(p=0, k=100), 'p', 'k'), 0)


if __name__ == '__main__':
    unittest.main()
