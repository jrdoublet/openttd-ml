#!/usr/bin/env python3
"""V307 1.9b: mesurer la demande de jonction censuree dans RAIL_ATTEMPT.

Lecture passive des logs 40x10 PC (bras reference uniquement). Le puits est
identifie par (graine, dst) : les logs ne donnent pas d'ID de gare physique.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
from statistics import median

from diag_v307_sink_joins import (
    ATTEMPT_RE, BUILD_RE, CARGO_DEST, DEFAULT_LOGS, FIELDS_RE, open_log,
)


def percentile(values, p):
    if not values:
        return None
    a = sorted(values)
    return a[min(len(a) - 1, int((len(a) - 1) * p))]


def parse_file(path):
    events = []
    with open_log(path) as lines:
        for raw in lines:
            match = ATTEMPT_RE.search(raw)
            if match:
                fields = dict(FIELDS_RE.findall(match.group(1)))
                if fields.get('shared_dest') == '1' and fields.get('join_end') == 'B':
                    day = raw.split(' OPEX ', 1)[1].split(' ', 1)[0]
                    events.append(('attempt', date(*map(int, day.split('-'))), fields))
                continue
            match = BUILD_RE.search(raw)
            if match:
                fields = dict(FIELDS_RE.findall(match.group(2)))
                if 'dst' in fields and 'cargo' in fields:
                    events.append(('build', date(*map(int, match.group(1).split('-'))), fields))
    return events


def analyse(files):
    if not files:
        raise ValueError('Aucun journal de reference disponible')
    totals = Counter()
    by_category = defaultdict(Counter)
    reasons = Counter()
    failure_by_previous = defaultdict(Counter)
    abnd_iters = []
    sides_present = Counter()
    anomalies = Counter()
    per_seed = {}
    for path in files:
        seed = path.stem.replace('reference_seed', '').split('_', 1)[0]
        events = parse_file(path)
        opened, cargo_by_dst, joined, attempts, build_counts = set(), {}, Counter(), set(), Counter()
        local_reasons = Counter()
        # L'ordre dans un journal correspond a l'ordre d'execution, meme le meme jour.
        for kind, day, f in events:
            if kind == 'build':
                dst = f['dst']
                if f.get('shared_dest') == '1' and f.get('join_end') == 'B':
                    if dst not in opened:
                        anomalies['build_shared_without_initial'] += 1
                    build_counts[dst] += 1
                else:
                    if dst in opened:
                        anomalies['second_nonshared_same_dst'] += 1
                    opened.add(dst)
                    build_counts[dst] += 1
                cargo_by_dst.setdefault(dst, f['cargo'])
                continue
            dst = f.get('dst')
            if dst is None:
                anomalies['attempt_without_dst'] += 1
                continue
            attempts.add(dst)
            if dst not in opened:
                anomalies['attempt_without_observed_initial'] += 1
            reason = f.get('reason', 'MISSING')
            reasons[reason] += 1
            local_reasons[reason] += 1
            totals['attempts'] += 1
            if f.get('ok') == '1':
                totals['ok'] += 1
                joined[dst] += 1
            elif reason == 'SITEAB':
                failure_by_previous[joined[dst]]['SITEAB'] += 1
            elif reason == 'ABND':
                failure_by_previous[joined[dst]]['ABND'] += 1
            if reason == 'ABND':
                try:
                    abnd_iters.append(int(f['iters']))
                except (KeyError, ValueError):
                    anomalies['abnd_without_iters'] += 1
                # 'startx/endx' sont sentinelles (0/-1), pas les cotes de la voie.
                for field in ('join_side', 'parallel_side', 'platform_side'):
                    if field in f:
                        sides_present[field] += 1
        totals['opened'] += len(opened)
        totals['targeted_existing'] += len(opened & attempts)
        totals['targeted_any'] += len(attempts)
        totals['targeted_never_joined'] += len((opened & attempts) - set(joined))
        totals['existing_with_2plus_realised'] += sum(build_counts[x] >= 2 for x in opened)
        totals['targeted_without_initial'] += len(attempts - opened)
        for dst in opened:
            cat = CARGO_DEST.get(cargo_by_dst.get(dst), 'Cargo inconnu')
            by_category[cat]['opened'] += 1
            by_category[cat]['targeted'] += dst in attempts
            by_category[cat]['never_joined'] += dst in attempts and not joined[dst]
            by_category[cat]['realised_multi'] += build_counts[dst] >= 2
        per_seed[seed] = {'opened': len(opened), 'targeted': len(opened & attempts),
                          'never_joined': len((opened & attempts) - set(joined)),
                          'attempts': sum(local_reasons.values())}
    totals['files'] = len(files)
    return {'totals': dict(totals), 'reasons': dict(sorted(reasons.items())),
            'failure_by_prior_joins': {str(k): dict(v) for k, v in sorted(failure_by_previous.items())},
            'abnd_iters': {'n': len(abnd_iters), 'median': median(abnd_iters) if abnd_iters else None,
                           'p90': percentile(abnd_iters, .90), 'max': max(abnd_iters) if abnd_iters else None},
            'categories': {k: dict(v) for k, v in sorted(by_category.items())},
            'side_fields': dict(sides_present), 'anomalies': dict(anomalies),
            'per_seed': per_seed,
            'limitations': ['identifiant physique de gare absent',
                            'aucun cote de quai parallele ni geometrie de voie dans RAIL_ATTEMPT',
                            'absence de tentative ne prouve pas absence de demande potentielle',
                            'categorie inferree du cargo des lignes construites']}


def render(result):
    total = result['totals']
    print('Fichiers', total['files'], 'Puits ouverts', total['opened'],
          'tentatives partagees', total['attempts'])
    print('Issues', result['reasons'])
    print('Puits vises', total['targeted_existing'], 'jamais joints', total['targeted_never_joined'],
          'orphan (puits sans ouverture observee)', total['targeted_without_initial'])
    print('ABND iters', result['abnd_iters'], 'cote du quai', result['side_fields'] or 'indisponible')
    print('SITEAB apres n jonctions reussies', {n: c.get('SITEAB', 0)
          for n, c in result['failure_by_prior_joins'].items()})
    print('| Categorie | Puits ouverts | Vises (%) | Jamais joints | Multi realises (%) |')
    print('|---|---:|---:|---:|---:|')
    for cat, c in result['categories'].items():
        n = c['opened']
        print(f'| {cat} | {n} | {c.get("targeted", 0)} ({100*c.get("targeted", 0)/n:.1f} %) | '
              f'{c.get("never_joined", 0)} | {c.get("realised_multi", 0)} '
              f'({100*c.get("realised_multi", 0)/n:.1f} %) |')
    print('Limites:', '; '.join(result['limitations']))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--logs', type=Path, default=DEFAULT_LOGS)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    files = sorted(a.logs.glob('reference_seed*_r0.log')) + sorted(a.logs.glob('reference_seed*_r0.log.gz'))
    result = analyse(files)
    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        render(result)


if __name__ == '__main__':
    main()
