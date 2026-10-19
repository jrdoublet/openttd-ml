"""V262 T10/T15 : lecture des sondes V262_ORPHAN_* (par graine et annee).

Usage : python sweeps/analyze_v262_orphans.py <engine_dir>

Lit les journaux ``*seed*.log`` et ``*seed*.log.gz``. Pour chaque graine et chaque
annee de jeu (date de la ligne OPEX, 1er decembre) :
- orphelins par type (train, truck, bus, airport, dock) ;
- entretien mensuel total, somme des six ``cost_*`` rendus par
  AIInfrastructure.GetMonthlyInfrastructureCosts.

Ces couts sont ceux de toute l'infrastructure de la compagnie. L'API ne separe
pas une part orpheline : ce lecteur n'en calcule pas. Un rechargement un 1er
decembre peut dupliquer le releve ; la derniere ligne d'une meme gare, et la
derniere ligne V262_ORPHAN_SUM, l'emportent.
"""
import collections
import glob
import gzip
import os
import re
import sys

KV = re.compile(r'(\w+)=(-?\d+)')
SEED = re.compile(r'seed(\d+)')
TYPES = ('train', 'truck', 'bus', 'airport', 'dock')
COSTS = ('cost_rail', 'cost_signals', 'cost_road', 'cost_canal', 'cost_station', 'cost_airport')


def seed_of(path):
    match = SEED.search(os.path.basename(path))
    return int(match.group(1)) if match else None


def _open(path):
    if path.endswith('.gz'):
        return gzip.open(path, 'rt', errors='replace')
    return open(path, errors='replace')


def parse_log(path):
    """Return {year: {'stations': {id: row}, 'sum': row or None}}."""
    years = {}
    with _open(path) as fh:
        for line in fh:
            if ' V262_ORPHAN_STATION ' in line:
                kind = 'station'
            elif ' V262_ORPHAN_SUM ' in line:
                kind = 'sum'
            else:
                continue
            rest = line.split(' OPEX ', 1)[1].split(' ', 2)
            year = int(rest[0].split('-', 1)[0])
            fields = {k: int(v) for k, v in KV.findall(rest[2])}
            bucket = years.setdefault(year, {'stations': {}, 'sum': None})
            if kind == 'station':
                bucket['stations'][fields['station']] = fields
            else:
                bucket['sum'] = fields
    return years


def orphans_by_type(bucket):
    """Count orphan station rows that carry each facility flag."""
    counts = {t: 0 for t in TYPES}
    for row in bucket['stations'].values():
        for t in TYPES:
            if row.get(t) == 1:
                counts[t] += 1
    return counts


def total_maintenance(sum_row):
    """Sum of the six infrastructure category costs. None if the sum line is absent."""
    if sum_row is None:
        return None
    return sum(int(sum_row[k]) for k in COSTS)


def games_by_seed(paths):
    """Return {seed: [(basename, {year: bucket})]}."""
    grouped = collections.defaultdict(list)
    for path in paths:
        grouped[seed_of(path)].append((os.path.basename(path), parse_log(path)))
    return grouped


def log_paths(engine):
    logs = glob.glob(os.path.join(engine, '*seed*.log'))
    logs += glob.glob(os.path.join(engine, '*seed*.log.gz'))
    return sorted(logs)


def main(argv):
    engine = argv[0]
    grouped = games_by_seed(log_paths(engine))
    out = ['# V262 — infrastructures orphelines', '']
    for seed in sorted(grouped, key=lambda s: (s is None, s)):
        for name, years in grouped[seed]:
            out += [f'## graine {seed} — `{name}`', '',
                    '| année | train | truck | bus | airport | dock | orphelin_n | entretien | maint |',
                    '|---|---|---|---|---|---|---|---|---|']
            for year in sorted(years):
                bucket = years[year]
                counts = orphans_by_type(bucket)
                summary = bucket['sum'] or {}
                maint = total_maintenance(bucket['sum'])
                orphan_n = summary.get('orphan_n', len(bucket['stations']))
                out.append(
                    f"| {year} | {counts['train']} | {counts['truck']} | {counts['bus']} | "
                    f"{counts['airport']} | {counts['dock']} | {orphan_n} | {maint} | "
                    f"{summary.get('maint', '—')} |"
                )
            out.append('')
    sys.stdout.write('\n'.join(out) + ('\n' if out else ''))


if __name__ == '__main__':
    main(sys.argv[1:])
