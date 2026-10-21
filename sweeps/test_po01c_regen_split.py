"""Source contracts; engine exposure separately measures slice overruns."""
import re
import unittest
from po01c_generate import generated
from test_v261_forum_behaviours import source, body, uncomment
from po01c_diagnostics import pending_save_dates, summarize


class PO01CContracts(unittest.TestCase):
    def test_log_days_not_elapsed_batch_are_freezes(self):
        log = ('[0] [I] OPEX 1972-1-31 PO01C_BATCH phase=save_pending days=30\n'
               '[0] [I] OPEX 1972-2-3 PO01C_BATCH phase=publish days=33 ops=100\n'
               '[0] [I] OPEX 1972-2-3 PO01C_SLICE phase=publish days=2 ops=100\n'
               '[1] [I] OPEX 1972-2-3 PO01C_SLICE phase=publish days=99 ops=100\n')
        self.assertEqual(pending_save_dates(log), {'1972-01-31'})
        summary = summarize(log)
        self.assertEqual(summary['published_count'], 1)
        self.assertEqual(summary['max_slice_days'], 2)
        self.assertEqual(summary['freezes_over_5_days'], 0)

    def test_default_and_single_read(self):
        setting = re.search(r'AddSetting\(\{ name = "po01c_regen_split".*?\}\);', source('info.nut'), re.S)[0]
        for level in ('easy', 'medium', 'hard', 'custom'):
            self.assertIn(level + '_value = 0', setting)
        self.assertEqual(source('settings.nut').count('GetSetting("po01c_regen_split")'), 1)
        self.assertIn('PO01C_REGEN_SPLIT <- false;', source('globals_pre.nut'))

    def test_generators_track_current_producers(self):
        self.assertEqual(source('po01c_generators.nut'), generated())

    def test_selective_publication(self):
        code = body('po01c_regen.nut', 'OpexPO01CPublish')
        self.assertNotRegex(code, r'owner\._catalog\s*=')
        self.assertIn('foreach (layer in s.layers)', code)
        self.assertIn('foreach (mode in s.modes)', code)
        self.assertIn('clone owner._projects', code)
        self.assertIn('OpexAvailableCapital()', code)
        self.assertIn('layer == "engines.air" && OpexPO01CAirPending(owner)', code)

    def test_air_guard_is_local_and_no_fallback(self):
        code = body('po01c_regen.nut', 'OpexPO01CStart')
        self.assertIn('needed && mode == "air" && airPending', code)
        self.assertNotIn('_c76DoFullRegen', source('po01c_regen.nut'))

    def test_snapshot_ack_is_monotone_and_all_consumers_required(self):
        code = body('po01c_regen.nut', 'OpexPO01CAcknowledge')
        self.assertNotIn('_c76Revisions', code)
        self.assertIn('OpexAC06SnapshotLayer(s.snapshot, layer)', code)
        self.assertIn('covered > old ? covered : old', code)
        self.assertIn('if (consumed < covered) covered = consumed;', code)

    def test_coalesces_without_restarting(self):
        code = body('orchestrator.nut', 'OpexAI::_dispatchReactiveIntention')
        branch = code[code.index('if (modes == null)'):code.index('} else if (modes.len() > 0)')]
        self.assertIn('if (PO01C_REGEN_SPLIT && this._projects != null) this._po01cPending = true;', branch)
        self.assertIn('else this._c76DoFullRegen("reactive", year);', branch)
        self.assertIn('this._c80DoModeRegen(modes, "reactive", year);', code)
        self.assertNotIn('_po01cJob =', branch)
        self.assertNotIn('_taskQueue.append', source('po01c_regen.nut'))
        self.assertIn('OpexPO01CStep(this)', body('orchestrator.nut', 'OpexAI::_runOrchestratorTick'))
        self.assertIn('OpexPO01CStep(this)', body('probes.nut', 'OpexAI::_mainLoopProfiled'))
        self.assertIn('while (true) {\n    if (PO01C_REGEN_SPLIT', source('main.nut'))

    def test_budget_and_no_forbidden_syntax(self):
        code = uncomment(source('po01c_regen.nut') + source('po01c_generators.nut'))
        self.assertIn('const PO01C_SLICE_OPS = 40000;', code)
        self.assertIn('OpexOpsMeasureEnd(mark) < PO01C_SLICE_OPS', code)
        self.assertIn('if (tick == owner._po01cLastTick', code)
        self.assertNotIn('.find(', code)
        self.assertNotRegex(code, r'\blocal\s+(clone|base|parent|pass)\b')
        self.assertNotRegex(code, r'=\s*function\s*\(')

    def test_save_discards_job_load_uses_safety_rebuild(self):
        save = body('persist.nut', 'OpexAI::Save')
        self.assertNotRegex(save, r'(?:=|<-)\s*this\._po01cJob')
        self.assertIn('this._po01cJob = null;', body('persist.nut', 'OpexAI::Load'))
        self.assertIn('this._c76ForceReloadRegen = true;', source('persist.nut'))


if __name__ == '__main__':
    unittest.main()
