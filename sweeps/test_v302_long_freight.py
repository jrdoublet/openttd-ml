"""V302 settings, bounded fallback, and diagnostic parser fixtures."""
import gzip
from pathlib import Path
import re
import tempfile
import unittest

from diag_v302_long_freight import analyze, terminal_services
from test_b5_rail_persistence import function_body

AI = Path(__file__).resolve().parents[1] / 'ai' / 'OpexAI'


class V302Contracts(unittest.TestCase):
    def test_setting(self):
        info = (AI / 'info.nut').read_text()
        block = re.search(r'AddSetting\(\{\s*name = "v302_long_freight",(.*?)\}\);', info, re.S)[1]
        for level in ('easy', 'medium', 'hard', 'custom'):
            self.assertIn(f'{level}_value = 0', block)
        self.assertIn('min_value = 0, max_value = 1', block)
        self.assertEqual((AI / 'settings.nut').read_text().count('GetSetting("v302_long_freight")'), 1)
        self.assertIn('V302_LONG_FREIGHT <- 0;', (AI / 'globals_pre.nut').read_text())

    def test_same_station_same_length_unique_anchors(self):
        body = function_body((AI / 'lines.nut').read_text(), 'function OpexAI::_tryAttachSharedDest(')
        self.assertIn('V302_LONG_FREIGHT > 0 && candidate.distance > 160', body)
        self.assertIn('OpexLineStationId(line, lineEnd) != bestMatch.stationId', body)
        self.assertIn('platform.length != bestMatch.platform.length', body)
        self.assertIn('platform.anchor in seen', body)
        self.assertNotIn('OpexJoinPlatformPlans(', body)

    def test_fallback_after_original_failure_only(self):
        body = function_body((AI / 'builder_rail.nut').read_text(), 'function OpexRailPlatformPlans(')
        start = body.index('/* V302')
        end = body.index('if (V264_CONVERGENT_FREIGHT', start)
        addition = body[start:end]
        for text in ('V302_LONG_FREIGHT > 0', 'candidate.kind == "freight"', 'candidate.distance > 160',
                     'candidate.shared_dest', 'jointPlansB.len() == 0', 'platform.length != jointLength',
                     'OpexJoinPlatformPlans(platform, candidate.joinStationId, statsB)', '"V302_JOIN"'):
            self.assertIn(text, addition)
        self.assertNotIn('SpreadJoinPlans', addition)
        self.assertNotIn('BuildRailStation', addition)
        self.assertNotIn('.call(', addition)

    def test_log_boundaries_missing_fields_and_gzip(self):
        prefix = '[script:4] [0] [I] OPEX '
        content = '\n'.join([
            prefix+'1975-1-1 PROJECT_CHOSEN mode=rail kind=freight cargo=COAL src=1 dst=180 dist=179',
            prefix+'1975-1-3 RAIL_ATTEMPT kind=freight src=1 dst=180 manh=179 reason=SITEAB ops=1000 search_ops=-1',
            prefix+'1975-1-4 RAIL_ATTEMPT kind=freight src=1 dst=161 manh=160 reason=OK ops=4000',
            prefix+'1975-1-4 RAIL_ATTEMPT kind=pax src=1 dst=181 manh=180 reason=OK ops=4000',
            '[script:4] [1] [I] 1975-1-5 # RouteBuilder Succeeded 0 20 200 Build RailRoute B<-A Coal',
            '[script:4] [1] [I] 1975-1-6 # RouteBuilder Succeeded 0 20 200 Build RailRoute B<-A Mail',
        ])
        with tempfile.TemporaryDirectory() as tmp:
            for suffix in ('.log', '.log.gz'):
                path = Path(tmp)/('fixture'+suffix)
                if suffix.endswith('gz'):
                    with gzip.open(path, 'wt') as stream:
                        stream.write(content)
                else:
                    path.write_text(content)
                data = analyze(path)
                self.assertIsNone(data['long_generated'])
                self.assertEqual(len(data['attempts']), 1)
                row = data['attempts'][0]
                self.assertEqual(row['selection_to_result_days'], 2)
                self.assertIsNone(row['search_slot_days'])
                self.assertEqual(row['search_ops'], '-1')
                self.assertEqual(len(data['aaa']), 1)
                self.assertIsNone(data['aaa'][0]['trains_in_service'])

    def test_terminal_counts_use_decoded_consists_and_keep_unknowns(self):
        line = dict(line_key_local='rail|1,2', mode='rail', capacity_by_cargo={'1': 100},
                    ordered_station_tiles=[0, 161], vehicles=3)
        unknown = dict(line, line_key_local='rail|3', ordered_station_tiles=[None])
        snapshot = dict(duel_policy_id='v302', arm='AAAHogEx', seed=42, repeat=0,
                        date='1979-12-01', ok=True, unresolved_vehicles=[], lines=[line, unknown])
        result = dict(line_telemetry=dict(snapshots=[snapshot, snapshot]))
        services = terminal_services(result)
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]['trains'], 3)
        self.assertEqual(len(services[0]['lines']), 1)
        self.assertEqual(services[0]['unknown_lines'], ['rail|3'])
        result['line_telemetry']['snapshots'].append(dict(snapshot, ok=False))
        with self.assertRaises(ValueError):
            terminal_services(result)


if __name__ == '__main__':
    unittest.main()
