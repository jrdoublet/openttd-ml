#!/usr/bin/env python3
"""V299: passive, standard-library analysis of C66 JSON/JSONL and engine logs.

December Y vehicle profits refer to Y-1; company profit_year is a rolling
four-quarter measure. Never allocate a multicargo train's profit by capacity.
RAIL-CARGO (branch raildiag) informed the grouping, but its hardcoded 256-wide
map, even-sample median and max-waiting-as-current-stock are not reused.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import statistics
import tempfile
import unittest

# Only the frozen vanilla temperate configuration, not a general cargo decoder.
CARGOS = {"0": "PASS", "1": "COAL", "2": "MAIL", "3": "OIL_",
          "4": "LVST", "5": "GOOD", "6": "GRAI", "7": "WOOD",
          "8": "IORE", "9": "STEL", "10": "VALU"}


def open_text(path):
    return (gzip.open if str(path).endswith(".gz") else open)(
        path, "rt", encoding="utf-8")


def read_json(path):
    with open_text(path) as stream:
        return json.load(stream)


def mean(values):
    values = list(values)
    return statistics.mean(values) if values and all(v is not None for v in values) else None


def total(values):
    values = list(values)
    return sum(values) if all(v is not None for v in values) else None


def ratio(a, b):
    return a / b if a is not None and b else None


def cargo_key(line):
    cargos = [CARGOS.get(str(c), 'ID:' + str(c)) for c, n in
              line.get('capacity_by_cargo', {}).items() if n > 0]
    return '+'.join(sorted(cargos)) if cargos else 'UNKNOWN'


def freight(line):
    return any(str(c) not in ('0', '2') and n > 0
               for c, n in line.get('capacity_by_cargo', {}).items())


def distance(line, width):
    tiles = line.get('ordered_station_tiles', [])
    if len(tiles) != 2 or any(t is None for t in tiles):
        return None
    a, b = tiles
    return abs(a % width - b % width) + abs(a // width - b // width)


def line_metrics(lines, width):
    trains = total(l.get('vehicles') for l in lines)
    profit = total(l.get('profit_last_year_gbp') for l in lines)
    dists = [distance(l, width) for l in lines]
    caps = defaultdict(int)
    for line in lines:
        for cargo, cap in line.get('capacity_by_cargo', {}).items():
            caps[CARGOS.get(str(cargo), str(cargo))] += cap
    return dict(lines=len(lines), vehicles=trains, vehicles_per_line=ratio(trains, len(lines)),
                capacity_by_cargo=dict(caps),
                capacity_per_vehicle_by_cargo={c: ratio(n, trains) for c, n in caps.items()},
                median_manhattan=(statistics.median(d for d in dists if d is not None)
                                  if any(d is not None for d in dists) else None),
                distance_known=sum(d is not None for d in dists),
                profit_gbp=profit, profit_per_vehicle_gbp=ratio(profit, trains))


def snapshot_metrics(snap, width):
    if not snap.get('ok'):
        raise ValueError('Invalid line telemetry: ' + str(snap.get('error')))
    lines = snap['lines']
    rail = [l for l in lines if l['mode'] == 'rail']
    groups = {'rail': rail, 'freight': [l for l in rail if freight(l)],
              'passenger_mail': [l for l in rail if not freight(l)]}
    for mode in ('air', 'road', 'water'):
        groups[mode] = [l for l in lines if l['mode'] == mode]
    for key in sorted(set(cargo_key(l) for l in rail) | {'PASS', 'MAIL', 'COAL', 'GOOD'}):
        groups['cargo:' + key] = [l for l in rail if cargo_key(l) == key]
    groups['freight_long_gt160'] = [l for l in rail if freight(l)
                                  and (distance(l, width) or 0) > 160]
    groups['freight_long_non_good'] = [l for l in groups['freight_long_gt160']
                                     if cargo_key(l) != 'GOOD']
    return {key: line_metrics(value, width) for key, value in groups.items()}


def unique_snapshots(snaps):
    out = {}
    for s in snaps:
        key = (s['duel_policy_id'], s['arm'], s['seed'], s['repeat'], s['date'])
        if key in out and out[key] != s:
            raise ValueError('Conflicting duplicate snapshot ' + str(key))
        out[key] = s
    return list(out.values())


def parse_engine(path):
    events, revenues, attempts, regens = [], {}, [], []
    pattern = re.compile(r'\[0\].*?OPEX (\d{4})-(\d+)-(\d+) (\w+) (.*)')
    with open_text(path) as stream:
        for raw in stream:
            match = pattern.search(raw)
            if not match:
                continue
            y, m, d, kind, body = match.groups()
            fields = dict(re.findall(r'(\w+)=([^\s]+)', body))
            row = dict(year=int(y), date=f'{int(y):04}-{int(m):02}-{int(d):02}', **{'event': kind})
            row.update(fields)
            row['event'] = kind
            row['year'] = int(row['year'])
            if kind == 'V284':
                events.append(row)
            elif kind == 'LINE_REVENUE' and fields.get('mode') == 'rail':
                key = (row['year'], fields['line'])
                if key in revenues and revenues[key] != row:
                    raise ValueError('Conflicting line report ' + str(key))
                revenues[key] = row
            elif kind in ('RAIL_ATTEMPT', 'V294C'):
                attempts.append(row)
            elif kind == 'C76_REGEN' and fields.get('phase') == 'regen' and fields.get('kind') == 'full':
                regens.append(row)
    return {'events': events, 'revenues': list(revenues.values()), 'attempts': attempts,
            'regens': regens}


def growth_cohort(before, after, width):
    """Stable local key: observed survivors, no inference about demolished routes."""
    a = {l['line_key_local']: l for l in before['lines'] if l['mode'] == 'rail'}
    b = {l['line_key_local']: l for l in after['lines'] if l['mode'] == 'rail'}
    result = {}
    for group, predicate in [('rail', lambda l: True), ('freight', freight),
                              ('passenger_mail', lambda l: not freight(l))]:
        keys = {k for k in a.keys() & b.keys() if predicate(a[k]) and predicate(b[k])
                and a[k].get('station_ids') == b[k].get('station_ids')
                and cargo_key(a[k]) == cargo_key(b[k])}
        result[group] = {'survivors': len(keys),
                         'before': line_metrics([a[k] for k in sorted(keys)], width),
                         'after': line_metrics([b[k] for k in sorted(keys)], width),
                         'new_keys': sum(predicate(b[k]) for k in b.keys() - a.keys()),
                         'lost_keys': sum(predicate(a[k]) for k in a.keys() - b.keys()),
                         'changed_keys': sum(predicate(a[k]) and k not in keys
                                             for k in a.keys() & b.keys())}
    return result


def revenue_summary(rows):
    """Annual NoAI reports: source current stock; prediction only on full years."""
    result = {}
    for name, pred in [('freight', lambda r: r.get('kind') == 'freight'),
                       ('passenger_mail', lambda r: r.get('kind') != 'freight')]:
        selected = [r for r in rows if pred(r)]
        known = [r for r in selected if int(r.get('wait_a', -1)) >= 0
                 and int(r.get('cap', -1)) > 0 and int(r.get('vehs', 0)) > 0]
        mature = [r for r in selected if int(r.get('age', -1)) >= 2]
        ratios = [int(r['wait_a']) / (int(r['cap']) / int(r['vehs'])) for r in known]
        nominal = [r for r in known if int(r.get('platform', -1)) > 0 and int(r.get('wagons', -1)) > 0]
        at_limit = [r for r in nominal if int(r['wagons']) >= 2 * int(r['platform']) - 1]
        result[name] = dict(reports=len(selected), waiting_known=len(known),
            waiting_below_one_train=sum(v < 1 for v in ratios),
            waiting_at_least_one_train=sum(v >= 1 for v in ratios),
            median_waiting_train_equivalents=statistics.median(ratios) if ratios else None,
            one_train=sum(int(r['vehs']) == 1 for r in known),
            multiple_trains=sum(int(r['vehs']) > 1 for r in known),
            multiple_trains_waiting_one_train=sum(int(r['vehs']) > 1 and q >= 1
                                                  for r, q in zip(known, ratios)),
            nominal_platform_known=len(nominal), nominal_platform_full=len(at_limit),
            nominal_platform_full_waiting_one_train=sum(int(r['wait_a']) >=
                int(r['cap']) / int(r['vehs']) for r in at_limit),
            mature_lines=len(mature),
            mature_pred_profit=total(int(r['pred_prof']) for r in mature),
            mature_real_profit=total(int(r['real_prof']) for r in mature))
    return result


def telemetry_waiting(snap):
    """Rated endpoints, not guessed sources. Max since rating update, not stock."""
    result = []
    for l in snap['lines']:
        if l['mode'] != 'rail':
            continue
        for ep in l.get('endpoint_cargo_stats', []):
            for c, g in ep.get('cargo', {}).items():
                if not g.get('rated'):
                    continue
                cap = l['capacity_by_cargo'].get(c)
                result.append(dict(line_key=l['line_key_local'], station_id=ep['station_id'],
                    cargo=CARGOS.get(c, c), accepts=g.get('accepts'),
                    max_waiting=g.get('max_waiting_cargo'), rating=g.get('rating'),
                    max_waiting_train_equivalents=ratio(g.get('max_waiting_cargo'), ratio(cap, l['vehicles']))))
    return result


def analyze(data, checkpoint_rows, engine_dir, years):
    width = 2 ** data['map_size']
    snaps = unique_snapshots(data['line_telemetry']['snapshots'])
    selected = [s for s in snaps if s['year'] in years and '-12-' in s['date']]
    pids = [p if isinstance(p, str) else p['id'] for p in data['policies']]
    expected = {(p, a, seed, repeat, year) for p in pids for a in ('OpexAI', 'AAAHogEx')
                for seed in data['seeds'] for repeat in range(data['repeats']) for year in years}
    observed = {(s['duel_policy_id'], s['arm'], s['seed'], s['repeat'], s['year']) for s in selected}
    coverage = dict(expected=len(expected), observed=len(observed),
                    missing=sorted(expected - observed), extra=sorted(observed - expected),
                    unresolved_vehicles=sum(len(s['unresolved_vehicles']) for s in selected))
    coverage['complete'] = not coverage['missing'] and not coverage['extra'] and len(selected) == len(expected)
    per_game = []
    groups = defaultdict(list)
    for s in selected:
        item = {k: s[k] for k in ('duel_policy_id', 'arm', 'seed', 'repeat', 'year', 'date')}
        item['unresolved_vehicles'] = len(s['unresolved_vehicles'])
        item['metrics'] = snapshot_metrics(s, width)
        item['rated_endpoint_waiting'] = telemetry_waiting(s)
        per_game.append(item)
        groups[(s['duel_policy_id'], s['arm'], s['year'])].append(item)
    averages = []
    for (policy, arm, year), items in sorted(groups.items()):
        averaged = {}
        for group in sorted(set().union(*(i['metrics'] for i in items))):
            metrics = [i['metrics'].get(group, line_metrics([], width)) for i in items]
            averaged[group] = {}
            for key in metrics[0]:
                if key in ('capacity_by_cargo', 'capacity_per_vehicle_by_cargo'):
                    cargos = set().union(*(m[key] for m in metrics))
                    averaged[group][key] = {c: mean(
                        m[key].get(c, None if key == 'capacity_per_vehicle_by_cargo'
                                   and not m['vehicles'] else 0) for m in metrics)
                        for c in sorted(cargos)}
                    if key == 'capacity_per_vehicle_by_cargo':
                        averaged[group][key] = {c: mean(m[key].get(c, 0)
                            for m in metrics if m['vehicles']) for c in sorted(cargos)}
                elif key in ('vehicles_per_line', 'profit_per_vehicle_gbp', 'median_manhattan'):
                    averaged[group][key] = mean(m[key] for m in metrics if m['lines'])
                else:
                    averaged[group][key] = mean(m[key] for m in metrics)
            averaged[group]['games_with_lines'] = sum(m['lines'] > 0 for m in metrics)
        averages.append(dict(policy=policy, arm=arm, year=year, games=len(items), metrics=averaged))
    cohorts = []
    for s in selected:
        if s['year'] != 1979:
            continue
        before = [a for a in selected if a['year'] == 1975 and all(
            a[k] == s[k] for k in ('duel_policy_id', 'arm', 'seed', 'repeat'))]
        if len(before) == 1:
            cohorts.append(dict(policy=s['duel_policy_id'], arm=s['arm'], seed=s['seed'],
                                repeat=s['repeat'], metrics=growth_cohort(before[0], s, width)))
    logs = []
    for policy in data['policies']:
        # Policy list schema is checked against the manifest/result, not guessed from file order.
        pid = policy if isinstance(policy, str) else policy['id']
        for seed in data['seeds']:
            for repeat in range(data['repeats']):
                base = Path(engine_dir) / f'{pid}_seed{seed}_r{repeat}.log'
                path = base if base.exists() else Path(str(base) + '.gz')
                parsed = parse_engine(path)
                annual = {}
                for year in years:
                    events = [e for e in parsed['events'] if e['year'] == year]
                    annual[str(year)] = dict(
                        decisions=dict(Counter(e.get('action', '?') + ':' +
                            e.get('reason', e.get('kind', '?')) for e in events)),
                        reports=revenue_summary([r for r in parsed['revenues'] if r['year'] == year]))
                logs.append(dict(policy=pid, seed=seed, repeat=repeat, path=str(path),
                                 sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                 annual=annual, **parsed))
    company = {}
    for row in checkpoint_rows:
        if row['date'][:4].isdigit() and int(row['date'][:4]) in years and '-12-' in row['date']:
            key = (row['duel_policy_id'], *row['run'], row['date'])
            fields = {k: row.get(k) for k in ('profit_year', 'profit_year_quarters_available',
                      'profit_year_quarters_valid', 'profit_year_coverage', 'money',
                      'company_value', 'primary_vehicles_by_mode', 'vehs_chunk_valid')}
            if key in company and company[key]['metrics'] != fields:
                raise ValueError('Conflicting company checkpoint')
            company[key] = dict(policy=key[0], arm=key[1], seed=key[2], repeat=key[3],
                                date=key[4], metrics=fields)
    return dict(campaign=data['campaign_id'], map_width=width,
                source_bundle_sha256=data.get('source_bundle_sha256'),
                manifest_sha256=data.get('manifest_sha256'), policies=data['policies'],
                comparison=data.get('policy_comparison'), failed_runs=data.get('failed_runs'),
                games=data.get('games'), coverage=coverage, per_game=per_game, averages=averages,
                cohorts_1975_1979=cohorts, company=list(company.values()), logs=logs)


def tables(report):
    out = ['# V299 — tableaux reproductibles', '',
           'Cliché décembre Y ; profit véhicules = année Y−1, en k£. Moyennes par partie.',
           'AAA reste séparé par bras ; v299 = adapt400. Ratios et médianes : moyenne des parties avec des lignes dans la catégorie ; distances sur les lignes à deux extrémités connues. Les effectifs incluent les autres lignes.',
           'Capacités : moyenne conditionnelle aux parties équipées du cargo, n/N entre parenthèses ; aucune somme de tonnes et places.', '']
    out += ['| Bras | IA | Année | Lignes fret/pax-mail | Trains fret/pax-mail | Trains/ligne fret/pax | Médiane distance fret/pax | Profit rail | Air k£ / véh. | Route k£ / véh. |',
            '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    def f(x):
        return '—' if x is None else f'{x:.1f}'
    def kilo(x):
        return x / 1000 if x is not None else None
    for r in report['averages']:
        m = r['metrics']; a, b = m['freight'], m['passenger_mail']
        pair = lambda key: f(a[key]) + '/' + f(b[key])
        out.append(f"| {r['policy']} | {r['arm']} | {r['year']} | {pair('lines')} | {pair('vehicles')} | {pair('vehicles_per_line')} | {pair('median_manhattan')} | {f(kilo(m['rail']['profit_gbp']))} | {f(kilo(m['air']['profit_gbp']))} / {f(m['air']['vehicles'])} | {f(kilo(m['road']['profit_gbp']))} / {f(m['road']['vehicles'])} |")
    out += ['', '| Bras | IA | Année | PASS | MAIL | COAL | GOOD | Autres et mixtes | Profit/train rail |',
            '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in report['averages']:
        m = r['metrics']
        vals = [kilo(m['cargo:' + c]['profit_gbp']) for c in ('PASS', 'MAIL', 'COAL', 'GOOD')]
        rail_profit = kilo(m['rail']['profit_gbp'])
        rest = rail_profit - sum(vals) if rail_profit is not None and None not in vals else None
        out.append('| ' + ' | '.join([r['policy'], r['arm'], str(r['year']),
                     *map(f, vals), f(rest), f(kilo(m['rail']['profit_per_vehicle_gbp']))]) + ' |')
    out += ['', '| Bras | IA | Année | PASS places/train | MAIL sacs/train | COAL tonnes/train | GOOD caisses/train |',
            '|---|---|---:|---:|---:|---:|---:|']
    for r in report['averages']:
        vals = [f(r['metrics']['cargo:' + c]['capacity_per_vehicle_by_cargo'].get(c))
                + ' (' + str(r['metrics']['cargo:' + c]['games_with_lines']) + '/' + str(r['games']) + ')'
                for c in ('PASS', 'MAIL', 'COAL', 'GOOD')]
        out.append('| ' + ' | '.join([r['policy'], r['arm'], str(r['year']), *vals]) + ' |')
    out += ['', '## Décisions V284 et attente source', '',
            'Comptes sur les trois parties, pas moyennes. Stocks au rapport annuel (date dans le JSON), pas au cliché décembre.', '',
            '| Bras | Année | pick wagon/train | done wagon/train | traction | geometry | approche timeout | Autres refus | Fret attente < 1 rame / connu | Quais pleins / connus | Pleins et attente ≥ 1 rame |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for policy in sorted({l['policy'] for l in report['logs']}):
        logs = [l for l in report['logs'] if l['policy'] == policy]
        for year in range(1973, 1980):
            c = Counter()
            rs = []
            for l in logs:
                c.update(l['annual'][str(year)]['decisions'])
                rs.append(l['annual'][str(year)]['reports']['freight'])
            count = lambda k: sum(x[k] for x in rs)
            other = sum(v for k, v in c.items() if k.startswith(('skip:', 'fail:'))
                        and k not in ('skip:traction', 'skip:geometry', 'skip:approach_timeout'))
            out.append(f"| {policy} | {year} | {c['pick:wagon']}/{c['pick:train']} | {c['done:wagon']}/{c['done:train']} | {c['skip:traction']} | {c['skip:geometry']} | {c['skip:approach_timeout']} | {other} | {count('waiting_below_one_train')}/{count('waiting_known')} | {count('nominal_platform_full')}/{count('nominal_platform_known')} | {count('nominal_platform_full_waiting_one_train')} |")
    cargos = sorted({r['cargo'] for l in report['logs'] for r in l['revenues']
                     if r.get('kind') == 'freight' and r['year'] in range(1973, 1980)})
    out += ['', '## Stock aux sources Opex par cargo', '',
            'Somme des wait_a des rapports annuels, moyenne par partie, unités propres à chaque cargo ; pas un flux annuel. Une absence de ligne vaut zéro, une observation inconnue reste —.', '',
            '| Bras | Année | ' + ' | '.join(cargos) + ' |',
            '|---|---:|' + '---:|' * len(cargos)]
    for policy in sorted({l['policy'] for l in report['logs']}):
        logs = [l for l in report['logs'] if l['policy'] == policy]
        for year in range(1973, 1980):
            values = [mean(total(int(r['wait_a']) if int(r.get('wait_a', -1)) >= 0 else None
                                for r in l['revenues'] if r['year'] == year
                                and r.get('kind') == 'freight' and r['cargo'] == cargo)
                           for l in logs) for cargo in cargos]
            out.append('| ' + ' | '.join([policy, str(year), *map(f, values)]) + ' |')
    if report.get('regen_logs'):
        out += ['', '## Reconstructions complètes — campagne séparée avec probes=10', '',
                'Moyennes par partie ; année du journal. Jours = somme des équivalents C76 arrondis (ops + 93000) / 186000 ; durée de gel réelle non mesurée.', '',
                '| Bras | Année | Reconstructions | Jours équivalents C76 | Millions opcodes |',
                '|---|---:|---:|---:|---:|']
        for policy in sorted({l['policy'] for l in report['regen_logs']}):
            logs = [l for l in report['regen_logs'] if l['policy'] == policy]
            for year in range(1970, 1980):
                rows = [e for l in logs for e in l['regens'] if e['year'] == year]
                out.append(f"| {policy} | {year} | {len(rows)/len(logs):.2f} | {sum(int(e['days']) for e in rows)/len(logs):.2f} | {sum(int(e['ops']) for e in rows)/len(logs)/1e6:.3f} |")
    return '\n'.join(out) + '\n'


class ReaderTests(unittest.TestCase):
    def test_unknown_and_median(self):
        self.assertIsNone(total([1, None]))
        self.assertIsNone(mean([1, None]))
        self.assertIsNone(ratio(0, 0))
        lines = [dict(vehicles=1, profit_last_year_gbp=0, capacity_by_cargo={'1': 30},
                      ordered_station_tiles=[0, n]) for n in (2, 4)]
        self.assertEqual(line_metrics(lines, 512)['median_manhattan'], 3)
        self.assertEqual(distance({'ordered_station_tiles': [511, 512]}, 512), 512)
        self.assertEqual(cargo_key({'capacity_by_cargo': {'0': 40, '2': 10}}), 'MAIL+PASS')

    def test_logs_text_gzip_and_age(self):
        text = ('[script:4] [0] [S] OPEX 1979-1-4 V284 action=skip line=2 reason=traction\n'
                '[script:4] [1] [S] OPEX 1979-1-4 V284 action=done line=9\n'
                '[script:4] [0] [I] OPEX 1979-1-4 LINE_REVENUE mode=rail line=2 year=1979 age=1\n')
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a.log', Path(tmp)/'b.log.gz'
            a.write_text(text)
            with gzip.open(b, 'wt') as stream:
                stream.write(text)
            self.assertEqual(parse_engine(a), parse_engine(b))
            self.assertEqual(len(parse_engine(a)['events']), 1)
            self.assertEqual(len([r for r in parse_engine(a)['revenues'] if int(r['age']) >= 2]), 0)

    def test_duplicate(self):
        s = dict(duel_policy_id='reference', arm='OpexAI', seed=42, repeat=0, date='1979-12-01')
        self.assertEqual(unique_snapshots([s, s]), [s])
        with self.assertRaises(ValueError):
            unique_snapshots([s, dict(s, ok=False)])

    def test_maturity_source_stock_and_missing(self):
        base = dict(kind='freight', vehs='2', cap='120', wait_a='90', pred_prof='100', real_prof='80')
        result = revenue_summary([dict(base, age='1'), dict(base, age='2'),
                                  dict(base, age='3', wait_a='-1')])['freight']
        self.assertEqual(result['mature_lines'], 2)
        self.assertEqual(result['mature_pred_profit'], 200)
        self.assertEqual(result['mature_real_profit'], 160)
        self.assertEqual(result['waiting_known'], 2)
        self.assertEqual(result['median_waiting_train_equivalents'], 1.5)

    def test_existing_cohort_excludes_new_lines(self):
        def line(key, count):
            return dict(line_key_local=key, vehicles=count, mode='rail',
                        capacity_by_cargo={'1': 30*count}, profit_last_year_gbp=100*count,
                        ordered_station_tiles=[1, 10])
        result = growth_cohort({'lines': [line('a', 1), line('lost', 1)]},
                               {'lines': [line('a', 3), line('new', 1)]}, 256)['freight']
        self.assertEqual(result['before']['vehicles'], 1)
        self.assertEqual(result['after']['vehicles'], 3)
        self.assertEqual(result['new_keys'], 1)
        self.assertEqual(result['lost_keys'], 1)

    def test_regen_and_event_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'regen.log'
            path.write_text(
                '[0] OPEX 1973-1-2 C76_REGEN phase=regen kind=full days=5 ops=123 year=1973\n'
                '[0] OPEX 1973-1-3 C76_REGEN phase=regen kind=targeted days=2 ops=12\n'
                '[0] OPEX 1973-1-4 C76_REGEN phase=regen_year kind=full days=9 ops=999\n'
                '[0] OPEX 1973-1-5 V294C event=weight from=120 to=400\n', encoding='utf-8')
            result = parse_engine(path)
            self.assertEqual(len(result['regens']), 1)
            self.assertEqual(result['regens'][0]['ops'], '123')
            self.assertEqual(result['attempts'][0]['event'], 'V294C')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result', type=Path)
    parser.add_argument('--jsonl', type=Path)
    parser.add_argument('--engine-dir', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--markdown', type=Path)
    parser.add_argument('--regen-engine-dir', type=Path,
                        help='Optional completed companion campaign, same policies/seeds/repeats')
    parser.add_argument('--selftest', action='store_true')
    args = parser.parse_args()
    if args.selftest:
        unittest.main(argv=['diag_v299'], exit=True)
        return
    if not all((args.result, args.jsonl, args.engine_dir, args.out)):
        parser.error('--result, --jsonl, --engine-dir and --out are required')
    with open_text(args.jsonl) as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    report = analyze(read_json(args.result), rows, args.engine_dir, range(1973, 1980))
    if args.regen_engine_dir:
        report['regen_logs'] = []
        for log in report['logs']:
            base = args.regen_engine_dir / f"{log['policy']}_seed{log['seed']}_r{log['repeat']}.log"
            path = base if base.exists() else Path(str(base) + '.gz')
            report['regen_logs'].append(dict(policy=log['policy'], seed=log['seed'],
                repeat=log['repeat'], path=str(path),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                regens=parse_engine(path)['regens']))
    report['inputs'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (args.result, args.jsonl)}
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.markdown:
        args.markdown.write_text(tables(report), encoding='utf-8')
    print(f"{len(report['per_game'])} snapshots, {len(report['logs'])} logs → {args.out}")


if __name__ == '__main__':
    main()
