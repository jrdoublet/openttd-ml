import tempfile
import csv
from pathlib import Path
import unittest

from v249_effect import baseline, events, stats, write_statues_csv


class StatueEvidence(unittest.TestCase):
    def test_dates_owner_and_annual_profit(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'engine.log'
            p.write_text('[0] [I] OPEX 1972-1-4 AIR_BUILD line=3 src_town=38 dst_town=22\n'
                         '[1] [I] OPEX 1972-1-4 AIR_BUILD line=99 src_town=38 dst_town=22\n'
                         '[0] [I] OPEX 1972-1-6 LINE_REVENUE line=3 year=1972 real_prof=-8\n'
                         '[0] [I] OPEX 1973-1-6 LINE_REVENUE line=3 year=1973 real_prof=10\n')
            evs = list(events(p))
        self.assertEqual(len(evs), 3)
        pre = baseline(evs, 38, '1972-05-01')
        self.assertEqual(pre['profit'], -8)
        self.assertEqual(pre['lines'][0]['profit_year'], 1971)
        self.assertIsNone(baseline(evs, 2, '1972-05-01')['profit'])
        self.assertIsNone(baseline(evs, None, '1972-05-01', {22})['profit'])

    def test_lines_are_not_joined_between_games(self):
        evs = [dict(kind='AIR_BUILD', date='1970-01-01', fields=dict(line='5', src_town='2', dst_town='3')),
               dict(kind='LINE_REVENUE', date='1972-01-01', fields=dict(line='5', year='1972', real_prof='0'))]
        self.assertEqual(baseline(evs, 2, '1972-02-01')['profit'], 0)
        self.assertIsNone(baseline(evs, 38, '1972-02-01')['profit'])
        self.assertEqual(stats([]), dict(n=0, mean=None, median=None))

    def test_export_keeps_unknown_and_refuses_overwrite(self):
        result = dict(statues=[dict(seed=42, town=38, cost=140625,
            before=dict(lines=[], profit=None), reference_before=dict(lines=[], profit=None),
            untreated_before=dict(lines=[], profit=None))])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'statues.csv'
            write_statues_csv(result, path)
            self.assertNotIn(b'\r', path.read_bytes())
            with path.open() as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row['annual_causal_gain'], 'unknown')
            self.assertEqual(row['before_air_profit'], 'unknown')
            with self.assertRaises(FileExistsError):
                write_statues_csv(result, path)


if __name__ == '__main__':
    unittest.main()
