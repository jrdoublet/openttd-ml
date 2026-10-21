"""V304 diagnostic contracts. Python does not compile Squirrel."""
import unittest
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestV304Probe(unittest.TestCase):
    def test_probe_only_attached_under_decision_log(self):
        builder = (ROOT / 'ai/OpexAI/builder_rail.nut').read_text()
        self.assertIn('if (DECISION_LOG) {\n    state.v304Probe <-', builder)
        self.assertIn('if (DECISION_LOG && ("_v304Probe" in pathfinder))', builder)
        self.assertIn('DECISION_LOG && done && ("v304Probe" in state)', builder)

    def test_probe_bounded_and_reports_coverage(self):
        builder = (ROOT / 'ai/OpexAI/builder_rail.nut').read_text()
        for field in ('tile_reexpanded=', 'state_reexpanded=', 'native_segments=', 'overflow='):
            self.assertIn(field, builder)
        self.assertIn('p.tiles.len() < 50000', builder)
        self.assertIn('p.states.len() < 50000', builder)

    def test_only_accepted_expansions_count(self):
        native = (ROOT / 'ai/OpexAI/pathfinder_v90/v296.nut').read_text()
        self.assertLess(native.index('closed[cur] <- direction;'), native.index('OpexV304Observe('))
        self.assertLess(native.index('OpexV304Observe('), native.index('local atGoal ='))

    def test_setting_is_opt_in_and_read_once(self):
        info = (ROOT / 'ai/OpexAI/info.nut').read_text()
        block = re.search(r'name = "v304_segment_memory",(.*?)\}\);', info, re.S)[1]
        for level in ('easy', 'medium', 'hard', 'custom'):
            self.assertIn(f'{level}_value = 0', block)
        self.assertIn('min_value = 0, max_value = 1', block)
        self.assertEqual(info.count('AddSetting('), 90)
        settings = (ROOT / 'ai/OpexAI/settings.nut').read_text()
        self.assertEqual(settings.count('GetSetting("v304_segment_memory")'), 1)
        self.assertIn('V304_SEGMENT_MEMORY <- 0;', (ROOT / 'ai/OpexAI/globals_pre.nut').read_text())

    def test_mode_does_not_reset_g_or_drop_frontier_on_cut(self):
        text = (ROOT / 'ai/OpexAI/builder_rail.nut').read_text()
        body = text.split('function OpexAdvanceSegmentMemory(', 1)[1].split('function OpexSearchPath(', 1)[0]
        for required in ('m.frames.push(open)', 'pf._pathfinder._open = m.frames.pop()',
                         'branch.AddItem(id, priority)', 'state.backtracks >= SEGMENTED_MAX_BACKTRACKS',
                         'state.currentSegmentLimit = SEGMENTED_RECOVERY_ITERS',
                         'state.prefix = OpexSegmentTiles(path)'):
            self.assertIn(required, body)
        for forbidden in ('InitializePath(', 'OpexNewRailPathfinder', 'state.iterations = 0',
                          'OpexSegmentIgnoredTiles('):
            self.assertNotIn(forbidden, body)

    def test_g_memory_is_bounded_and_reopens_improvements(self):
        native = (ROOT / 'ai/OpexAI/pathfinder_v90/v296.nut').read_text()
        for required in ('costs[id] >= memory.bestG[key]', 'memory.bestG[key] <- costs[id]',
                         'memory.bestG.len() >= 50000', 'nid >= 50000',
                         'if (this._v304Memory != null) return null;',
                         'this._v304Memory.active'):
            self.assertIn(required, native)
        # No early freeing of ancestry on local exhaustion; controller owns alternatives.
        self.assertLess(native.index('if (this._v304Memory != null) return null;'),
                        native.index('return this._Finish(-1);'))

    def test_weights_revalue_retained_frontiers(self):
        text = (ROOT / 'ai/OpexAI/builder_rail.nut').read_text()
        self.assertIn('OpexV304ReweightQueue(pf._pathfinder._open, pf);', text)
        self.assertIn('foreach (frame in state.v304Memory.frames) OpexV304ReweightQueue(frame, pf);', text)
        self.assertIn('open.SetValue(id, OpexV304Priority(id, pf))', text)
        self.assertIn('V304_SEGMENT_MEMORY == 1 && V296_ASTAR_NATIVE == 1', text)

    def test_parser_preserves_failure_and_missing_coverage(self):
        from diag_v304_segments import read_rows, summarise
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reference_seed42_r0.log'
            path.write_text('[0] OPEX 1970 V304_SEARCH src=1 dst=2 dist=170 outcome=ABND '
                            'iters=5000 segments=3 expanded=4000 tile_reexpanded=900 '
                            'state_reexpanded=700 tiles=3100 states=3300 overflow=0 native_segments=3\n'
                            '[1] OPEX 1970 V304_SEARCH src=9\n')
            rows = read_rows(directory)
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0]['coverage_complete'])
            summary = summarise(rows)[0]
            self.assertEqual(summary['outcome'], 'ABND')
            self.assertEqual(summary['distance'], '>=160')
            self.assertEqual(summary['iters']['mean'], 5000)
            path.write_text(path.read_text().replace('native_segments=3', 'native_segments=2'))
            self.assertFalse(read_rows(directory)[0]['coverage_complete'])
            path.write_text('[0] OPEX 1970 V304_SEARCH src=1\n')
            with self.assertRaises(ValueError):
                read_rows(directory)

    def test_pair_comparison_does_not_claim_same_route_for_different_endpoints(self):
        from diag_v304_segments import compare_first_pairs
        common = dict(seed=42, repeat=0, src=1, dst=2, outcome='OK', iters=20, segments=1)
        rows = [dict(common, arm='reference', route=[10, 11, 12], path_cost=100),
                dict(common, arm='v304', route=[20, 21, 22], path_cost=80)]
        result = compare_first_pairs(rows)[0]
        self.assertFalse(result['identical_route'])
        self.assertFalse(result['same_endpoints'])
        self.assertEqual(result['path_cost_delta'], -20)
        # A second attempt must not replace the first with a more favourable outcome.
        rows.append(dict(common, arm='v304', route=[10, 11, 12], path_cost=100))
        self.assertEqual(compare_first_pairs(rows)[0], result)


if __name__ == '__main__':
    unittest.main()
