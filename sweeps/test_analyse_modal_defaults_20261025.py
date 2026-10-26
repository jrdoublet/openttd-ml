"""The modal summary must not attribute mixed-service profits to freight alone."""

import json
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from sweeps import analyse_modal_defaults_20261025 as modal


class ModalCargoClassesTests(unittest.TestCase):
    def test_passenger_mail_only_is_not_freight(self):
        self.assertEqual(modal.cargo_class({'0': 80, '2': 40}), 'passenger_mail')

    def test_pure_freight_remains_freight(self):
        self.assertEqual(modal.cargo_class({'5': 120}), 'freight')

    def test_passenger_and_freight_are_separate_mixed_class(self):
        self.assertEqual(modal.cargo_class({'0': 60, '2': 10, '5': 100}),
                         'mixed_passenger_freight')

    def test_absent_and_zero_capacity_are_not_carried_cargo(self):
        self.assertEqual(modal.cargo_class({}), 'unknown')
        self.assertEqual(modal.cargo_class({'0': 0, '5': 100}), 'freight')

    def test_full_summary_excludes_mixed_profit_from_pure_freight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stem = 'modal_rail_defaults_master85c88_40x5_20261025'
            campaign = {
                'summary': [{'arm': 'OpexAI', 'seed': 42, 'profit_year': 900}],
                'games': [{'game_status': 'complete'}],
                'failed_runs': [],
                'source_bundle_sha256': 'fixture',
            }
            (root / (stem + '.json')).write_text(json.dumps(campaign), encoding='utf-8')
            snapshot = {
                'run': ['OpexAI', 42, 0], 'date': '1974-12-01',
                'line_telemetry': {'ok': True, 'lines': [
                    {'line_key_local': 'group:1', 'mode': 'rail',
                     'capacity_by_cargo': {'0': 60, '5': 100},
                     'ordered_station_tiles': [1, 300],
                     'vehicles': 1, 'profit_this_year_gbp': 300},
                    {'line_key_local': 'group:2', 'mode': 'rail',
                     'capacity_by_cargo': {'5': 100},
                     'ordered_station_tiles': [3, 500],
                     'vehicles': 1, 'profit_this_year_gbp': 100},
                ]},
            }
            (root / (stem + '.jsonl')).write_text(json.dumps(snapshot) + '\n', encoding='utf-8')
            with patch.object(modal, 'ROOT', root):
                lines = modal.summarize('rail')['annual']['OpexAI']['1974']['lines']
            classes = lines['line_profit_by_cargo_class']
            self.assertEqual(classes['freight']['n'], 1)
            self.assertEqual(classes['freight']['mean'], 100)
            self.assertEqual(classes['mixed_passenger_freight']['n'], 1)
            self.assertEqual(classes['mixed_passenger_freight']['mean'], 300)

    def test_existing_rail_report_cannot_be_replaced_or_trigger_air_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / 'modal_rail_defaults_master85c88_40x5_20261025_analysis.json'
            existing.write_bytes(b'original historic rail verdict\n')
            unused = Mock()
            with patch.object(modal, 'ROOT', root), patch.object(modal, 'summarize', unused):
                with self.assertRaises(FileExistsError):
                    modal.publish_reports()
            unused.assert_not_called()
            self.assertEqual(existing.read_bytes(), b'original historic rail verdict\n')
            self.assertFalse((root / 'modal_air_defaults_master85c88_40x5_20261025_analysis.json').exists())

    def test_existing_air_report_blocks_rail_before_any_partial_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / 'modal_air_defaults_master85c88_40x5_20261025_analysis.json'
            existing.write_bytes(b'original historic air verdict\n')
            with patch.object(modal, 'ROOT', root), patch.object(modal, 'summarize') as run:
                with self.assertRaises(FileExistsError):
                    modal.publish_reports()
            run.assert_not_called()
            self.assertEqual(existing.read_bytes(), b'original historic air verdict\n')
            self.assertFalse((root / 'modal_rail_defaults_master85c88_40x5_20261025_analysis.json').exists())

    def test_failed_second_analysis_creates_neither_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def summarizer(mode):
                if mode == 'air':
                    raise ValueError('missing source archive')
                return {'campaign': 'fixture'}
            with patch.object(modal, 'ROOT', root), patch.object(modal, 'summarize', summarizer):
                with self.assertRaisesRegex(ValueError, 'missing source archive'):
                    modal.publish_reports()
            self.assertEqual(list(root.iterdir()), [])

    def test_new_reports_are_written_exclusively_with_expected_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def summarizer(mode):
                return {'campaign': f'{mode}-fixture', 'status_counts': {'complete': 1},
                        'losses': {'1974': {'ratio_of_means_pct': 95}}}
            with patch.object(modal, 'ROOT', root), patch.object(modal, 'summarize', summarizer):
                with contextlib.redirect_stdout(io.StringIO()):
                    modal.publish_reports()
            for mode in ('rail', 'air'):
                path = root / f'modal_{mode}_defaults_master85c88_40x5_20261025_analysis.json'
                self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['campaign'],
                                 f'{mode}-fixture')
                self.assertTrue(path.read_bytes().endswith(b'\n'))


if __name__ == '__main__':
    unittest.main()
