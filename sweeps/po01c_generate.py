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
    sources += [('catalog.nut', 'OpexCatalog::_refresh' + n) for n in
                ('Cargos', 'Rail', 'Towns', 'Industries', 'Air', 'Water', 'Road')]
    for file, name in sources:
        code = function((AI / file).read_text(), name)
        if name.startswith('OpexCatalog::'):
            code = code.replace(name + '()', 'OpexPO01C' + name.split('_refresh')[1] + '(catalog)', 1)
            code = code.replace('this.', 'catalog.')
            # Only the live catalogue may update C78's global town revisions.
            code = code.replace('  OpexC121CatalogSeedTownPopulations(catalog.towns);', '')
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
        pieces.append(code)
    pieces.extend(deep_copy(file, name) for file, name in DEEP_SOURCES)
    return '\n\n'.join(pieces) + '\n'


if __name__ == '__main__':
    (AI / 'po01c_generators.nut').write_text(generated())
