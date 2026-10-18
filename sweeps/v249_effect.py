"""Audit V249 hors moteur : couverture, comptes et observations par statue.

Les rapports LINE_REVENUE de janvier portent sur l'année précédente. Les IDs
de lignes sont locaux à chaque duel ; les villes AIR servent de jointure nominale
entre bras, jamais les IDs de lignes. Aucune extrapolation d'un gain manquant.
"""
import argparse
import csv
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from statistics import mean, median

from analyse_line_profit_by_mode import parse_kv_fields


EVENT = re.compile(r"\[0\].*?OPEX (\d+)-(\d+)-(\d+) (\w+) (.*)")


def events(path):
    for number, line in enumerate(path.read_text().splitlines(), 1):
        match = EVENT.search(line)
        if match:
            y, m, d, kind, fields = match.groups()
            yield dict(date=date(int(y), int(m), int(d)).isoformat(),
                       kind=kind, fields=parse_kv_fields(fields), source=f"{path}:{number}")


def stats(values):
    return dict(n=len(values), mean=mean(values) if values else None,
                median=median(values) if values else None)


def write_statues_csv(result, path):
    fields = ['seed', 'repeat', 'town', 'date', 'cost', 'days_to_checkpoint',
              'before_air_profit', 'reference_before_air_profit', 'untreated_before_air_profit',
              'before_air_lines', 'reference_before_air_lines', 'later_line_reports',
              'after_profit', 'annual_causal_gain', 'repaid_within_vehicle_life', 'source']
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for statue in result['statues']:
            row = {k: statue.get(k) for k in fields}
            for src, dst in [('before', 'before_air_profit'), ('reference_before', 'reference_before_air_profit'),
                             ('untreated_before', 'untreated_before_air_profit')]:
                row[dst] = statue[src]['profit']
            row['before_air_lines'] = json.dumps(statue['before']['lines'])
            row['reference_before_air_lines'] = json.dumps(statue['reference_before']['lines'])
            writer.writerow({k: 'unknown' if v is None else v for k, v in row.items()})


def inventory(prefix):
    logs = Path(str(prefix) + "_engine")
    by_game = {}
    hashes = {}
    for path in sorted(logs.glob("*.log")):
        match = re.fullmatch(r"(.+)_seed(\d+)_r(\d+)\.log", path.name)
        if not match:
            continue
        policy, seed, repeat = match.groups()
        by_game[policy, int(seed), int(repeat)] = list(events(path))
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return by_game, hashes


def baseline(evs, town, before, exclude_towns=()):
    """Dernier rapport par ligne AIR reliée nominalement à la ville, avant date.

    Coverage partielle : aucune ville inventée à partir des tuiles route/rail.
    """
    towns, reports = {}, {}
    for event in evs:
        if event['date'] >= before:
            continue
        f = event['fields']
        if event['kind'] == 'AIR_BUILD' and 'src_town' in f and 'dst_town' in f:
            towns[f['line']] = {int(f['src_town']), int(f['dst_town'])}
        if event['kind'] == 'LINE_REVENUE':
            reports[f['line']] = event
    selected = []
    for line, ts in towns.items():
        if line not in reports or (town is not None and town not in ts) or ts.intersection(exclude_towns):
            continue
        r = reports[line]
        selected.append(dict(line=int(line), profit=int(r['fields']['real_prof']),
                             profit_year=int(r['fields']['year']) - 1, report_date=r['date']))
    return dict(lines=selected, profit=sum(r['profit'] for r in selected) if selected else None,
                scope='AIR nominal towns only; partial, not station-nearest-town')


def analyse(prefix):
    prefix = Path(prefix)
    data = json.loads(prefix.with_suffix('.json').read_text())
    games, hashes = inventory(prefix)
    comparison = data['policy_comparison']
    variant, reference = comparison['variant_policy_id'], comparison['reference_policy_id']
    all_statues, skip_counts, ratings, loans = [], Counter(), [], []
    terminal = date.fromisoformat(data['expected_last_checkpoint'])
    for (policy, seed, repeat), evs in games.items():
        if policy != variant:
            continue
        statues = [e for e in evs if e['kind'] == 'V249_STATUE']
        treated_towns = {int(e['fields']['town']) for e in statues}
        ref = games.get((reference, seed, repeat), [])
        for event in evs:
            f = event['fields']
            if event['kind'] == 'V249_SKIP':
                skip_counts[f['reason']] += 1
                if f['reason'] == 'loan':
                    loans.append(dict(seed=seed, repeat=repeat, **event))
            if event['kind'] == 'V249_RATING':
                ratings.append(dict(seed=seed, repeat=repeat, **event))
        for statue in statues:
            f, dt = statue['fields'], date.fromisoformat(statue['date'])
            town = int(f['town'])
            later = [e for e in evs if e['kind'] == 'LINE_REVENUE' and e['date'] > statue['date']]
            all_statues.append(dict(seed=seed, repeat=repeat, town=town, **statue,
                cost=int(f['cost']), days_to_checkpoint=(terminal - dt).days,
                before=baseline(evs, town, statue['date']),
                reference_before=baseline(ref, town, statue['date']),
                untreated_before=baseline(evs, None, statue['date'], treated_towns),
                later_line_reports=len(later), after_profit=None, cargo_transported=None,
                annual_causal_gain=None, repaid_within_vehicle_life=None))
    # Checkpoints are engine save dates, not the end of the engine log.
    paid = [s for s in all_statues if s['date'] < terminal.isoformat()]
    rows = [json.loads(line) for line in prefix.with_suffix('.jsonl').read_text().splitlines()]
    snapshots = {(r['policy_id'], r['run'][1], r['run'][2], r['date']): r
                 for r in rows if r['run'][0] == 'OpexAI'}
    for event in loans:
        # Last preceding snapshot is a diagnostic, not contemporaneous cash.
        candidates = [r for (p, seed, rep, dt), r in snapshots.items()
                      if p == variant and seed == event['seed'] and rep == event['repeat'] and dt <= event['date']]
        r = max(candidates, key=lambda r: r['date']) if candidates else None
        event['prior_snapshot'] = ({k: r[k] for k in ('date', 'money', 'current_loan')} if r else None)
    observed_cost = max((s['cost'] for s in all_statues), default=None)
    cash_bound = sum(e['prior_snapshot']['money'] - e['prior_snapshot']['current_loan'] > observed_cost
                     for e in loans if e['prior_snapshot']) if observed_cost is not None else None
    seed_rows = []
    for pair in comparison['per_pair']:
        ss = [s for s in paid if s['seed'] == pair['seed'] and s['repeat'] == pair['repeat']]
        value_delta = pair['metrics']['company_value']['policy_delta']
        seed_rows.append(dict(seed=pair['seed'], statues_at_checkpoint=len(ss),
            statue_cash_cost=sum(s['cost'] for s in ss), profit_delta=pair['metrics']['profit_year']['policy_delta'],
            value_delta=value_delta, value_delta_plus_statue_cash=value_delta + sum(s['cost'] for s in ss)))
    return dict(campaign=data['campaign_id'], source_bundle_sha256=data['source_bundle_sha256'],
        inputs_sha256={str(prefix.with_suffix('.json')): hashlib.sha256(prefix.with_suffix('.json').read_bytes()).hexdigest(),
                      str(prefix.with_suffix('.jsonl')): hashlib.sha256(prefix.with_suffix('.jsonl').read_bytes()).hexdigest(), **hashes},
        telemetry=data['line_telemetry'], retained_savegames=data['retained_savegames'],
        verdict=comparison['verdict'], aggregates=comparison['aggregates'], statues=all_statues,
        statue_count=len(all_statues), costs=dict(Counter(s['cost'] for s in all_statues)),
        statue_months=dict(sorted(Counter(s['date'][:7] for s in all_statues).items())),
        statues_at_checkpoint=len(paid), statue_cost_at_checkpoint=sum(s['cost'] for s in paid),
        exposure_days=stats([s['days_to_checkpoint'] for s in paid]), skips=dict(skip_counts),
        loan_skips=loans, ratings=ratings, per_seed=seed_rows,
        loan_prior_net_cash_above_observed_cost=cash_bound,
        loan_cash_bound_cost=observed_cost,
        treated_seed_profit_delta=stats([r['profit_delta'] for r in seed_rows if r['statues_at_checkpoint']]),
        untreated_seed_profit_delta=stats([r['profit_delta'] for r in seed_rows if not r['statues_at_checkpoint']]),
        value_delta_plus_statue_cash=stats([r['value_delta_plus_statue_cash'] for r in seed_rows]),
        post_statue_line_reports=sum(s['later_line_reports'] for s in all_statues),
        causal_gain_per_statue=None, repaid_fraction=None, profitable_loan_refusals=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--statues-csv', type=Path)
    args = parser.parse_args()
    result = analyse(args.prefix)
    # Exclusive creation: never overwrite evidence or the input campaign.
    with args.out.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    if args.statues_csv:
        write_statues_csv(result, args.statues_csv)
    print(json.dumps({k: result[k] for k in ('campaign', 'statue_count', 'costs', 'statue_months',
        'statues_at_checkpoint', 'statue_cost_at_checkpoint', 'exposure_days', 'skips',
        'post_statue_line_reports', 'treated_seed_profit_delta', 'untreated_seed_profit_delta',
        'value_delta_plus_statue_cash', 'loan_prior_net_cash_above_observed_cost')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
