"""Check fixture/schema bindings against the actual Squirrel codec assignments.

This checks field layout statically, not Squirrel execution or an engine roundtrip.
"""
import json
import re
import unittest
from pathlib import Path
from test_v233_contracts import AI
from test_c45_subsidy_persistence import function_body


class SaveFixtures(unittest.TestCase):
    def test_partial_and_complete_windows_roundtrip_field_layout(self):
        text = (AI / 'goods_v233.nut').read_text()
        writer = function_body(text, 'function OpexV233SaveObservations(rows)')
        reader = function_body(text, 'function OpexV233LoadObservations(data)')
        fields = re.findall(r'row\.(\w+)', writer.split('out.append([', 1)[1].split(']);', 1)[0])
        bindings = {name: int(index) for name, index in re.findall(r'(\w+) = tuple\[(\d+)\]', reader)}
        self.assertEqual(fields, ['factoryId', 'factoryTile', 'cargo', 'stationId', 'stationTile',
                                  'lastMonth', 'q0', 'q1', 'q2', 'count'])
        fixtures = json.loads((Path(__file__).parent / 'fixtures/v233_goods_observations.json').read_text())
        self.assertNotIn('v233GoodsObservations', fixtures['legacy'])
        for name, save in fixtures.items():
            if name == 'legacy':
                continue
            with self.subTest(name=name):
                data = save['v233GoodsObservations']
                self.assertEqual(data['version'], 1)
                for row in data['rows']:
                    decoded = {field: row[index] for field, index in bindings.items()}
                    self.assertEqual([decoded[field] for field in fields], row)
                    self.assertTrue(all(type(value) is int for value in row))
                    self.assertIn(decoded['count'], (1, 2, 3))
                    self.assertNotEqual(decoded['stationId'], decoded['stationTile'])

    def test_projection_keeps_optional_line_scalars_without_plan_objects(self):
        persist = (AI / 'persist.nut').read_text()
        projection = function_body(persist, 'function OpexSaveProjectLine(line)')
        # Optional station/factory/cargo identities use the existing scalar projection.
        self.assertIn('typeof', projection)
        self.assertIn('integer', projection)
        save = function_body(persist, 'function OpexAI::Save()')
        self.assertNotIn('_v233Plans', save)
        self.assertIn('OpexSaveProjectLine(line)', save)
        rail = (AI / 'task_rail.nut').read_text()
        for field in ('v233SharedStationId', 'v233FactoryId', 'v233GoodsCargo'):
            self.assertIn(field, rail)
        self.assertIn('this._saveProjection = null;', rail)


if __name__ == '__main__':
    unittest.main()
