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
import hashlib
import json
from pathlib import Path
import re
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPCODE = ROOT / 'results/ac04v3_usage_B20x10_holdout_20261012_r1_opcode.json'
BLOCK_OPS = 430
BLOCKS_256 = 1024
REGEN = re.compile(r'\bOPEX (\d{4})-\d+-\d+ C76_REGEN\s+(.*)')
IDLE = re.compile(r'\bOPEX (\d{4})-(\d{1,2})-\d{1,2} V309_IDLE\s+(.*)')
FIELDS = re.compile(r'([\w]+)=([^\s]+)')
MODES = ('rail', 'road', 'air', 'water', 'fleet')
IDLE_CORE_FIELDS = ('loops', 'useless', 'useless_ops', 'sleep_ops', 'blocks')


def _valid_idle_core(fields):
    """Return comparable core counters, or None for an invalid monthly flush."""
    try:
        values = {name: int(fields[name]) for name in IDLE_CORE_FIELDS}
    except (KeyError, ValueError):
        return None
    if (values['loops'] < 0 or not 0 <= values['useless'] <= values['loops']
            or any(values[name] < 0 for name in
                   ('useless_ops', 'sleep_ops', 'blocks'))):
        return None
    return values


def _idle_monthly_rows(path):
    """Compare unique observed months, tolerating repeated flushes in one log."""
    months = {}
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8', errors='replace') as stream:
        for line in stream:
            event = IDLE.search(line)
            if event is not None:
                fields = dict(FIELDS.findall(event.group(3)))
                if _valid_idle_core(fields) is None:
                    continue
                key = (int(event.group(1)), int(event.group(2)))
                months.setdefault(key, fields)
    return months


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
    logs = sorted(p for p in Path(directory).glob('reference_seed*_r0.log*')
                  if re.fullmatch(r'reference_seed\d+_r0\.log(?:\.gz)?', p.name))
    source_hashes = {}
    for log in logs:
        base = log.name[:-3] if log.name.endswith('.gz') else log.name
        local_stats = defaultdict(Counter)
        digest = hashlib.sha256()
        opener = gzip.open if log.suffix == '.gz' else open
        with opener(log, 'rt', encoding='utf-8', errors='replace') as stream:
            for line in stream:
                digest.update(line.encode('utf-8'))
                m = REGEN.search(line)
                if not m:
                    continue
                f = dict(FIELDS.findall(m.group(2)))
                if f.get('phase') != 'regen':
                    continue
                year = int(m.group(1))
                rec = local_stats[year]
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
        fingerprint = digest.digest()
        if base in source_hashes:
            if source_hashes[base] != fingerprint:
                raise ValueError(f'copies de partie contradictoires : {base}')
            continue
        source_hashes[base] = fingerprint
        for year, rec in local_stats.items():
            stats[year].update(rec)
    return len(source_hashes), {y: dict(row) for y, row in sorted(stats.items())}


def read_idle_logs(directory):
    """Read PASSIVE monthly V309 observations, never extrapolate missing months.

    Expected fields: loops, useless, useless_ops, sleep_ops, wait_days, blocks.
    wait_days=-1 means unavailable (nonpositive net profit / absent data).
    cash_below_days is optional for legacy fixtures, not silently zeroed when missing.
    Each arm and year remain distinct; the source year/date is reported as-is.
    """
    grouped = defaultdict(lambda: defaultdict(lambda: {
        'months': set(), 'loops': 0, 'useless': 0, 'useless_ops': 0,
        'sleep_ops': 0, 'waits': [], 'blocks': 0, 'unavailable_waits': 0,
        'cash_below_days': 0, 'cash_below_days_observations': 0,
        'unknown_cost_loops': 0, 'unfunded_cost_loops': 0,
        'cost_source_observations': 0, 'capped_wait_months': 0,
        'stable_unfunded_loops': 0, 'stable_unfunded_ops': 0,
        'stable_unfunded_observations': 0,
    }))
    seen_months = set()
    first_copy_by_game = {}
    logs = sorted(p for p in Path(directory).glob('*.log*')
                  if re.search(r'_seed\d+_r\d+\.log(?:\.gz)?$', p.name))
    for log in logs:
        base = log.name[:-3] if log.name.endswith('.gz') else log.name
        if base in first_copy_by_game:
            original = _idle_monthly_rows(first_copy_by_game[base])
            duplicate = _idle_monthly_rows(log)
            if (not (original.keys() <= duplicate.keys() or duplicate.keys() <= original.keys())
                    or any(original[month] != duplicate[month]
                           for month in original.keys() & duplicate.keys())):
                raise ValueError(f'copies de partie contradictoires : {base}')
        else:
            first_copy_by_game[base] = log
        arm = re.sub(r'_seed\d+_r\d+\.log(?:\.gz)?$', '', log.name)
        match = re.search(r'_seed(\d+)_r(\d+)', log.name)
        stream_id = (arm, match.group(1), match.group(2)) if match else (arm, log.name)
        opener = gzip.open if log.suffix == '.gz' else open
        with opener(log, 'rt', encoding='utf-8', errors='replace') as stream:
            for line in stream:
                event = IDLE.search(line)
                if event is None:
                    continue
                year, month = int(event.group(1)), int(event.group(2))
                fields = dict(FIELDS.findall(event.group(3)))
                values = _valid_idle_core(fields)
                if values is None:
                    continue
                # One monthly flush per game; ignore duplicate replayed records
                # and .log/.log.gz copies rather than inflating annual totals.
                observation = (*stream_id, year, month)
                if observation in seen_months:
                    continue
                seen_months.add(observation)
                row = grouped[arm][year]
                row['months'].add((stream_id, month))
                for key, value in values.items():
                    row[key] += value
                try:
                    row['cash_below_days'] += max(0, int(fields['cash_below_days']))
                    row['cash_below_days_observations'] += 1
                except (KeyError, ValueError):
                    pass
                try:
                    unknown = int(fields['unknown_cost_loops'])
                    unfunded = int(fields['unfunded_cost_loops'])
                    if unknown < 0 or unfunded < 0 or unknown + unfunded > values['loops']:
                        raise ValueError('invalid cost source counters')
                    row['unknown_cost_loops'] += unknown
                    row['unfunded_cost_loops'] += unfunded
                    row['cost_source_observations'] += 1
                except (KeyError, ValueError):
                    pass  # Ne jamais assimiler une source manquante à zéro.
                try:
                    stable = int(fields['stable_unfunded_loops'])
                    stable_ops = int(fields['stable_unfunded_ops'])
                    if not 0 <= stable <= values['loops'] or stable_ops < 0:
                        raise ValueError('invalid stable unfunded counters')
                    row['stable_unfunded_loops'] += stable
                    row['stable_unfunded_ops'] += stable_ops
                    row['stable_unfunded_observations'] += 1
                except (KeyError, ValueError):
                    pass
                if fields.get('wait_capped') == '1':
                    row['capped_wait_months'] += 1
                try:
                    days = int(fields['wait_days'])
                except (KeyError, ValueError):
                    days = -1
                if days >= 0:
                    row['waits'].append(days)
                else:
                    row['unavailable_waits'] += 1
    return {arm: {year: {
        'months': len(row['months']),
        'loops': row['loops'], 'useless': row['useless'],
        'useless_pct': round(100.0 * row['useless'] / row['loops'], 2)
                         if row['loops'] else None,
        'useless_ops': row['useless_ops'], 'sleep_ops': row['sleep_ops'],
        'blocks': row['blocks'],
        'cash_below_days': (row['cash_below_days']
                            if row['cash_below_days_observations'] == len(row['months'])
                            else None),
        'unknown_cost_loops': (row['unknown_cost_loops']
                               if row['cost_source_observations'] == len(row['months'])
                               else None),
        'unfunded_cost_loops': (row['unfunded_cost_loops']
                                if row['cost_source_observations'] == len(row['months'])
                                else None),
        'stable_unfunded_loops': (row['stable_unfunded_loops']
                                  if row['stable_unfunded_observations'] == len(row['months'])
                                  else None),
        'stable_unfunded_ops': (row['stable_unfunded_ops']
                                if row['stable_unfunded_observations'] == len(row['months'])
                                else None),
        'capped_wait_months': row['capped_wait_months'],
        'wait_days_mean': round(mean(row['waits']), 2) if row['waits'] else None,
        'unavailable_waits': row['unavailable_waits'],
    } for year, row in sorted(years.items())}
            for arm, years in sorted(grouped.items())}


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


def render_idle(annual):
    print('| Bras | Annee | Mois observes | Boucles | Inutiles (%) | Ops inutiles | Ops Sleep | Jours sous-finances | Cout inconnu (tours) | Prix hors selection (tours) | Attente stable sans selection (tours) | Ops pendant attente stable | Attente plafonnee (mois) | Jours avant financement (moy. connu) | Blocs /1024 |')
    print('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for arm, years in annual.items():
        for year, row in years.items():
            pct = '-' if row['useless_pct'] is None else f"{row['useless_pct']:.2f}"
            days = '-' if row['wait_days_mean'] is None else f"{row['wait_days_mean']:.1f}"
            below_days = '-' if row['cash_below_days'] is None else str(row['cash_below_days'])
            unknown = '-' if row['unknown_cost_loops'] is None else str(row['unknown_cost_loops'])
            unfunded = '-' if row['unfunded_cost_loops'] is None else str(row['unfunded_cost_loops'])
            stable = '-' if row['stable_unfunded_loops'] is None else str(row['stable_unfunded_loops'])
            stable_ops = '-' if row['stable_unfunded_ops'] is None else str(row['stable_unfunded_ops'])
            print(f"| {arm} | {year} | {row['months']} | {row['loops']} | {pct} | "
                  f"{row['useless_ops']} | {row['sleep_ops']} | {below_days} | {unknown} | "
                  f"{unfunded} | {stable} | {stable_ops} | {row['capped_wait_months']} | {days} | "
                  f"{row['blocks']}/1024 |")


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
        logs = Path(tmp) / 'logs'
        logs.mkdir()
        (logs / 'reference_seed42_r0.log').write_text(
            '[0] [I] OPEX 1970-2-1 V309_IDLE loops=10 useless=4 useless_ops=120 '
            'sleep_ops=430 wait_days=-1 blocks=1\n'
            '[0] [I] OPEX 1970-3-1 V309_IDLE loops=30 useless=9 useless_ops=200 '
            'sleep_ops=860 wait_days=60 blocks=2\n', encoding='utf-8')
        x = read_idle_logs(logs)['reference'][1970]
        assert x['months'] == 2 and x['loops'] == 40
        assert x['useless_pct'] == 32.5 and x['blocks'] == 3
        assert x['wait_days_mean'] == 60 and x['unavailable_waits'] == 1
    print('selftest OK')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--opcode-json', type=Path, default=DEFAULT_OPCODE)
    ap.add_argument('--logs', type=Path, help='Optionnel : logs de reference avec C76_REGEN')
    ap.add_argument('--idle-logs', type=Path, help='Logs moteur (bras reference et variante) avec V309_IDLE mensuel')
    ap.add_argument('--arm', default='reference')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.idle_logs is not None:
        rows = read_idle_logs(args.idle_logs)
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            render_idle(rows)
        return
    result = analyse(args.opcode_json, args.logs, args.arm)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        render(result)


if __name__ == '__main__':
    main()
