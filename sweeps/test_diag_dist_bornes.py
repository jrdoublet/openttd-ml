"""Fixtures autonomes : aucun journal externe ni moteur nécessaire."""

import gzip
from pathlib import Path
import tempfile
import unittest

from sweeps import diag_dist_bornes as diag


EPOCH = 'OPEX 1970-1-2 EPOCH_BOUNDS roadMin=7 roadMax=7 roadGen=200 railMin=7 railAir=200 railMax=200 airMin=200 airMax=512\n'
LOG = ('bruit moteur\n' + EPOCH
       + '[I] OPEX 1970-1-3 PROJECT_CHOSEN mode=air src=1 dst=2 dist=154\n'
       + 'OPEX 1970-1-3 AIR_BUILD arm=hubsite dist=154\n'
       + 'OPEX 1970-1-4 PROJECT_CHOSEN mode=rail dist=201\n'
       + 'OPEX 1970-1-4 RAIL_BUILD dist=201\n'
       + 'OPEX 1970-1-4 ROAD_BUILD dist=20\n'
       + 'OPEX 1970-1-4 RAIL_BUILD_FAIL dist=500\n'
       + 'OPEX 1970-1-5 VIVIER_REJECT reason=distance_long n=30\n'
       + 'OPEX 1970-1-5 VIVIER_REJECT reason=road_distance_short n=2\n'
       + 'OPEX 1970-1-5 C78_AIRPAIR outcome=pax_band\n')


class DistanceTests(unittest.TestCase):
    def analyse(self, text):
        return diag.analyse(diag.parse_lines(text.splitlines()))

    def test_real_fields_and_builds(self):
        result = self.analyse(LOG)
        self.assertEqual(result['distances']['construits', 'air'], [154])
        self.assertEqual(result['distances']['construits', 'rail'], [201])
        self.assertEqual(result['distances']['construits', 'road'], [20])
        self.assertEqual(result['outside']['air', 'sous airMin'], 1)
        self.assertEqual(result['outside']['rail', 'au-dessus de railMax'], 1)
        self.assertEqual(sum(result['rejections'].values()), 33)

    def test_epoch_order_and_same_day(self):
        text = ('OPEX 1970-1-1 PROJECT_CHOSEN mode=air dist=1\n' + EPOCH
                + 'OPEX 1970-10-1 PROJECT_CHOSEN mode=air dist=154\n'
                + EPOCH.replace('1970-1-2', '1970-2-1').replace('airMin=200', 'airMin=100')
                + 'OPEX 1970-2-1 PROJECT_CHOSEN mode=air dist=154\n'
                + EPOCH.replace('1970-1-2', '1970-2-1'))
        result = self.analyse(text)
        self.assertIn('inconnu', result['chosen'][0][-1])
        self.assertEqual(result['chosen'][1][-1], 'dans la bande')
        self.assertEqual(result['chosen'][2][-1], 'sous airMin')
        self.assertIn('airMin: 200 → 100', result['epochs'][1][2])
        self.assertEqual(self.analyse(EPOCH + EPOCH)['epochs'][1][2], '')

    def test_boundaries_and_missing(self):
        bounds = dict(roadMin=7, roadMax=7, railMin=7, railMax=200, airMin=200, airMax=0)
        for mode, distance in [('road', 7), ('rail', 200), ('air', 999)]:
            self.assertEqual(diag.position(mode, distance, bounds), ('dans la bande', []))
        self.assertEqual(diag.position('road', 8, bounds)[1], ['au-dessus de roadMax'])
        self.assertEqual(diag.position('rail', 6, bounds)[1], ['sous railMin'])
        self.assertEqual(diag.position('air', 513, dict(airMin=200, airMax=512))[1], ['au-dessus de airMax'])
        self.assertIn('inconnu', diag.position('air', 5, dict(airMin=200))[0])
        self.assertEqual(diag.position('water', 50, {})[0], 'non applicable')
        result = self.analyse(EPOCH + 'OPEX 1970-1-3 PROJECT_CHOSEN mode=air dist=oops\n')
        self.assertEqual(result['missing']['choisis', 'air'], 1)
        self.assertFalse(result['distances'])

    def test_quantiles(self):
        self.assertEqual(diag.distribution([]), (0, None, None, None, None, None))
        self.assertEqual(diag.distribution([7]), (1, 7, 7, 7, 7, 7))
        self.assertEqual(diag.distribution([40, 10, 30, 20]), (4, 10, 17.5, 25, 32.5, 40))

    def test_rejection_variants(self):
        result = self.analyse('OPEX 1970-1-1 REJECT reason=distanceShort n=4\n'
                              'OPEX 1970-1-1 STATS distanceShort=2 distanceLong=3\n'
                              'OPEX 1970-1-1 REJECT reason=distanceLong n=oops\n')
        self.assertEqual(sum(result['rejections'].values()), 9)
        self.assertEqual(sum(result['unknown_rejections'].values()), 1)
        self.assertIn('non exposés', diag.summary([self.analyse(EPOCH)]))

    def test_files_gzip_aggregation_and_repeat_isolation(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'ref_name_seed42_r0.log').write_text(LOG, encoding='utf-8')
            with gzip.open(folder / 'ref_name_seed42_r1.log.gz', 'wt', encoding='utf-8') as stream:
                stream.write('OPEX 1970-2-1 PROJECT_CHOSEN mode=air dist=100\n')
            (folder / 'variant_seed99_r0.log').write_text(EPOCH, encoding='utf-8')
            (folder / 'ignored.log').write_text(LOG, encoding='utf-8')
            runs = diag.load_logs(folder)
            self.assertEqual(len(runs), 3)
            self.assertIn('inconnu', runs['ref_name', 42, 1]['chosen'][0][-1])
            report = diag.render(runs)
            self.assertIn('### Agrégat du bras ref_name', report)
            self.assertIn('| choisis | air | 2 | 100 | 113.5 | 127 | 140.5 | 154 | 0 |', report)
            self.assertIn('aucun', report.lower())
            (folder / 'ref_name_seed42_r1.log').write_text('', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'dupliqué'):
                diag.load_logs(folder)

    def test_empty_folder_and_invalid_date(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'Aucun journal'):
                diag.load_logs(Path(temp))
        with self.assertRaisesRegex(ValueError, 'Date invalide'):
            diag.parse_lines(['OPEX 1970-13-1 PROJECT_CHOSEN dist=1'])


if __name__ == '__main__':
    unittest.main()
