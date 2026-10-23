import gzip
from pathlib import Path
import tempfile
import unittest

from diag_calib_rail_air import analyse, band, parse_game, ratio, stats


def log(tag, fields, day='1970-1-1', owner=0):
    return f'[script:4] [{owner}] [I] OPEX {day} {tag} {fields}\n'


class CalibrationTest(unittest.TestCase):
    def fixture(self):
        return [
            log('PROJECT_CHOSEN', 'mode=rail src=1 dst=2 cargo=PASS cost=100 profit=20'),
            log('RAIL_ATTEMPT', 'src=1 dst=2 ok=1 pre=90 model=-1 quote=150 actual=150'),
            log('RAIL_BUILD', 'line=1 src=1 dst=2 cargo=PASS dist=80 cost=150 trains=2'),
            log('LINE_REVENUE', 'line=1 mode=rail cargo=PASS age=1 year=1971 vehs=2 real_prof=999', '1971-1-1'),
            log('LINE_REVENUE', 'line=1 mode=rail cargo=PASS age=2 year=1972 vehs=4 real_prof=60 pred_prof=22', '1972-1-1'),
            log('LINE_REVENUE', 'line=1 mode=rail cargo=PASS age=3 year=1973 vehs=4 real_prof=999', '1973-1-1'),
        ]

    def test_rail_join_and_first_mature_fleet_scaling(self):
        rows, counts = parse_game(self.fixture())
        r = rows[0]
        self.assertEqual(r['capital_ratio'], 1.5)
        self.assertEqual(r['profit_ratio'], 1.5)
        self.assertEqual(r['revenue']['profit_actual'], 60)
        self.assertEqual(r['revenue']['operating_year'], 1971)
        self.assertEqual(len(r['revenue_reports']), 3)
        self.assertEqual(r['revenue_reports'][0]['fields']['real_prof'], '999')
        self.assertIsNone(r['capital_model'])
        self.assertEqual(counts['revenue_immature'], 1)

    def test_air_plan_is_never_actual(self):
        rows, _ = parse_game([
            log('PROJECT_CHOSEN', 'mode=air src=1 dst=2 cargo=PASS cost=100 profit=20'),
            log('AIR_BUILD', 'line=0 src=1 dst=2 dist=140 cost=100 profit=20 planes=1')])
        self.assertEqual(rows[0]['capital_predicted'], 100)
        self.assertIsNone(rows[0]['capital_actual'])
        self.assertIsNone(rows[0]['capital_ratio'])
        self.assertIsNone(rows[0]['profit_ratio'])

    def test_no_cross_company_cargo_reverse_or_choice_reuse(self):
        events = self.fixture()[:3]
        events += [log('RAIL_BUILD', 'line=2 src=1 dst=2 cargo=PASS dist=80 cost=150 trains=1')]
        events += [log('PROJECT_CHOSEN', 'mode=rail src=3 dst=4 cargo=COAL cost=1 profit=1', owner=1),
                   log('PROJECT_CHOSEN', 'mode=rail src=4 dst=3 cargo=COAL cost=1 profit=1'),
                   log('PROJECT_CHOSEN', 'mode=rail src=3 dst=4 cargo=PASS cost=1 profit=1'),
                   log('RAIL_BUILD', 'line=3 src=3 dst=4 cargo=COAL dist=10 cost=150 trains=1')]
        rows, _ = parse_game(events)
        self.assertEqual(len(rows), 3)
        self.assertIsNone(rows[1]['choice_log_line'])
        self.assertIsNone(rows[2]['choice_log_line'])

    def test_failed_or_old_attempt_not_matched(self):
        for ok, day in [('0', '1970-1-1'), ('1', '1969-12-31')]:
            rows, _ = parse_game([
                log('RAIL_ATTEMPT', f'src=1 dst=2 ok={ok} pre=100', day),
                self.fixture()[2]])
            self.assertIsNone(rows[0]['attempt_log_line'])

    def test_missing_zero_negative_and_bins(self):
        self.assertIsNone(ratio(1, 0))
        self.assertIsNone(ratio(None, 2))
        self.assertEqual(ratio(0, 2), 0)
        self.assertEqual(ratio(-4, 2), -2)
        self.assertEqual([band(d) for d in (0, 79, 80, 139, 140, 199, 200, None)],
                         ['0-80', '0-80', '80-140', '80-140', '140-200', '140-200', '200+', 'unknown'])
        self.assertEqual(stats([None, 1, 2, 3, 4]), dict(n=4, median=2.5, q25=1.75, q75=3.25))

    def test_gzip_sources_and_duplicate_rejection(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temp:
            folder = Path(temp)
            plain = folder / 'reference_seed42_r0.log'
            plain.write_text(''.join(self.fixture()), encoding='utf-8')
            first = analyse([folder])
            compressed = plain.with_suffix('.log.gz')
            with gzip.open(compressed, 'wt', encoding='utf-8') as stream:
                stream.write(plain.read_text())
            with self.assertRaises(ValueError):
                analyse([folder])
            plain.unlink()
            second = analyse([folder])
            self.assertEqual(first['summary'], second['summary'])
            self.assertEqual(second['rows'][0]['seed'], 42)
            with self.assertRaises(ValueError):
                analyse([folder, folder])

    def test_duplicate_id_refused(self):
        with self.assertRaises(ValueError):
            parse_game(self.fixture()[:3] + self.fixture()[2:3])


if __name__ == '__main__':
    unittest.main()
