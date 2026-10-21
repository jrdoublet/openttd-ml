#!/usr/bin/env python3
"""V309 etape 0 : lire LOOP_OPS archives et C76_REGEN (si disponibles).

Les opcodes sleep_left sont une borne haute du budget reutilisable, pas une
mesure de tours inutiles. Sans la sonde V309 on ne peut pas reconstruire le
triplet revisions inchangees / meilleur projet stable / caisse insuffisante.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import re
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPCODE = ROOT / 'results/ac04v3_usage_B20x10_holdout_20261012_r1_opcode.json'
BLOCK_OPS = 430
BLOCKS_256 = 1024
REGEN = re.compile(r'\bOPEX (\d{4})-\d+-\d+ C76_REGEN\s+(.*)')
FIELDS = re.compile(r'([\w]+)=([^\s]+)')
MODES = ('rail', 'road', 'air', 'water', 'fleet')


def opcode_years(source, arm='reference'):
    data = json.loads(Path(source).read_text(encoding='utf-8'))
    if not data.get('valid') or not data.get('source_frozen'):
        raise ValueError('Archive d opcodes non valide ou source non figee')
    years = defaultdict(list)
    for name, annual in data['per_game_annual'].items():
        if not name.startswith(arm + ':'):
            continue
        for year, row in annual.items():
            if row.get('loop_posts', {}).get('_year') and 'sleep_left' in row.get('loop_posts', {}):
                years[int(year)].append(row)
    return {y: {
        'games': len(rows),
        'sleep_left_ops_mean': round(mean(r['sleep_left_ops'] for r in rows)),
        'executed_ops_mean': round(mean(r['loop_executed_ops'] for r in rows)),
        'loop_count_mean': round(mean(r['loop_posts']['sleep_left']['n'] for r in rows)),
        'sleep_left_pct_of_budget': round(100 * sum(r['sleep_left_ops'] for r in rows) /
                                          max(1, sum(r['sleep_left_ops'] + r['loop_executed_ops']
                                                     for r in rows)), 2),
        'sleep_block_equiv_mean': round(mean(r['sleep_left_ops'] for r in rows) / BLOCK_OPS),
        'maps_256_equiv_upper_bound': round(mean(r['sleep_left_ops'] for r in rows) /
                                          (BLOCK_OPS * BLOCKS_256), 2),
        'useless_loops_pct': None,
        'useless_loop_ops': None,
        'cash_below_cheapest_selected_days': None,
    } for y, rows in sorted(years.items())}


def read_regen_logs(directory):
    """Only count proven 100%-same candidate keys; keep missing keys unknown."""
    stats = defaultdict(lambda: Counter())
    logs = sorted(Path(directory).glob('reference_seed*_r0.log*'))
    for log in logs:
        opener = gzip.open if log.suffix == '.gz' else open
        with opener(log, 'rt', encoding='utf-8', errors='replace') as stream:
            for line in stream:
                m = REGEN.search(line)
                if not m:
                    continue
                f = dict(FIELDS.findall(m.group(2)))
                if f.get('phase') != 'regen':
                    continue
                year = int(m.group(1))
                rec = stats[year]
                rec['regens'] += 1
                try:
                    ops = int(f['ops'])
                except (KeyError, ValueError):
                    rec['missing_ops'] += 1
                    continue
                rec['regen_ops'] += ops
                seen = [f.get('cand_' + mode + '_same_keys_pct') for mode in MODES]
                if all(v is not None for v in seen) and f.get('best_same_top1') is not None:
                    rec['measured_keys'] += 1
                    if all(float(v) >= 100.0 for v in seen) and f['best_same_top1'] == '1':
                        rec['fully_same_keys_and_top1'] += 1
                        rec['fully_same_ops'] += ops
                else:
                    rec['missing_comparability'] += 1
    return len(logs), {y: dict(row) for y, row in sorted(stats.items())}


def analyse(opcode, logs=None, arm='reference'):
    annual = opcode_years(opcode, arm)
    n_logs, regeneration = read_regen_logs(logs) if logs else (0, {})
    for year in annual:
        annual[year]['regen'] = regeneration.get(year, {})
        annual[year]['select_ops_with_same_keys'] = None
    return {
        'opcode_source': str(opcode), 'arm': arm, 'annual': annual,
        'regen_log_files': n_logs, 'regen_events_by_year': regeneration,
        'missing': {
            'idle_loops': 'sonde V309_IDLE absente : aucune conjunction des trois conditions par tour',
            'money_wait_days': 'caisse et cout minimal du portefeuille non synchronises quotidiennement',
            'select_ops_unchanged': 'pub.select ne fournit pas le meme instant de comparaison des cles',
            'regen_if_empty': 'C76_REGEN/cand_*_same_keys_pct absents des journaux fournis' if not regeneration else None,
        },
        'caveat': 'sleep_left est un budget theorique maximal reutilisable avant Sleep(1), et non une mesure de travail inutile ou de temps economiquement disponible; les compteurs sont des flushs annuels et la derniere annee peut manquer',
    }


def render(result):
    print('Archive', result['opcode_source'], '| bras', result['arm'],
          '| journaux regen', result['regen_log_files'])
    print('| Annee | Parties | Sleep, Mops/partie | Part du budget | Boucles/partie | Blocs V308 possibles (plafond) | Cartes 256² equivalentes | Regens cles identiques |')
    print('|---|---:|---:|---:|---:|---:|---:|---:|')
    for y, r in result['annual'].items():
        rg = r['regen']
        cells = f"{rg.get('fully_same_keys_and_top1', 0)}/{rg['measured_keys']}" if rg.get('measured_keys') else 'non mesurable'
        print(f"| {y} | {r['games']} | {r['sleep_left_ops_mean']/1e6:.2f} | "
              f"{r['sleep_left_pct_of_budget']:.2f} % | {r['loop_count_mean']:,} | "
              f"{r['sleep_block_equiv_mean']:,} | {r['maps_256_equiv_upper_bound']:.2f} | {cells} |")
    print('Tours inutiles (%) : non mesurables. Jours sous le cout minimal : non mesurables.')
    print('Limites:', '; '.join(str(x) for x in result['missing'].values() if x))


def selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'opcode.json'
        p.write_text(json.dumps({'valid': True, 'source_frozen': True,
                                 'per_game_annual': {'reference:42': {'1970': {
                                     'sleep_left_ops': 860, 'loop_executed_ops': 3440,
                                     'loop_posts': {'_year': {'n': 1}, 'sleep_left': {'n': 2}}}}}}),
                     encoding='utf-8')
        row = opcode_years(p)[1970]
        assert row['sleep_block_equiv_mean'] == 2
        assert row['sleep_left_pct_of_budget'] == 20.0
        assert row['useless_loops_pct'] is None
    print('selftest OK')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--opcode-json', type=Path, default=DEFAULT_OPCODE)
    ap.add_argument('--logs', type=Path, help='Optionnel : logs de reference avec C76_REGEN')
    ap.add_argument('--arm', default='reference')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    result = analyse(args.opcode_json, args.logs, args.arm)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        render(result)


if __name__ == '__main__':
    main()
