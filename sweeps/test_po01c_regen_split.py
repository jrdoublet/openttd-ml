"""Source contracts; engine exposure separately measures slice overruns."""
import re
import unittest
import hashlib
from po01c_generate import AI, DEEP_SOURCES, generated
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

    def test_po01d_synchronous_path_bytes_unchanged(self):
        # Baseline origin/master 190b4ba1. Intentional later synchronous edits
        # must explicitly rebase this PO01D isolation contract, never regenerate it.
        expected = {
            'builder_water.nut': '92c50153b6712f238943f75e2c9498a602695132a7850c5f663f91344499162e',
            'air_planning.nut': 'c182f3f8fe82d0e39c11426d596a83ccad79a14ec486a1ebe148287790440e32',
            'air_sites.nut': '679b2912e9c71f708e6ad308ce187277f477f1751987405c74fb774998698fc4',
            'candidates.nut': '1f56d53670182f66b2c3d54360927e4be912ba65f4cdbffe1a04dff6dadd54ad',
            'catalog.nut': '4882c4c3de58c97882b2739432e62045a2e567b1ee980e5a2a56dedd34a17ba9',
            'orchestrator.nut': 'bc9aa564c5f84aff5d638086094048548f6f5a9a8eb61d44c047030bfcc71743',
            'main.nut': '81f077c68e094a0a9a8d4a63e1600af0fce0cdd9b9b835077e3da386d3b36ece',
            'probes.nut': 'ef0a1228e758e648736c89b9252dc9568f6b6a834065343e805570aed47788dd',
            'settings.nut': '57c95f154fdb84e9aff9e63ab10d7fef1731b764997b5279cb2d33bba6b353db',
            'info.nut': '9071e91f6a569689275228804d8438c390ed5692ee026f02fe5d172999815c97',
        }
        for name, digest in expected.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((AI / name).read_bytes()).hexdigest(), digest)

    def test_po01d_inner_loops_checkpoint_before_rejections(self):
        targets = {
            'WaterFindConnection': ['while (head < queue.len() && head < WATER_BFS_MAX_NODES)',
                                    'foreach (offset in offsets)'],
            'AirFindSiteListed': ['for (local r = 4; r <= AIR_SITE_RADIUS; r++)',
                                  'foreach (anchor, anchorX in ring)'],
            'AirFindSiteCatchmentListed': ['for (local r = 4; r <= AIR_SITE_RADIUS; r++)',
                                           'foreach (anchor, anchorX in ring)'],
            'AirPlansDiscoverHubs': ['foreach (line in lines)', 'foreach (other in lines)',
                                     'foreach (town in towns)'],
        }
        for name, loops in targets.items():
            code = body('po01c_generators.nut', 'OpexPO01C' + name)
            for loop in loops:
                with self.subTest(name=name, loop=loop):
                    self.assertRegex(code, re.escape(loop) + r'\s*\{\s*yield null;')

    def test_po01d_nested_calls_propagate_and_return_null_safely(self):
        edges = {
            'WaterPlans': 'WaterFindConnection',
            'AirPlans': 'AirPlansStepFindSites',
            'AirPlansStepFindSites': 'AirPlansFindSites',
            'AirPlansFindSites': 'AirFindSite',
            'AirPlansHubDiscoveryPhase': 'AirPlansDiscoverHubs',
            'AirPlansDiscoverHubs': 'AirFindSite',
            'AirFindSite': 'AirFindSiteCatchmentListed',
            'AirFindSiteCatchmentListed': 'AirFindSiteListed',
        }
        for caller, callee in edges.items():
            code = body('po01c_generators.nut', 'OpexPO01C' + caller)
            self.assertIn('OpexPO01C' + callee + '(po01dBox, ', code)
            self.assertNotIn('Opex' + callee + '(', code)
            self.assertRegex(code, r'while \(po01dChild.getstatus\(\) != "dead"\)\s*'
                             r'\{\s*resume po01dChild;\s*yield null;\s*\}')
        for _, name in DEEP_SOURCES:
            code = body('po01c_generators.nut', 'OpexPO01C' + name[4:])
            self.assertNotRegex(code, r'\breturn\s+[^;\s]')
        code = body('po01c_generators.nut', 'OpexPO01CAirFindSiteListed')
        self.assertIn('po01dResult.value = { site = null,', code)
        # Test-mode commands must finish (and release the mode) before yielding.
        for scope in re.findall(r'\{[^{}]*local probe = AITestMode\(\);[^{}]*\}',
                                source('po01c_generators.nut')):
            self.assertNotIn('yield', scope)

    def test_po01d_air_iterator_guard_and_completion(self):
        step = body('po01c_regen.nut', 'OpexPO01CStep')
        self.assertIn('if (s.iterator == null) s.iterator = OpexPO01CGenerateAir(s);', step)
        self.assertIn('s.iterator = null;\n        s.modes.remove(s.modeCursor);', step)
        air = body('po01c_regen.nut', 'OpexPO01CGenerateAir')
        self.assertIn('while (!("done" in s.airCursor) || !s.airCursor.done)', air)
        self.assertIn('best = result.value;', air)
        self.assertLess(air.index('C121_AIR_PLAN_PERF = s.airCursor.c121PlanPerf;'),
                        air.index('resume iterator;'))
        self.assertLess(air.index('C121_AIR_ENDPOINT_CACHE = s.airCursor.c121EndpointCache;'),
                        air.index('resume iterator;'))
        self.assertRegex(air, r'resume iterator;\s*yield null;')

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
        # En tete de boucle, seule la sonde passive V309 (defaut 0) peut preceder le pas PO01C.
        self.assertIn('while (true) {\n    if (V309_IDLE_PROBE) OpexV309IdleBegin();\n    if (PO01C_REGEN_SPLIT', source('main.nut'))

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
