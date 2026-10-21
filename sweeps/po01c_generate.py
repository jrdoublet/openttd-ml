"""Mechanical resumable copies of current producers (checked by contracts)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / 'ai/OpexAI'


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
        pieces.append(code)
    return '\n\n'.join(pieces) + '\n'


if __name__ == '__main__':
    (AI / 'po01c_generators.nut').write_text(generated())
