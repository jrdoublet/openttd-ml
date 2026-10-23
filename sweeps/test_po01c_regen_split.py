"""Source contracts; engine exposure separately measures slice overruns."""
import re
import unittest
import hashlib
from po01c_generate import AI, DEEP_SOURCES, generated, function, unit_sites, bridge, budgeted_pax
from test_v261_forum_behaviours import source, body, uncomment
from po01c_diagnostics import pending_save_dates, summarize


def unbudgeted_pax(code):
    # Strip only PO01H scheduling, retaining PO01G checkpoints/site diagnostics.
    code = re.sub(r'if \(OpexOpsMeasureEnd\(PO01C_WORK_MARK\) >= PO01C_WORK_OPS\) \{\s*'
                  r'(yield null;(?: // PO01C_CHECKPOINT)?'
                  r'(?:\s*if \(DECISION_LOG\) OpexPO01CWhere\([^;]*\);)?)\s*\}',
                  r'\1', code)
    return code.replace('if (po01dChild.getstatus() != "dead") yield null;', 'yield null;')


class PO01CContracts(unittest.TestCase):
    def test_po01h_budget_gate_and_live_propagation(self):
        for name in ('PaxCandidates', 'MakePaxCandidate', 'RailOriginSitable',
                     'V216MarkRect', 'V216RefreshCover', 'V216AdvAround',
                     'V216Coverage', 'V216GainPct', 'V216aEndPct', 'V216aScaleDemand'):
            code = function(source('po01c_generators.nut'), 'OpexPO01C' + name)
            restored = unbudgeted_pax(code)
            # Inverse scheduling transform restores every business token and
            # every original site; no silently removed return/continue/loop.
            self.assertEqual(re.sub(r'\s+', '', budgeted_pax(restored)),
                             re.sub(r'\s+', '', code))
            for match in re.finditer(r'resume po01dChild;', code):
                self.assertTrue(code[match.end():].lstrip().startswith(
                    'if (po01dChild.getstatus() != "dead") yield null;'))
        step = body('po01c_regen.nut', 'OpexPO01CStep')
        self.assertEqual(step.count('PO01C_WORK_MARK ='), 2)
        self.assertIn('const PO01C_WORK_OPS = 30000;', source('po01c_regen.nut'))
        self.assertNotIn('PO01C_WORK_MARK', source('persist.nut'))

    def test_po01h_yield_count_budget_and_order_model(self):
        # Scheduling model, not VM measurements. Polling and propagation costs
        # are explicit illustrative inputs. Epoch/API data remain fixed.
        def run(width, height, depth, gated):
            ops = unit_ops = yields = polls = 0
            visits, admitted = [], []

            def checkpoint():
                nonlocal ops, unit_ops, yields, polls
                polls += 1
                ops += 40
                unit_ops += 40
                if not gated or unit_ops >= 30000:
                    yields += 1
                    ops += 80 + 20 * depth
                    unit_ops = 0  # Step refreshes mark; other tasks excluded.

            for x in range(width):
                checkpoint()
                for y in range(height):
                    if (x * height + y + 1) % 32 == 0:
                        checkpoint()
                    visits.append((x, y))
                    # Include cheap rejected tiles and heavier accepted tiles.
                    cost = 20 if (x + y) % 3 == 0 else 100
                    ops += cost
                    unit_ops += cost
                    self.assertLessEqual(unit_ops, 30000 + 32 * 140)
                    if (x + y) % 3 == 0:
                        continue
                    admitted.append((x, y))
            return visits, admitted, yields, polls, ops

        for depth in (1, 4, 8):
            for width, height in ((1, 1), (15, 15), (200, 15), (200, 225)):
                old, new = run(width, height, depth, False), run(width, height, depth, True)
                self.assertEqual(new[:2], old[:2])
                self.assertEqual(new[3], old[3])
                self.assertLessEqual(new[2], old[2])
                self.assertLessEqual(new[4], old[4])
                if width == 200:
                    self.assertLess(new[2], old[2] / 4)
        # Cached children can return without a single suspension. Dead children
        # must not cause eight gratuitous yields on the return path.
        def nested(depth, checkpoints, gated, box):
            if depth == 0:
                for visit in range(checkpoints):
                    yield visit
                box.append(None)  # A legitimate null result, not a suspension.
                return
            child = nested(depth - 1, checkpoints, gated, box)
            while True:
                try:
                    value = next(child)
                except StopIteration:
                    if not gated:
                        yield None  # PO01G also propagated dead-child resumes.
                    return
                yield value

        for suspended in (0, 1, 10):
            before, after = [], []
            old = list(nested(8, suspended, False, before))
            new = list(nested(8, suspended, True, after))
            self.assertEqual(before, after)
            self.assertEqual(after, [None])
            self.assertEqual(new, list(range(suspended)))
            self.assertEqual(len(old) - len(new), 8)

    def test_po01h_unit_covers_layer_publish_and_mode(self):
        step = body('po01c_regen.nut', 'OpexPO01CStep')
        self.assertNotIn('DECISION_LOG && phase == "mode"', step)
        self.assertIn('unit = s.layers[s.layerCursor];', step)
        self.assertIn('"phase=" + phase + " mode=" + unit', step)
        self.assertIn('"whole_publish"', step)
        publish = body('po01c_regen.nut', 'OpexPO01CPublish')
        for site in ('resizeAirFleets', 'OpexReselectProjects'):
            self.assertRegex(publish, r'if \(DECISION_LOG\) OpexPO01CUnitEnd\([^;]*"' + site + r'"\);')
        self.assertIn('if (!DECISION_LOG) return;', body('po01c_regen.nut', 'OpexPO01CUnitEnd'))

    def test_po01g_epoch_and_diagnostics_scope(self):
        producer = body('po01c_generators.nut', 'OpexPO01CPaxCandidates')
        candidate = body('po01c_generators.nut', 'OpexPO01CMakePaxCandidate')
        refresh = body('po01c_generators.nut', 'OpexPO01CV216RefreshCover')
        self.assertEqual(producer.count('now = AIDate.GetCurrentDate()'), 1)
        self.assertNotIn('po01fContext.now =', source('po01c_generators.nut'))
        self.assertLess(refresh.index('if (cover.ownMonth == ym)'),
                        refresh.index('po01fContext.diagnostics.coverRebuilds++'))
        for code, counter in ((refresh, 'coverRebuilds'), (candidate, 'sitableFills')):
            self.assertRegex(code, r'if \(DECISION_LOG && po01fContext.diagnostics != null\)\s*'
                             + 'po01fContext.diagnostics.' + counter + r'\+\+;')
        self.assertLess(candidate.index('po01fSitableCache[sitableKey] <- sitable;'),
                        candidate.index('po01fContext.diagnostics.sitableFills++'))
        start = body('po01c_regen.nut', 'OpexPO01CStart')
        self.assertIn('paxDiagnostics = DECISION_LOG ? { coverRebuilds = 0, sitableFills = 0 } : null', start)
        step = body('po01c_regen.nut', 'OpexPO01CStep')
        self.assertIn('else if (DECISION_LOG && s.slices % 200 == 0)', step)
        self.assertIn('OpexPO01CLog(owner, s, "progress");', step)
        log = body('po01c_regen.nut', 'OpexPO01CLog')
        self.assertLess(log.index('if (!DECISION_LOG) return;'), log.index('cover_rebuilds='))
        self.assertIn('sitable_fills=', log)
        self.assertNotIn('paxDiagnostics', source('persist.nut'))

    def test_po01g_bounded_rebuilds_and_identical_frozen_reads_model(self):
        # Executable cache-lifetime model, NOT a Squirrel/opcode simulator.
        # Advancing scheduling time must not invalidate a producer's epoch.
        def run(months, frozen, warm=False):
            epoch = months[0]
            own_month = epoch if warm else -1
            rebuilds = fills = coverage_fills = 0
            sitable, coverage = {}, {}
            emitted, counters = [], dict(unsitable=0, noMonthly=0, admitted=0)
            for i, clock in enumerate(months):
                src, dst = i // 8, (i * 7 + 3) % 31
                # Includes cached false and cached zero, two endpoints and mail.
                if src not in sitable:
                    sitable[src] = src % 5 != 0
                    fills += 1
                if not sitable[src]:
                    counters['unsitable'] += 1
                    continue
                values = []
                for cargo in (0, 1):
                    for center in (src, dst):
                        ym = epoch if frozen else clock
                        if own_month != ym:
                            own_month = ym
                            coverage = {}
                            rebuilds += 1
                        key = center, cargo
                        if key not in coverage:
                            # Frozen API fixture, independent of scheduling time.
                            coverage[key] = (center * 11 + cargo * 3) % 17
                            coverage_fills += 1
                        values.append(coverage[key])
                if sum(values[:2]) == 0:
                    counters['noMonthly'] += 1
                else:
                    emitted.append((src, dst, tuple(values)))
                    counters['admitted'] += 1
            return emitted, counters, rebuilds, fills, coverage_fills

        for month_count in (1, 12, 24, 120):
            # Every month contains 64 pairs, including rejecting origins.
            months = [100 + i // 64 for i in range(month_count * 64)]
            for warm in (False, True):
                reference = run([months[0]] * len(months), False, warm)
                before = run(months, False, warm)
                after = run(months, True, warm)
                self.assertEqual(after, reference)
                self.assertEqual(before[:2], reference[:2])
                self.assertEqual(after[2], 0 if warm else 1)
                self.assertEqual(before[2], month_count - int(warm))
                self.assertEqual(after[3], len(months) // 8)
                self.assertLessEqual(after[4], 2 * (len(months) // 8 + 31))

    def test_po01g_checkpoint_packets_preserve_rejections_and_order(self):
        # Model the emitted inner checkpoints (outer row checkpoints remain).
        for width in (1, 15, 31, 32, 33, 1024):
            work, gap, max_gap, checkpoints = 0, 0, 0, 0
            actual = []
            for x in range(7):
                max_gap = max(max_gap, gap)
                gap = 0  # Existing unconditional outer checkpoint.
                for y in range(width):
                    work += 1
                    if work % 32 == 0:
                        max_gap = max(max_gap, gap)
                        gap = 0
                        checkpoints += 1
                    gap += 1
                    if (x + y) % 3 == 0:
                        continue
                    actual.append((x, y))
            self.assertLessEqual(max(max_gap, gap), 32)
            self.assertEqual(checkpoints, 7 * width // 32)
            self.assertEqual(actual, [(x, y) for x in range(7) for y in range(width)
                                      if (x + y) % 3 != 0])

    def test_po01f_candidate_business_tokens_preserved(self):
        copied = unbudgeted_pax(function(source('po01c_generators.nut'), 'OpexPO01CMakePaxCandidate'))
        copied = re.sub(r'if \(DECISION_LOG\) OpexPO01CWhere\([^;]*\);', '', copied)
        for callee, args, result, original in (
            ('OpexRailOriginSitable', 'srcTile, cargo, catalog.railCoverage, true', 'sitable',
             'sitable = OpexRailOriginSitable(srcTile, cargo, catalog.railCoverage, true);'),
            ('OpexV216aScaleDemand', 'po01fContext, srcTile, dstTile, cargo, monthly', 'monthly',
             'monthly = OpexV216aScaleDemand(srcTile, dstTile, cargo, monthly);'),
            ('OpexV216aScaleDemand', 'po01fContext, srcTile, dstTile, secondary.cargo, secondary.monthly',
             'local po01fMail', 'SECONDARY')):
            segment = bridge('CHILD', 'CHILD', callee, args, result)
            self.assertIn(segment, copied)
            copied = copied.replace(segment, original)
        copied = re.sub(r'if \(secondary != null\) \{\s*SECONDARY\s*secondary = '
                        r'\{ cargo = secondary.cargo, monthly = po01fMail \};\s*\}',
                        'if (secondary != null) secondary = { cargo = secondary.cargo, '
                        'monthly = OpexV216aScaleDemand(srcTile, dstTile, secondary.cargo, secondary.monthly) };', copied)
        copied = copied.replace('OpexPO01CMakePaxCandidate(po01dResult, po01fSitableCache, po01fContext,',
                                'OpexMakeCandidate(')
        copied = copied.replace('po01fSitableCache', '::OpexSitableCache')
        copied = re.sub(r'if \(DECISION_LOG && po01fContext.diagnostics != null\)\s*'
                        r'po01fContext.diagnostics.sitableFills\+\+;', '', copied)
        copied = copied.replace('po01fContext.used = true;', '')
        copied = re.sub(r'\{ po01dResult.value = ([^;]*); return; \}', r'return \1;', copied)
        self.assertEqual(re.sub(r'\s+', '', copied),
                         re.sub(r'\s+', '', function(source('candidates.nut'), 'OpexMakeCandidate')))

    def test_po01f_historical_dependencies_unchanged(self):
        expected = {
            'probe_v216.nut': '8971a9dcf90ec29fce9baaca9f4959bbcc3c7db5d3e648963f1481c768ab5166',
            'economy.nut': 'c89b774e6465708574567ad591372917c13fc6fe51b82921def346fbc623978b',
            'builder_rail.nut': 'e9c8b8b15e4f852168752851e0261efebedb8098df21d7d1f61073c95826188f',
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((AI / name).read_bytes()).hexdigest(), digest)

    def test_po01f_heavy_loop_tokens_and_checkpoints(self):
        for file, name in [('probe_v216.nut', 'V216MarkRect'),
                           ('candidates.nut', 'RailOriginSitable')]:
            original = function(source(file), 'Opex' + name)
            copied = unbudgeted_pax(function(source('po01c_generators.nut'), 'OpexPO01C' + name))
            copied = copied.replace('OpexPO01C' + name + '(po01dResult, ', 'Opex' + name + '(')
            copied = copied.replace('po01fContext, ', '')
            copied = copied.replace('local po01gWork = 0;', '')
            copied = re.sub(r'if \(\+\+po01gWork % 32 == 0\) \{\s*'
                            r'yield null; // PO01C_CHECKPOINT\s*'
                            r'if \(DECISION_LOG\) OpexPO01CWhere\([^;]*\);\s*\}', '', copied)
            copied = re.sub(r'yield null; // PO01C_CHECKPOINT', '', copied)
            copied = re.sub(r'if \(DECISION_LOG\) OpexPO01CWhere\([^;]*\);', '', copied)
            copied = re.sub(r'\{ po01dResult.value = ([^;]*); return; \}', r'return \1;', copied)
            self.assertEqual(re.sub(r'\s+', '', original), re.sub(r'\s+', '', copied))
        targets = {'V216MarkRect': 'for (local y = y0; y <= y1; y++)',
                   'V216RefreshCover': 'foreach (tile, tv in AITileList_StationType(st, type))',
                   'V216AdvAround': 'foreach (tile, tv in tiles)',
                   'V216Coverage': 'for (local y = cy - radius; y <= cy + radius; y++)',
                   'RailOriginSitable': 'for (local dy = -r; dy <= r; dy++)'}
        for name, loop in targets.items():
            code = unbudgeted_pax(body('po01c_generators.nut', 'OpexPO01C' + name))
            self.assertRegex(code, re.escape(loop) + r'\s*\{\s*'
                             r'(?:if \(\+\+po01gWork % 32 == 0\) \{\s*)?yield null;')
            for line in code.splitlines():
                if 'OpexPO01CWhere(' in line:
                    self.assertIn('if (DECISION_LOG)', line)

    def test_po01f_entire_coverage_chain_is_resumed(self):
        edges = {'PaxCandidates': ['MakePaxCandidate'],
                 'MakePaxCandidate': ['RailOriginSitable', 'V216aScaleDemand'],
                 'V216aScaleDemand': ['V216aEndPct'],
                 'V216aEndPct': ['V216GainPct', 'V216Coverage'],
                 'V216GainPct': ['V216Coverage'],
                 'V216Coverage': ['V216RefreshCover', 'V216AdvAround'],
                 'V216RefreshCover': ['V216MarkRect'],
                 'V216AdvAround': ['V216MarkRect']}
        for caller, callees in edges.items():
            code = unbudgeted_pax(body('po01c_generators.nut', 'OpexPO01C' + caller))
            for callee in callees:
                self.assertIn('OpexPO01C' + callee + '(po01dBox, ', code)
                self.assertNotIn('Opex' + callee + '(', code)
            self.assertRegex(code, r'resume po01dChild;\s*yield null;')
        candidate = body('po01c_generators.nut', 'OpexPO01CMakePaxCandidate')
        self.assertNotIn('OpexStationPlans', candidate)
        self.assertIn('OpexLineEconomics(catalog, cargo, distance, monthly, kind, 0, null, profile, cruiseCache,', candidate)
        self.assertNotIn('::OpexSitableCache', candidate)
        self.assertIn('po01fSitableCache[sitableKey] <- sitable;', candidate)
        refresh = body('po01c_generators.nut', 'OpexPO01CV216RefreshCover')
        self.assertIn('local now = po01fContext.now;', refresh)
        self.assertNotIn('V216_COVER', refresh)
        for field in ('adv', 'cache'):
            self.assertIn(field + ' = clone po01fOriginal.' + field,
                          body('po01c_generators.nut', 'OpexPO01CPaxCandidates'))
        producer = body('po01c_generators.nut', 'OpexPO01CPaxCandidates')
        self.assertNotIn('V216_COVER', candidate)
        self.assertNotIn('po01fContext.now =', candidate)
        self.assertIn('now = AIDate.GetCurrentDate()', producer)
        self.assertIn('po01fSitableCache, po01fContext, catalog, "pax"', producer)
        self.assertGreater(producer.index('V216_COVER = po01fContext.cover;'),
                           producer.index('out.append(candidate);'))

    def test_po01f_cache_interleaving_model(self):
        # Copy-on-write invariant: entries are immutable once published. A refresh
        # replaces own, never edits the previous map or its rating arrays.
        published = dict(ownMonth=1, advQuarter=0, own={1: [20, 10]},
                         adv={5: {9: True}}, cache={'old': {'prod': 2}})
        private = dict(published, adv=dict(published['adv']), cache=dict(published['cache']))
        private.update(ownMonth=2, own={}, cache={})
        for tile in range(5):
            private['own'][tile] = [30, 15]
            # A synchronous consumer between resumes can see only complete old data.
            self.assertEqual(published['own'], {1: [20, 10]})
            published['cache']['external'] = {'prod': 3}
        private['cache']['pair'] = {'prod': 5}
        self.assertNotIn('pair', published['cache'])
        # Another consumer completes a cache entry AFTER the first pair, before
        # the second. Both pairs must keep using the producer's private context.
        published['cache']['second'] = {'prod': 99}
        following = private
        self.assertEqual(following['cache']['pair'], {'prod': 5})
        self.assertEqual(following['own'], {i: [30, 15] for i in range(5)})
        # The next pair uses the completed first pair's cache, never its partial map.
        self.assertNotIn('external', following['cache'])
        self.assertNotIn('second', following['cache'])
        published = private  # Only the producer's completion publishes its maps.
        self.assertEqual(published['cache'], {'pair': {'prod': 5}})

    def test_po01e_units_group_only_logged_maxima(self):
        prefix = '[0] [I] OPEX 1973-11-4 PO01C_UNIT '
        log = ''.join(prefix + f'mode=rail gen=OpexPO01CPaxCandidates '
                      f'site=rail_pax:pair_candidate idx={i} ops={ops}\n'
                      for i, ops in enumerate((1000000, 500000, 600000)))
        log += prefix + 'mode=road gen=OpexPO01CRoadFreightCandidates site=before_first_yield idx=-1 ops=41000\n'
        log += log.replace('[0]', '[1]')  # Opponent must not enter the aggregates.
        log += '[0] [I] OPEX 1973-11-4 PO01C_SLICE phase=mode ops=9999999 days=5\n'
        rows = summarize(log)['units']
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], dict(mode='rail', gen='OpexPO01CPaxCandidates',
                         site='rail_pax:pair_candidate', count=3,
                         ops_max=1000000, ops_median=600000))
        self.assertEqual(rows[1]['ops_median'], 41000)
        self.assertEqual(summarize('')['units'], [])
        even = prefix + 'mode=road gen=g site=s idx=0 ops=40001\n'
        even += prefix + 'mode=road gen=g site=s idx=1 ops=40002\n'
        self.assertEqual(summarize(even)['units'][0]['ops_median'], 40001.5)

    def test_po01e_sites_guarded_and_business_code_preserved(self):
        for name in ('PaxCandidates', 'FreightCandidates', 'RoadFreightCandidates'):
            original = function(source('candidates.nut'), 'Opex' + name)
            original = original.replace('Opex' + name, 'OpexPO01C' + name, 1)
            original = re.sub(r'((?:for|foreach|while)\s*\([^\n]*\)\s*\{)',
                              r'\1\n    yield null; // PO01C_CHECKPOINT', original)
            instrumented = unit_sites(original, 'Opex' + name)
            for line in instrumented.splitlines():
                if 'OpexPO01CWhere(' in line:
                    self.assertIn('if (DECISION_LOG) OpexPO01CWhere(', line)
            self.assertIn('"before_first_yield"', instrumented)
            self.assertIn('"after_last_yield"', instrumented)
            self.assertIn(':pair_candidate"', instrumented)
            self.assertEqual(original.count('yield null;'), instrumented.count('yield null;'))
            stripped = re.sub(r'if \(DECISION_LOG\) OpexPO01CWhere\([^;]*\);', '', instrumented)
            stripped = stripped.replace('{  return; }', 'return;')
            stripped = stripped.replace('foreach (po01eLineIndex, line in lines)', 'foreach (line in lines)')
            # After deleting diagnostics, all business tokens, order and counters match.
            self.assertEqual(re.sub(r'\s+', '', original), re.sub(r'\s+', '', stripped))

    def test_po01e_step_logged_branch_and_transient_state(self):
        code = body('po01c_regen.nut', 'OpexPO01CStep')
        self.assertIn('if (DECISION_LOG) {', code)
        logged = code[code.index('if (DECISION_LOG) {'):code.index('\n    } else {', code.index('local largest'))]
        self.assertIn('local largest = null;', logged)
        self.assertRegex(logged, r'local unitMark = OpexOpsMeasureBegin\(\);\s*PO01C_WORK_MARK = unitMark;\s*resume s.iterator;\s*local unitOps = OpexOpsMeasureEnd\(unitMark\);')
        self.assertIn('unitOps > PO01C_SLICE_OPS && (largest == null || unitOps > largest.ops)', logged)
        self.assertIn('idx = PO01C_WHERE.idx, ops = unitOps', logged)
        self.assertEqual(logged.count('OpexDecide("PO01C_UNIT"'), 1)
        self.assertIn('PO01C_WORK_MARK = OpexOpsMeasureBegin();\n        resume s.iterator;', code)
        self.assertNotIn('PO01C_WHERE', source('persist.nut'))
        self.assertIn('if (DECISION_LOG) {', body('po01c_regen.nut', 'OpexPO01CWhere'))
        mode = body('po01c_regen.nut', 'OpexPO01CGenerateMode')
        for site in ('before_first_yield', 'after_last_yield', 'OpexFreightCargoOrder', 'OpexProjectFromCandidate'):
            self.assertIn(site, mode)
        for helper, site in (('OpexPO01CLoggedTopK', 'OpexTopK'), ('OpexPO01CLoggedBands', 'OpexBands')):
            self.assertIn('DECISION_LOG ? ' + helper, mode)
            self.assertIn(site, body('po01c_regen.nut', helper))

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
            self.assertIn(level + '_value = 1', setting)
        self.assertEqual(source('settings.nut').count('GetSetting("po01c_regen_split")'), 1)
        self.assertIn('PO01C_REGEN_SPLIT <- true;', source('globals_pre.nut'))

    def test_generators_track_current_producers(self):
        self.assertEqual(source('po01c_generators.nut'), generated())

    def test_po01d_synchronous_path_bytes_unchanged(self):
        # Baseline origin/master 190b4ba1, rebased 23/10 onto c1b23cbb (V307S v3,
        # PO-02 precheck, PO-01c default 1; copied functions unaffected). Intentional later synchronous edits
        # must explicitly rebase this PO01D isolation contract, never regenerate it.
        expected = {
            'builder_water.nut': '92c50153b6712f238943f75e2c9498a602695132a7850c5f663f91344499162e',
            'air_planning.nut': 'c182f3f8fe82d0e39c11426d596a83ccad79a14ec486a1ebe148287790440e32',
            'air_sites.nut': '679b2912e9c71f708e6ad308ce187277f477f1751987405c74fb774998698fc4',
            'candidates.nut': '1f56d53670182f66b2c3d54360927e4be912ba65f4cdbffe1a04dff6dadd54ad',
            'catalog.nut': '4882c4c3de58c97882b2739432e62045a2e567b1ee980e5a2a56dedd34a17ba9',
            'main.nut': '81f077c68e094a0a9a8d4a63e1600af0fce0cdd9b9b835077e3da386d3b36ece',
            'probes.nut': 'ef0a1228e758e648736c89b9252dc9568f6b6a834065343e805570aed47788dd',
            'settings.nut': '580b8d9fd4997e6ec84a6c08ad51e02d6227c1de0d6b2411580cfb6c4306076d',
            'info.nut': '6eca938a429a092661801d8312d8738874bc6899a3beb3b74ebebc3fc94d205c',
        }
        for name, digest in expected.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((AI / name).read_bytes()).hexdigest(), digest)

        # PO03 ajoute exactement deux lignes dans _dispatchReactiveIntention.
        # Conserver la preuve byte-a-byte de tout le reste de orchestrator.nut :
        # seul ce fragment autorise est neutralise pour la comparaison SHA.
        # Cela refuse les changements secondaires de ce fichier, contrairement
        # a une rebaseline globale sur le nouveau SHA.
        guard = (
            b'    if (C77_INTENT_DEFER_SUBSIDY && PO01C_REGEN_SPLIT && '
            b'(this._po01cJob != null || this._po01cPending))\n'
            b'      blocked = true;\n'
        )
        orchestrator = (AI / 'orchestrator.nut').read_bytes()
        self.assertEqual(orchestrator.count(guard), 1, 'garde PO03 exactement une fois')
        dispatch = function(source('orchestrator.nut'), 'OpexAI::_dispatchReactiveIntention')
        self.assertIn(guard.decode('ascii'), dispatch)
        self.assertLess(dispatch.index(guard.decode('ascii')),
                        dispatch.index('if (C77_INTENT_DEFER_SUBSIDY && ("subsidyId" in deferPayload)'))
        self.assertEqual(
            hashlib.sha256(orchestrator.replace(guard, b'', 1)).hexdigest(),
            '1600953e477a5db49827d2f277ed965f4442a56ca32710f3c15a209a1b563ace'
        )

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
            code = unbudgeted_pax(body('po01c_generators.nut', 'OpexPO01C' + name))
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
            code = unbudgeted_pax(body('po01c_generators.nut', 'OpexPO01C' + caller))
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
