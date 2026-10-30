"""Offline guards for write-once ESTIM31 combinatorial source bundles."""
import hashlib
import json
from pathlib import Path
import unittest

from sweeps.estim31_combo2_prepare_20261030 import (
    DESIGNS, DEST, LIMIT_NEW, LIMIT_OLD, ROOT, WAIT_NEW, WAIT_OLD,
)


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CombinationContracts(unittest.TestCase):
    def test_distinct_interactions_and_no_existing_historical_top3(self):
        self.assertEqual(len(DESIGNS), 10)
        self.assertEqual(len(set(DESIGNS.values())), len(DESIGNS))
        for candidate in DESIGNS.values():
            _, _, _, growth, flow, load, statue, policy = candidate
            self.assertTrue(growth != 3 or flow or load or statue != 2 or policy != 3)

    def test_off_source_is_not_rewritten(self):
        historical = (ROOT / "ai/OpexAI/air_economics_c121.nut").read_text("utf8")
        settings = (ROOT / "ai/OpexAI/settings.nut").read_text("utf8")
        self.assertIn('require("air_economics_c121_fullscan.nut")', settings)
        self.assertIn('if ((ESTIM_UNIFIE & 1) != 0)', settings)
        self.assertIn('::OpexC121ChooseRoutePlane <- OpexC121ChooseRoutePlaneFullScan;', settings)
        self.assertIn('function OpexC121ChooseRoutePlane(', historical)

    def test_v284_only_existing_gates_are_replaced(self):
        original = (ROOT / "ai/OpexAI/task_v284.nut").read_text("utf8")
        self.assertEqual(original.count(WAIT_OLD), 1)
        self.assertEqual(original.count(LIMIT_OLD), 1)
        self.assertNotIn(WAIT_NEW, original)
        self.assertNotIn(LIMIT_NEW, original)
        self.assertIn('OpexEstimV284Project', original)
        self.assertIn('OpexV284LoopPlan', original)

    def test_frozen_file_set_and_hashes(self):
        for name, params in DESIGNS.items():
            bundle = DEST / name
            if not (bundle / 'design.json').exists():
                continue
            metadata = json.loads((bundle / 'design.json').read_text('utf8'))
            self.assertEqual(metadata['configuration']['estim_unifie'], 31)
            self.assertEqual(metadata['configuration']['probes'], 2)
            self.assertEqual(metadata['configuration']['v284_flow_gate'], params[4])
            allowed = {'ai/OpexAI/air_economics_c121_fullscan.nut'}
            if params[4]:
                allowed.add('ai/OpexAI/task_v284.nut')
            self.assertEqual(set(metadata['changed_from_public']), allowed)
            for rel, expected_sha in metadata['ai_file_sha256'].items():
                self.assertEqual(hash_file(bundle / rel), expected_sha, (name, rel))
            for rel in ('ai/OpexAI/air_economics_c121.nut',
                        'ai/OpexAI/settings.nut', 'ai/OpexAI/persist.nut'):
                self.assertEqual(hash_file(bundle / rel), hash_file(ROOT / rel), rel)
            fullscan = (bundle / 'ai/OpexAI/air_economics_c121_fullscan.nut').read_text('utf8')
            self.assertIn('unsafe bound cannot truncate this scan', fullscan)
            self.assertIn('foreach (candidate in candidates)', fullscan)
            self.assertIn('OpexC121EngineEconomics(', fullscan)
            v284 = (bundle / 'ai/OpexAI/task_v284.nut').read_text('utf8')
            if params[4]:
                self.assertIn(WAIT_NEW, v284)
                self.assertIn(LIMIT_NEW, v284)


if __name__ == '__main__':
    unittest.main()
