"""Mechanical resumable copies of current producers (checked by contracts)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / 'ai/OpexAI'

# PO01D: only these private copies suspend; the synchronous sources stay intact.
DEEP_SOURCES = [('builder_water.nut', 'OpexWaterFindConnection')]
DEEP_SOURCES += [('air_sites.nut', 'OpexAirFindSite' + suffix) for suffix in
                 ('', 'Listed', 'CatchmentListed')]
DEEP_SOURCES += [('air_planning.nut', 'OpexAirPlans' + suffix) for suffix in
                 ('', 'StepFindSites', 'FindSites', 'HubDiscoveryPhase', 'DiscoverHubs')]


def bridge(code, statement, callee, arguments, result=None):
    """Replace one statement, retaining its scope and its evaluation position."""
    if code.count(statement) != 1:
        raise ValueError((callee, statement))
    replacement = ('local po01dBox = { value = null };\n'
                   f'    local po01dChild = OpexPO01C{callee[4:]}(po01dBox, {arguments});\n'
                   '    while (po01dChild.getstatus() != "dead") {\n'
                   '      resume po01dChild;\n'
                   '      yield null; // PO01C_CHECKPOINT\n'
                   '    }')
    # A local result must remain visible in the caller's original scope.
    if result is not None:
        replacement += '\n    ' + result + ' = po01dBox.value;'
    else:
        replacement = '{\n    ' + replacement + '\n    }'
    return code.replace(statement, replacement)


def deep_copy(file, name):
    code = function((AI / file).read_text(encoding='utf-8'), name)
    code = code.replace(name + '(', 'OpexPO01C' + name[4:] + '(po01dResult, ', 1)
    # Returns use an explicit result box: null is a valid result, never a checkpoint.
    tokens = list(re.finditer(r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*|\breturn\b|;', code))
    edits = []
    for i, token in enumerate(tokens):
        if token[0] != 'return':
            continue
        end = next(t for t in tokens[i + 1:] if t[0] == ';')
        expr = code[token.end():end.start()].strip()
        edits.append((token.start(), end.end(),
                      '{ po01dResult.value = ' + expr + '; return; }' if expr else 'return;'))
    for start, end, value in reversed(edits):
        code = code[:start] + value + code[end:]
    # Same iteration order, including rejected elements/continue paths. Never yield
    # inside an AITestMode scope: all selected loops enclose complete test commands.
    code = re.sub(r'((?:for|foreach|while)\s*\([^\n]*\)\s*\{)',
                  r'\1\n    yield null; // PO01C_CHECKPOINT\n', code)
    if name == 'OpexAirFindSite':
        args = 'town, airport, probes, requiredSlotTownId, key, useSiteCache'
        statement = '{ po01dResult.value = OpexAirFindSiteCatchmentListed(' + args + ').site; return; }'
        code = bridge(code, statement, 'OpexAirFindSiteCatchmentListed', args,
                      'local po01dSiteResult')
        code = code.replace('local po01dSiteResult = po01dBox.value;',
                            'po01dResult.value = po01dBox.value.site; return;')
    elif name == 'OpexAirFindSiteCatchmentListed':
        args = 'town, airport, probes, requiredSlotTownId, key, useSiteCache'
        statement = '{ po01dResult.value = OpexAirFindSiteListed(' + args + '); return; }'
        code = bridge(code, statement, 'OpexAirFindSiteListed', args, 'po01dResult.value')
        code = code.replace('po01dResult.value = po01dBox.value;',
                            'po01dResult.value = po01dBox.value; return;')
    elif name in ('OpexAirPlansFindSites', 'OpexAirPlansDiscoverHubs'):
        variable = 'site' if name.endswith('FindSites') else 'extraSite'
        probes = 'probes' if variable == 'site' else 'hubProbes'
        args = f'towns[i], airport, {probes}, c83RequiredSlotTown'
        code = bridge(code, f'local {variable} = OpexAirFindSite({args});',
                      'OpexAirFindSite', args, 'local ' + variable)
    elif name == 'OpexAirPlansHubDiscoveryPhase':
        args = 'ctx, combo, airport, plane'
        code = bridge(code, 'OpexAirPlansDiscoverHubs(' + args + ');',
                      'OpexAirPlansDiscoverHubs', args)
    elif name == 'OpexAirPlansStepFindSites':
        statement = ('local sitesOk = V278_AIR_LAZY_SITES && OpexV278LazyEnabled(ctx)\n'
                     '      ? OpexV278LazySites(ctx, comboIndex, combo, airport, plane)\n'
                     '      : OpexAirPlansFindSites(ctx, comboIndex, combo, airport, plane, resumingCombo);')
        args = 'ctx, comboIndex, combo, airport, plane, resumingCombo'
        replacement = ('local sitesOk;\n'
                       '  if (V278_AIR_LAZY_SITES && OpexV278LazyEnabled(ctx)) {\n'
                       '    sitesOk = OpexV278LazySites(ctx, comboIndex, combo, airport, plane);\n'
                       '  } else {\n    CHILD\n  }')
        replacement = bridge(replacement, 'CHILD', 'OpexAirPlansFindSites', args, 'sitesOk')
        if code.count(statement) != 1:
            raise ValueError(name)
        code = code.replace(statement, replacement)
    elif name == 'OpexAirPlans':
        args = 'ctx, comboIndex, combo, airport, plane, resumingCombo'
        code = bridge(code, 'local sitesOk = OpexAirPlansStepFindSites(' + args + ');',
                      'OpexAirPlansStepFindSites', args, 'local sitesOk')
        args = 'ctx, comboIndex, combo, airport, plane'
        code = bridge(code, 'OpexAirPlansHubDiscoveryPhase(' + args + ');',
                      'OpexAirPlansHubDiscoveryPhase', args)
    return code


def function(text, name):
    start = text.index('function ' + name + '(')
    opening = text.index('{', start)
    depth = 0
    for m in re.finditer(r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*|[{}]', text[opening:]):
        if m[0] == '{':
            depth += 1
        elif m[0] == '}':
            depth -= 1
            if depth == 0:
                return text[start:opening + m.end()]
    raise ValueError(name)


def generated():
    pieces = ['/* Mechanical copies: python3 sweeps/po01c_generate.py.\n'
              ' * Checkpoints retain VM locals; no captured closures. Never saved. */']
    sources = [('candidates.nut', n) for n in
               ('OpexPaxCandidates', 'OpexFreightCandidates', 'OpexRoadFreightCandidates')]
    sources += [('builder_water.nut', 'OpexWaterPlans')]
    # R08: the unused PO01CCargos copy was deleted; the live catalogue owns cargos.
    sources += [('catalog.nut', 'OpexCatalog::_refresh' + n) for n in
                ('Rail', 'Towns', 'Industries', 'Air', 'Water', 'Road')]
    for file, name in sources:
        code = function((AI / file).read_text(encoding='utf-8'), name)
        if name.startswith('OpexCatalog::'):
            code = code.replace(name + '()', 'OpexPO01C' + name.split('_refresh')[1] + '(catalog)', 1)
            code = code.replace('this.', 'catalog.')
            # Only the live catalogue may update C78's global town revisions.
            code = code.replace('  OpexC121CatalogSeedTownPopulations(catalog.towns);', '')
            if name == 'OpexCatalog::_refreshRail':
                # L3 native sort is synchronous; PO01C must keep a yield per type.
                old = ('  /* OPCODE-AILIST L3 : la cle de tri native est l\'ID, pas la valeur disponible=1.\n'
                       '   * Ainsi Begin() rend exactement le maximum numerique choisi historiquement. */\n'
                       '  types.Sort(AIList.SORT_BY_ITEM, AIList.SORT_DESCENDING);\n'
                       '  local chosen = types.IsEmpty() ? -1 : types.Begin();')
                new = ('  local chosen = -1;\n'
                       '  for (local t = types.Begin(); !types.IsEnd(); t = types.Next()) {\n'
                       '    if (OpexRailTypePreferred(t, chosen)) chosen = t;\n'
                       '  }')
                if code.count(old) != 1:
                    raise ValueError('PO01C Rail L3 source diverged')
                code = code.replace(old, new)
            if name == 'OpexCatalog::_refreshIndustries':
                # R02 invalidation belongs to the live full catalogue refresh.
                # PO01C is a private incremental snapshot, never used for V276.
                old = ('  /* Les producteurs et les volumes qui ordonnent V276 viennent de ce catalogue. */\n'
                       '  V276_CARGO_ORDER = null;\n')
                if code.count(old) != 1:
                    raise ValueError('PO01C Industries R02 source diverged')
                code = code.replace(old, '')
            if name == 'OpexCatalog::_refreshAir':
                # L5 prefilters the synchronous list once. PO01C retains its
                # historical per-airport, per-engine rejection and checkpoints.
                old = ('  /* OPCODE-AILIST L5 : refit passagers evalue une seule fois en natif sur la\n'
                       '   * liste deja construite, avant les parcours repetes par type d\'aeroport. */\n'
                       '  engines.Valuate(AIEngine.CanRefitCargo, catalog.paxCargo);\n'
                       '  engines.KeepValue(1);\n')
                if code.count(old) != 1:
                    raise ValueError('PO01C Air L5 source diverged')
                code = code.replace(old, '')
                old = '      local planeType = AIEngine.GetPlaneType(e);'
                if code.count(old) != 2:
                    raise ValueError('PO01C Air L5 loops diverged')
                code = code.replace(old, ('      if (!AIEngine.CanRefitCargo(e, catalog.paxCargo)) continue;\n'
                                          + old))
        else:
            code = code.replace(name, 'OpexPO01C' + name[4:], 1)
        if name == 'OpexWaterPlans':
            code = code.replace('return null;', 'return;').replace('return best;', 'return;')
        code = re.sub(r'((?:for|foreach|while)\s*\([^\n]*\)\s*\{)',
                      r'\1\n    yield null; // PO01C_CHECKPOINT', code)
        if name == 'OpexWaterPlans':
            code = bridge(code,
                          'navigableDistance = OpexWaterFindConnection(sites[a], sites[b]);',
                          'OpexWaterFindConnection', 'sites[a], sites[b]', 'navigableDistance')
        if name in ('OpexPaxCandidates', 'OpexFreightCandidates', 'OpexRoadFreightCandidates'):
            code = unit_sites(code, name)
        if name == 'OpexPaxCandidates':
            code = code.replace('targetId = -1)', 'targetId = -1, po01gDiagnostics = null)', 1)
            opening = ('\n{\n  local po01fSitableCache = clone ::OpexSitableCache;\n'
                       '  local po01fOriginal = V216_COVER;\n'
                       '  // Private for the entire producer: intervening consumers cannot seed later pairs.\n'
                       '  // One cache epoch per producer, not per pair: suspension must not invalidate it.\n'
                       '  local po01fContext = { used = false, now = AIDate.GetCurrentDate(),\n'
                       '    diagnostics = po01gDiagnostics, cover = {\n'
                       '    ownMonth = po01fOriginal.ownMonth, advQuarter = po01fOriginal.advQuarter,\n'
                       '    own = po01fOriginal.own, adv = clone po01fOriginal.adv,\n'
                       '    cache = clone po01fOriginal.cache } };\n')
            code = code.replace('\n{\n', opening, 1)
            statement = ('local candidate = OpexMakeCandidate(catalog, "pax", cargo, towns[a].tile, towns[b].tile,\n'
                         '                                          monthly, false, stats, false, candidateProfile, cruiseCache,\n'
                         '                                          secondary);')
            code = bridge(code, statement, 'OpexMakePaxCandidate',
                          'po01fSitableCache, po01fContext, catalog, "pax", cargo, towns[a].tile, towns[b].tile, monthly, false, stats, '
                          'false, candidateProfile, cruiseCache, secondary', 'local candidate')
            code = code[:-1] + ('  ::OpexSitableCache = po01fSitableCache;\n'
                                '  if (po01fContext.used) V216_COVER = po01fContext.cover;\n}')
        pieces.append(code)
    pieces.extend(deep_copy(file, name) for file, name in DEEP_SOURCES)
    pieces.extend(pax_copies())
    # PO01H: a completed child has no suspended work to propagate. Keep the
    # terminal checkpoint in the source (so these remain generators), but only
    # unwind a live child. Apply the budget gate to PAX's actual work sites,
    # never to a propagation checkpoint: a live child's yield must reach Step.
    for i, code in enumerate(pieces):
        if code.startswith('function OpexPO01CPaxCandidates(') or any(
                code.startswith('function OpexPO01C' + n + '(') for n in
                ['MakePaxCandidate'] + [name[4:] for _, name in PAX_SOURCES[1:]]):
            pieces[i] = budgeted_pax(code)
    return '\n\n'.join(pieces) + '\n'


def budgeted_pax(code):
    """No business edits: gate work checkpoints, propagate only live children.

    The shared mark is reset by Step immediately before each root resume, so
    time/opcodes spent by other planners between slices are never charged here.
    Inner tile loops still test once per 32 visits, including rejected visits.
    """
    forwarding = 'resume po01dChild;\n      yield null; // PO01C_CHECKPOINT'
    code = code.replace(forwarding, 'resume po01dChild;\n      PO01H_FORWARD;')
    # Move the optional work-site diagnostic inside the gate as well; otherwise
    # logging would still execute at every row even when it does not suspend.
    code = re.sub(r'yield null; // PO01C_CHECKPOINT'
                  r'(\s*if \(DECISION_LOG\) OpexPO01CWhere\([^;]*\);)?',
                  lambda m: 'if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {\n'
                  '      yield null; // PO01C_CHECKPOINT'
                  + (m[1] or '') + '\n    }', code)
    return code.replace('PO01H_FORWARD;',
                        'if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT')


# PO01F: coverage, not station planning, is reachable from candidate admission.
PAX_SOURCES = [('candidates.nut', 'OpexMakeCandidate'),
               ('candidates.nut', 'OpexRailOriginSitable')]
PAX_SOURCES += [('probe_v216.nut', 'OpexV216' + suffix) for suffix in
                ('MarkRect', 'RefreshCover', 'AdvAround', 'Coverage', 'GainPct',
                 'aEndPct', 'aScaleDemand')]


def pax_copies():
    for file, name in PAX_SOURCES:
        code = deep_copy(file, name)
        if name.startswith('OpexV216'):
            code = code.replace('(po01dResult, ', '(po01dResult, po01fContext, ', 1)
            # Empty historical signature.
            code = code.replace('po01fContext, )', 'po01fContext)')
        if name == 'OpexMakeCandidate':
            code = code.replace('OpexPO01CMakeCandidate(', 'OpexPO01CMakePaxCandidate(', 1)
            code = code.replace('(po01dResult, catalog,', '(po01dResult, po01fSitableCache, po01fContext, catalog,', 1)
            code = code.replace('::OpexSitableCache', 'po01fSitableCache')
            # The producer owns the epoch, including all pairs and PASS/MAIL.
            code = code.replace('po01fSitableCache[sitableKey] <- sitable;',
                                'po01fSitableCache[sitableKey] <- sitable;\n'
                                '      if (DECISION_LOG && po01fContext.diagnostics != null)\n'
                                '        po01fContext.diagnostics.sitableFills++;')
            code = code.replace('if (V216A_GHOST_DEMAND > 0 && kind == "pax") {',
                                'if (V216A_GHOST_DEMAND > 0 && kind == "pax") {\n    po01fContext.used = true;')
            code = bridge(code, 'sitable = OpexRailOriginSitable(srcTile, cargo, catalog.railCoverage, true);',
                          'OpexRailOriginSitable', 'srcTile, cargo, catalog.railCoverage, true', 'sitable')
            code = bridge(code, 'monthly = OpexV216aScaleDemand(srcTile, dstTile, cargo, monthly);',
                          'OpexV216aScaleDemand', 'po01fContext, srcTile, dstTile, cargo, monthly', 'monthly')
            statement = ('if (secondary != null)\n      secondary = { cargo = secondary.cargo,\n'
                         '                    monthly = OpexV216aScaleDemand(srcTile, dstTile, secondary.cargo, secondary.monthly) };')
            replacement = 'if (secondary != null) {\n      CHILD\n      secondary = { cargo = secondary.cargo, monthly = po01fMail };\n    }'
            replacement = bridge(replacement, 'CHILD', 'OpexV216aScaleDemand',
                                 'po01fContext, srcTile, dstTile, secondary.cargo, secondary.monthly', 'local po01fMail')
            assert statement in code
            code = code.replace(statement, replacement)
        elif name == 'OpexV216RefreshCover':
            code = code.replace('local now = AIDate.GetCurrentDate();', 'local now = po01fContext.now;')
            code = code.replace('local cover = V216_COVER;', 'local cover = po01fContext.cover;')
            code = code.replace('cover.ownMonth = ym;',
                                'cover.ownMonth = ym;\n'
                                '  if (DECISION_LOG && po01fContext.diagnostics != null)\n'
                                '    po01fContext.diagnostics.coverRebuilds++;')
            code = code.replace('AIStation.STATION_TRUCK_STOP, AIStation.STATION_DOCK]) {',
                                'AIStation.STATION_TRUCK_STOP, AIStation.STATION_DOCK]) {\n    yield null; // PO01C_CHECKPOINT')
            statement = 'if (x1 >= 0) OpexV216MarkRect(cover.own, x0 - r, y0 - r, x1 + r, y1 + r, ratings);'
            replacement = bridge('CHILD', 'CHILD', 'OpexV216MarkRect',
                                 'po01fContext, cover.own, x0 - r, y0 - r, x1 + r, y1 + r, ratings')
            code = code.replace(statement, 'if (x1 >= 0) ' + replacement)
        elif name == 'OpexV216AdvAround':
            statement = ('OpexV216MarkRect(table, x - r > cx - radius ? x - r : cx - radius,\n'
                         '        y - r > cy - radius ? y - r : cy - radius,\n'
                         '        x + r < cx + radius ? x + r : cx + radius,\n'
                         '        y + r < cy + radius ? y + r : cy + radius, null);')
            code = bridge(code, statement, 'OpexV216MarkRect',
                          'po01fContext, ' + statement[len('OpexV216MarkRect('):-2])
        elif name == 'OpexV216Coverage':
            code = bridge(code, 'local cover = OpexV216RefreshCover();',
                          'OpexV216RefreshCover', 'po01fContext', 'local cover')
            # Separate scopes avoid duplicate child/box local declarations.
            code = code.replace('local adv = OpexV216AdvAround(cover, center, radius);',
                                'local adv;\n  { CHILD }')
            code = bridge(code, 'CHILD', 'OpexV216AdvAround',
                          'po01fContext, cover, center, radius', 'adv')
        elif name in ('OpexV216GainPct', 'OpexV216aEndPct'):
            code = bridge(code, 'local c = OpexV216Coverage(center, cargo, radius);',
                          'OpexV216Coverage', 'po01fContext, center, cargo, radius', 'local c')
            if name == 'OpexV216aEndPct':
                statement = '{ po01dResult.value = OpexV216GainPct(center, cargo, radius, V216A_RN); return; }'
                replacement = bridge('CHILD', 'CHILD', 'OpexV216GainPct',
                                     'po01fContext, center, cargo, radius, V216A_RN', 'po01dResult.value')
                code = code.replace(statement, '{ ' + replacement + ' return; }')
        elif name == 'OpexV216aScaleDemand':
            statement = 'local pct = (OpexV216aEndPct(srcTile, cargo, radius) + OpexV216aEndPct(dstTile, cargo, radius)) / 2;'
            replacement = 'local po01fSrc, po01fDst;\n  { SRC }\n  { DST }\n  local pct = (po01fSrc + po01fDst) / 2;'
            replacement = bridge(replacement, 'SRC', 'OpexV216aEndPct',
                                 'po01fContext, srcTile, cargo, radius', 'po01fSrc')
            replacement = bridge(replacement, 'DST', 'OpexV216aEndPct',
                                 'po01fContext, dstTile, cargo, radius', 'po01fDst')
            code = code.replace(statement, replacement)
        # Forwarders retain the deepest site; only actual loop bodies set a new site.
        gen = 'OpexPO01CMakePaxCandidate' if name == 'OpexMakeCandidate' else 'OpexPO01C' + name[4:]
        code = re.sub(r'((?:for|foreach)\s*\([\s\S]*?\)\s*\{\s*yield null; // PO01C_CHECKPOINT)',
                      lambda m: m[0] + '\n    if (DECISION_LOG) OpexPO01CWhere("' + gen + '", "pax:' + name[4:] + '", -1);', code)
        # A tile used to unwind up to eight generators plus the measured root
        # loop. Amortize that cost; keep outer checkpoints and check BEFORE any
        # continue. At most 32 innermost iterations between checkpoints.
        inner = {
            'OpexV216MarkRect': 'for (local y = y0; y <= y1; y++)',
            'OpexV216Coverage': 'for (local y = cy - radius; y <= cy + radius; y++)',
            'OpexRailOriginSitable': 'for (local dy = -r; dy <= r; dy++)',
        }.get(name)
        if inner is not None:
            code = code.replace('\n{\n', '\n{\n  local po01gWork = 0;\n', 1)
            checkpoint = ('yield null; // PO01C_CHECKPOINT\n'
                          '    if (DECISION_LOG) OpexPO01CWhere("' + gen + '", "pax:' + name[4:] + '", -1);')
            old = inner + ' {\n    ' + checkpoint
            assert code.count(old) == 1
            code = code.replace(old, inner + ' {\n    if (++po01gWork % 32 == 0) {\n    '
                                + checkpoint + '\n    }')
        if name == 'OpexMakeCandidate':
            for call in ('OpexLineEconomics', 'OpexM3ProbeRailEquipment'):
                code = re.sub(r'(?m)^(\s*)((?:local economics = )?' + call + r'\()',
                              lambda m: m[1] + 'if (DECISION_LOG) OpexPO01CWhere("' + gen + '", "pax:' + call[4:] + '", -1);\n' + m[1] + m[2], code)
        yield code


def unit_sites(code, name):
    """Telemetry only: mark AFTER a yield, never attribute work to the next pair.

    idx is the existing loop index/key (source/town index or cargo ID). -1 means
    outside a loop. The single unindexed line loop gets its array index explicitly.
    No added checkpoint, changed filter, or changed historical call.
    """
    gen = 'OpexPO01C' + name[4:]
    prefix = {'OpexPaxCandidates': 'rail_pax', 'OpexFreightCandidates': 'rail_freight',
              'OpexRoadFreightCandidates': 'road_freight'}[name]
    def mark(site, idx='-1'):
        return f'if (DECISION_LOG) OpexPO01CWhere("{gen}", "{site}", {idx});'
    code = code.replace('\n{\n', '\n{\n  ' + mark('before_first_yield') + '\n', 1)
    code = code.replace('foreach (line in lines)', 'foreach (po01eLineIndex, line in lines)')
    loop_sites = {
        'OpexPaxCandidates': [('air_lines', 'po01eLineIndex'), ('production', 'i'),
                             ('mail', 'i'), ('neighbors', 'a'), ('pair', 'b')],
        'OpexFreightCandidates': [('service', 'i'), ('cargo', 'cargo'), ('source', 'si'),
                                 ('industry_pair', 'k'), ('town_pair', 'k')],
        'OpexRoadFreightCandidates': [('industry_service', 'i'), ('town_service', 'i'),
                                     ('cargo', 'cargo'),
                                     ('cargo_industry_service', '-1'), ('cargo_town_service', '-1'),
                                     ('source', 'si'),
                                     ('rejected_industry', 'di'), ('rejected_town', 'ti'),
                                     ('industry_pair', 'k'), ('town_probe', 'ti'), ('town_pair', 'k')],
    }[name]
    checkpoints = iter(loop_sites)
    def checkpoint(m):
        site, idx = next(checkpoints)
        return m[0] + '\n    ' + mark(prefix + ':' + site, idx)
    code = re.sub(r'yield null; // PO01C_CHECKPOINT', checkpoint, code)
    assert next(checkpoints, None) is None
    # Last historical call reached within the unit. Keep its index from the loop.
    calls = ('OpexMakeCandidate', 'OpexMakeRoadCandidate', 'OpexRoadFreightAcceptedTowns',
             'OpexRoadFreightServedIndex', 'OpexV264EmitConvergent', 'OpexCatalogBounds')
    for call in calls:
        site = 'pair_candidate' if call in ('OpexMakeCandidate', 'OpexMakeRoadCandidate') else call
        pattern = r'(?m)^(\s*)(local \w+ = ' + call + r'\()'
        code = re.sub(pattern, lambda m: m[1] + mark(prefix + ':' + site, 'PO01C_WHERE.idx')
                      + '\n' + m[1] + m[2], code)
    for call in ('grid.Build', 'grid.GetCandidatesFor'):
        pattern = r'(?m)^(\s*)((?:local \w+ = )?' + re.escape(call) + r'\()'
        code = re.sub(pattern, lambda m: m[1] + mark(prefix + ':' + call, 'PO01C_WHERE.idx')
                      + '\n' + m[1] + m[2], code)
    # Even early exits identify the terminal checkpoint; never retain another generator.
    code = code.replace('return;', '{ ' + mark('after_last_yield', 'PO01C_WHERE.idx') + ' return; }')
    return code[:-1] + '  ' + mark('after_last_yield', 'PO01C_WHERE.idx') + '\n}'


if __name__ == '__main__':
    (AI / 'po01c_generators.nut').write_text(generated())
