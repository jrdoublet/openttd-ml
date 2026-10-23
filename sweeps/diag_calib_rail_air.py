#!/usr/bin/env python3
"""Offline DIST-BORNES-1 calibration. No engine calls; stdlib only.

Reuse current calibration log grammar/reader and distance diagnostic quantiles.
AIR_BUILD.cost is a PLAN, never an actual expense. Profit ratios are fleet-scaled
operating profit / predicted net profit, not a like-for-like accounting ROI.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from analyse_calibration_projets import LINE_RE, KV_RE, open_text
from diag_dist_bornes import LOG_RE, distribution
from diag_rail_profit_components_20261021 import number

BANDS = ('0-80', '80-140', '140-200', '200+')


def band(d):
    if d is None or d < 0:
        return 'unknown'
    return BANDS[sum(d >= cut for cut in (80, 140, 200))]


def ratio(actual, predicted):
    return actual / predicted if actual is not None and predicted is not None and predicted > 0 else None


def parse_game(lines):
    """Consume preceding exact directed pair+cargo choices, scoped to one game.

    Successful attempts must be same day/pair as BUILD; never borrow a failed
    attempt, a different cargo or another company's records. First mature annual
    report only: one observation per line, age>=2 excludes the partial first year.
    """
    choices, attempts, builds = {}, {}, {}
    rows, counts = [], Counter()
    for lineno, raw in enumerate(lines, 1):
        match = LINE_RE.search(raw)
        if not match:
            continue
        y, m, d, tag, payload = match.groups()
        stamp = f'{int(y):04}-{int(m):02}-{int(d):02}'
        f = dict(KV_RE.findall(payload))
        mode = f.get('mode')
        pair = (f.get('src'), f.get('dst'))
        if tag in ('PROJECT_CHOSEN', 'PORTFOLIO_RANK', 'RAIL_ATTEMPT',
                   'RAIL_BUILD', 'AIR_BUILD', 'LINE_REVENUE'):
            counts[tag] += 1
        if tag == 'PROJECT_CHOSEN' and mode in ('rail', 'air') and None not in pair:
            choices[(mode, *pair, f.get('cargo'))] = (lineno, f)
        elif tag == 'RAIL_ATTEMPT' and None not in pair:
            attempts[pair] = (stamp, lineno, f)
            counts['rail_attempt_success' if f.get('ok') == '1' else 'rail_attempt_failed'] += 1
        elif tag in ('RAIL_BUILD', 'AIR_BUILD'):
            mode = tag.split('_')[0].lower()
            cargo = f.get('cargo', 'PASS' if mode == 'air' else None)
            choice = choices.pop((mode, *pair, cargo), None) if None not in pair else None
            attempt = attempts.pop(pair, None) if mode == 'rail' else None
            if attempt and (attempt[0] != stamp or attempt[2].get('ok') != '1'):
                attempt = None
            cf = choice[1] if choice else {}
            af = attempt[2] if attempt else {}
            row = dict(mode=mode, cargo=cargo, line=f.get('line'), date=stamp,
                       build_log_line=lineno, choice_log_line=choice[0] if choice else None,
                       attempt_log_line=attempt[1] if attempt else None,
                       distance=number(f.get('dist')), distance_choice=number(cf.get('dist')),
                       capital_predicted=number(cf.get('cost')),
                       profit_predicted=number(cf.get('profit')),
                       capital_actual=number(f.get('cost')) if mode == 'rail' else None,
                       capital_build_plan=number(f.get('cost')) if mode == 'air' else None,
                       profit_build=number(f.get('pred_profit' if mode == 'rail' else 'profit')),
                       fleet_initial=number(f.get('trains' if mode == 'rail' else 'planes')),
                       capital_pre=number(af.get('pre')), capital_model=number(af.get('model')),
                       capital_quote=number(af.get('quote')), attempt_actual=number(af.get('actual')),
                       revenue=None, revenue_reports=[])
            for key in ('capital_actual', 'capital_pre', 'capital_model', 'capital_quote', 'attempt_actual'):
                if row[key] is not None and row[key] < 0:
                    row[key] = None  # -1 means unavailable in RAIL_ATTEMPT
            row['capital_ratio'] = ratio(row['capital_actual'], row['capital_predicted'])
            row['pre_ratio'] = ratio(row['capital_actual'], row['capital_pre'])
            row['model_ratio'] = ratio(row['capital_actual'], row['capital_model'])
            row['profit_ratio'] = None
            rows.append(row)
            key = (mode, row['line'])
            if row['line'] is None or key in builds:
                raise ValueError(f'Missing/duplicate BUILD line id at log line {lineno}')
            builds[key] = row
        elif tag == 'LINE_REVENUE' and mode in ('rail', 'air'):
            row = builds.get((mode, f.get('line')))
            age, vehicles = number(f.get('age')), number(f.get('vehs'))
            if row is None:
                counts['revenue_without_build'] += 1
                continue
            row['revenue_reports'].append(dict(log_line=lineno, date=stamp, fields=f))
            if age is None or age < 2:
                counts['revenue_immature'] += 1
                continue
            if row['revenue'] is not None:
                continue
            actual, n0, year = number(f.get('real_prof')), row['fleet_initial'], number(f.get('year'))
            if (actual is None or not vehicles or vehicles < 0 or not n0 or n0 < 0
                    or year is None or f.get('cargo') != row['cargo']):
                counts['revenue_unusable'] += 1
                continue
            scaled = actual * n0 / vehicles
            row['revenue'] = dict(log_line=lineno, report_year=year, operating_year=year-1,
                                  age=age, vehicles=vehicles, profit_actual=actual,
                                  profit_scaled=scaled, pred_prof=number(f.get('pred_prof')))
            row['profit_ratio'] = ratio(scaled, row['profit_predicted'])
    return rows, dict(counts)


def stats(values):
    n, _, q25, med, q75, _ = distribution([x for x in values if x is not None])
    return dict(n=n, median=med, q25=q25, q75=q75)


def summarize(rows):
    result = []
    for group in ('rail', 'air', 'rail_PASS', 'rail_FREIGHT'):
        for bucket in (*BANDS, 'unknown'):
            subset = [r for r in rows if band(r['distance']) == bucket and
                      (r['mode'] == group or
                       (group == 'rail_PASS' and r['mode'] == 'rail' and r['cargo'] == 'PASS') or
                       (group == 'rail_FREIGHT' and r['mode'] == 'rail' and r['cargo'] not in (None, 'PASS')))]
            if bucket == 'unknown' and not subset:
                continue
            result.append(dict(group=group, band=bucket, builds=len(subset),
                               choices=sum(r['choice_log_line'] is not None for r in subset),
                               attempts=sum(r['attempt_log_line'] is not None for r in subset),
                               mature=sum(r['revenue'] is not None for r in subset),
                               **{key: stats([r[key] for r in subset]) for key in
                                  ('capital_ratio', 'pre_ratio', 'model_ratio', 'profit_ratio')}))
    return result


def analyse(paths):
    all_rows, sources, counts = [], [], Counter()
    seen = set()
    for supplied in paths:
        p = Path(supplied)
        files = sorted(p.iterdir()) if p.is_dir() else [p]
        found = False
        for path in files:
            match = LOG_RE.fullmatch(path.name)
            if not match or not path.is_file():
                continue
            found = True
            arm, seed, repeat = match.groups()
            key = (str(path.resolve().parent), arm, int(seed), int(repeat))
            if key in seen:
                raise ValueError(f'Duplicate game (.log/.gz or repeated input): {key}')
            seen.add(key)
            with open_text(str(path)) as stream:
                rows, qc = parse_game(stream)
            counts.update(qc)
            for row in rows:
                row.update(source=str(path.resolve()), campaign=path.parent.name,
                           arm=arm, seed=int(seed), repeat=int(repeat))
            all_rows.extend(rows)
            sources.append(dict(path=str(path.resolve()), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                counts=qc, summary=summarize(rows)))
        if not found:
            raise ValueError(f'No <arm>_seed<N>_r<N>.log[.gz] in {p}')
    return dict(schema=1, sources=sources, counts=dict(counts), rows=all_rows,
                summary=summarize(all_rows))


def table(result):
    lines = ['| Mode | Distance | Construits | Choix | Tentatives | Matures | Capital réel/choix : médiane [q25;q75], n | Capital réel/pre : médiane [q25;q75], n | Profit opératoire normalisé/choix : médiane [q25;q75], n |',
             '|---|---|---:|---:|---:|---:|---|---|---|']
    def cell(s):
        return 'NA, n=0' if not s['n'] else f"{s['median']:.3f} [{s['q25']:.3f};{s['q75']:.3f}], n={s['n']}"
    for s in result['summary']:
        lines.append(f"| {s['group']} | {s['band']} | {s['builds']} | {s['choices']} | {s['attempts']} | {s['mature']} | {cell(s['capital_ratio'])} | {cell(s['pre_ratio'])} | {cell(s['profit_ratio'])} |")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('logs', nargs='+', type=Path)
    parser.add_argument('--out', type=Path, help='Optional JSON with all matches and source hashes')
    args = parser.parse_args()
    result = analyse(args.logs)
    if args.out:
        args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    print(table(result))
    print('\nAIR actual capital unavailable; profit ratios mix operating actual/net prediction. '
          'Mature = first age>=2 report, scaled by initial/current fleet; no economic verdict.')


if __name__ == '__main__':
    main()
