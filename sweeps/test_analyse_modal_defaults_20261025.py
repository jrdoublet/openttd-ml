"""The modal summary must not attribute mixed-service profits to freight alone."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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


if __name__ == '__main__':
    unittest.main()
