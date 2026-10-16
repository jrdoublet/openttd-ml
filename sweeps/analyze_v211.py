"""V211 : trajectoire trimestrielle face aux concurrents (lecture seule).

Usage : python sweeps/analyze_v211.py <engine_dir> [<policy_id> ...]

Lit <engine_dir>/<policy>_seed*_r0.log (journaux moteur, --script-debug, v211_rivals_log=1) et
ecrit en Markdown, par annee de jeu (trimestres clos de l'annee) :
- le ratio median nous / meilleur adversaire pour la valeur, le profit trimestriel, la note de
  performance, la tresorerie et la cargaison livree ;
- la part des parties ou nous sommes premiers en valeur, en note et en profit ;
- l'infrastructure mediane de chaque camp ;
- par partie, le premier trimestre a partir duquel un adversaire reste devant nous en valeur.
"""
import collections
import glob
import os
import re
import statistics
import sys

KV = re.compile(r'(\w+)=(\S+)')
METRICS = ('value', 'profit', 'perf', 'bank', 'delivered')
INFRA = ('rail', 'road', 'stations', 'airports')


def num(v):
    try:
        return int(v)
    except ValueError:
        return v


def parse_log(path):
    """Return {quarter_index: {'self': row, 'rivals': [rows]}} from V211_RIVAL lines.

    The row logged on the first day of a quarter describes the quarter just closed, so the
    index is the closed one: year * 4 + quarter (0..3).
    """
    quarters = collections.defaultdict(lambda: {'self': None, 'rivals': []})
    with open(path, errors='replace') as fh:
        for line in fh:
            if ' V211_RIVAL ' not in line:
                continue
            rest = line.split(' OPEX ', 1)[1].split(' ', 2)
            y, m, _ = (int(x) for x in rest[0].split('-'))
            q = y * 4 + (m - 1) // 3 - 1
            row = {k: num(v) for k, v in KV.findall(rest[2])}
            if row.get('self') == 1:
                quarters[q]['self'] = row
            else:
                quarters[q]['rivals'].append(row)
    return {q: d for q, d in quarters.items() if d['self'] is not None and d['rivals']}


def ratio(a, b):
    if b > 0 and a >= 0:
        return a / b
    return None


def year_table(games):
    """Per game year: medians of us / best rival and share of games where we lead."""
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    for quarters in games:
        for q, d in quarters.items():
            year = q // 4
            me = d['self']
            for k in METRICS:
                best = max(r[k] for r in d['rivals'])
                r = ratio(me[k], best)
                if r is not None:
                    acc[year]['ratio_' + k].append(r)
                acc[year]['lead_' + k].append(1 if me[k] >= best else 0)
            for k in INFRA:
                acc[year]['me_' + k].append(me[k])
                acc[year]['adv_' + k].append(max(r[k] for r in d['rivals']))
    return acc


def overtaken_from(quarters, key='value'):
    """First closed quarter from which a rival stays ahead of us on `key` to the end, or None."""
    qs = sorted(quarters)
    first = None
    for q in qs:
        d = quarters[q]
        behind = max(r[key] for r in d['rivals']) > d['self'][key]
        if behind and first is None:
            first = q
        elif not behind:
            first = None
    return first


def fmt_q(q):
    return '—' if q is None else f'{q // 4}-T{q % 4 + 1}'


def main(argv):
    engine, policies = argv[0], argv[1:] or ['ref', 'aa']
    out = ['# V211 — trajectoire face aux concurrents', '']
    for pol in policies:
        logs = sorted(glob.glob(os.path.join(engine, f'{pol}_seed*_r0.log')))
        games = [(os.path.basename(p), parse_log(p)) for p in logs]
        games = [(n, g) for n, g in games if g]
        if not games:
            continue
        out += [f'## Politique `{pol}` : {len(games)} parties', '',
                '### Ratios médians nous / meilleur adversaire et part des parties où nous menons', '',
                '| année | trimestres | valeur | profit | note | trésorerie | livré | 1er valeur | 1er note | 1er profit |',
                '|---|---|---|---|---|---|---|---|---|---|']
        acc = year_table([g for _, g in games])
        med = lambda xs: statistics.median(xs) if xs else float('nan')
        share = lambda xs: sum(xs) / len(xs) if xs else float('nan')
        for year in sorted(acc):
            a = acc[year]
            out.append(f"| {year} | {len(a['lead_value'])} | "
                       + ' | '.join(f"{med(a['ratio_' + k]):.2f}" for k in METRICS)
                       + ' | ' + ' | '.join(f"{share(a['lead_' + k]):.0%}" for k in ('value', 'perf', 'profit'))
                       + ' |')
        out += ['', '### Infrastructure médiane (nous / adversaire le plus équipé)', '',
                '| année | ' + ' | '.join(INFRA) + ' |', '|---|' + '---|' * len(INFRA)]
        for year in sorted(acc):
            a = acc[year]
            out.append(f'| {year} | ' + ' | '.join(
                f"{med(a['me_' + k]):.0f} / {med(a['adv_' + k]):.0f}" for k in INFRA) + ' |')
        out += ['', '### Dépassement durable en valeur et en note', '',
                '| partie | dernier trimestre | valeur dépassée dès | note dépassée dès |', '|---|---|---|---|']
        for name, g in games:
            out.append(f'| {name} | {fmt_q(max(g))} | {fmt_q(overtaken_from(g, "value"))} '
                       f'| {fmt_q(overtaken_from(g, "perf"))} |')
        out.append('')
    print('\n'.join(out))


if __name__ == '__main__':
    main(sys.argv[1:])
