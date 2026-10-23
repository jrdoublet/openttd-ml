#!/usr/bin/env python3
"""Diagnostic descriptif des distances, sans moteur ni dépendance externe.

Grammaire et lecture gzip reprises de diag_v307r_exposition.py ; aucun verdict
économique ou contrôle de santé de campagne n'est déduit de ces journaux.
"""

import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
from pathlib import Path
import re


LOG_RE = re.compile(r"^(.+)_seed(\d+)_r(\d+)\.log(?:\.gz)?$")
EVENT_RE = re.compile(r"\bOPEX\s+(\d{4}-\d{1,2}-\d{1,2})\s+([A-Z0-9_]+)\s*(.*)$")
FIELD_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z_0-9]*)=([^\s]+)")
BOUNDS = ('roadMin', 'roadMax', 'roadGen', 'railMin', 'railAir', 'railMax', 'airMin', 'airMax')
BANDS = {'road': ('roadMin', 'roadMax'), 'rail': ('railMin', 'railMax'),
         'air': ('airMin', 'airMax')}
BUILDS = {'AIR_BUILD': 'air', 'RAIL_BUILD': 'rail', 'ROAD_BUILD': 'road'}


def integer(value):
    try:
        result = int(value)
        return result if result >= 0 else None
    except (ValueError, TypeError):
        return None


def parse_lines(lines):
    """Dates numériques, puis ordre du journal pour départager un même jour."""
    events = []
    for number, line in enumerate(lines, 1):
        match = EVENT_RE.search(line)
        if not match:
            continue
        stamp, kind, payload = match.groups()
        try:
            day = date(*map(int, stamp.split('-')))
        except ValueError as exc:
            raise ValueError(f'Date invalide ligne {number}: {stamp}') from exc
        events.append({'date': day, 'line': number, 'kind': kind,
                       'fields': dict(FIELD_RE.findall(payload))})
    return sorted(events, key=lambda e: (e['date'], e['line']))


def position(mode, distance, bounds):
    if mode not in BANDS:
        return 'non applicable', []
    if distance is None:
        return 'inconnu (distance)', []
    low, high = BANDS[mode]
    outside = []
    if bounds.get(low) is not None and distance < bounds[low]:
        outside.append('sous ' + low)
    # airMax=0 désactive la limite haute dans OpexAirPairInBand.
    if bounds.get(high) is not None and not (mode == 'air' and bounds[high] == 0):
        if distance > bounds[high]:
            outside.append('au-dessus de ' + high)
    missing = any(bounds.get(key) is None for key in (low, high))
    label = ', '.join(outside) if outside else 'dans la bande'
    if missing:
        label = (label + '; ' if outside else '') + 'inconnu (bornes partielles/absentes)'
    return label, outside


def analyse(events):
    result = {'epochs': [], 'chosen': [], 'distances': defaultdict(list),
              'missing': Counter(), 'outside': Counter(), 'rejections': Counter(),
              'unknown_rejections': Counter()}
    bounds = {}
    epoch_date = None
    for event in events:
        fields, kind = event['fields'], event['kind']
        if kind == 'EPOCH_BOUNDS':
            current = {key: integer(fields.get(key)) for key in BOUNDS}
            changes = [f'{k}: {fmt(bounds.get(k))} → {fmt(current[k])}'
                       for k in BOUNDS if current[k] != bounds.get(k)]
            result['epochs'].append((event, current, ', '.join(changes) if epoch_date else 'initial'))
            bounds, epoch_date = current, event['date']
        if kind == 'PROJECT_CHOSEN' or kind in BUILDS:
            mode = fields.get('mode', 'inconnu').lower() if kind == 'PROJECT_CHOSEN' else BUILDS[kind]
            group = ('choisis' if kind == 'PROJECT_CHOSEN' else 'construits', mode)
            distance = integer(fields.get('dist'))
            if distance is None:
                result['missing'][group] += 1
            else:
                result['distances'][group].append(distance)
            if kind == 'PROJECT_CHOSEN':
                label, outside = position(mode, distance, bounds)
                result['chosen'].append((event, mode, distance, epoch_date, label))
                result['outside'].update((mode, reason) for reason in outside)
        # Les compteurs n sont des rejets de tentatives, jamais des paires uniques.
        reason = fields.get('reason', fields.get('outcome', ''))
        normalized = reason.replace('_', '').lower()
        if any(token in normalized for token in ('distanceshort', 'distancelong', 'maxorderdistance', 'paxband')):
            key = (kind, fields.get('mode', 'non indiqué'), reason)
            count = integer(fields.get('n', '1'))
            if count is None:
                result['unknown_rejections'][key] += 1
            else:
                result['rejections'][key] += count
        else:
            for key in ('distanceShort', 'distanceLong'):
                if key in fields:
                    count = integer(fields[key])
                    target = (kind, fields.get('mode', 'non indiqué'), key)
                    if count is None:
                        result['unknown_rejections'][target] += 1
                    else:
                        result['rejections'][target] += count
    return result


def load_logs(folder):
    if not folder.is_dir():
        raise ValueError(f'Dossier absent : {folder}')
    runs = {}
    for path in sorted(folder.iterdir()):
        match = LOG_RE.fullmatch(path.name)
        if not path.is_file() or not match:
            continue
        arm, seed, repeat = match.groups()
        key = (arm, int(seed), int(repeat))
        if key in runs:
            raise ValueError(f'Journal dupliqué (.log/.gz) : {key}')
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rt', encoding='utf-8') as stream:
            runs[key] = analyse(parse_lines(stream))
    if not runs:
        raise ValueError(f'Aucun journal <bras>_seed<N>_r<k>.log[.gz] : {folder}')
    return runs


def distribution(values):
    ordered = sorted(values)
    if not ordered:
        return (0, None, None, None, None, None)
    def quantile(p):
        index = (len(ordered) - 1) * p
        lo = int(index)
        hi = min(lo + 1, len(ordered) - 1)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)
    return (len(ordered), ordered[0], quantile(.25), quantile(.5), quantile(.75), ordered[-1])


def fmt(value):
    return '—' if value is None else f'{value:g}' if isinstance(value, (float, int)) else str(value)


def table(headers, rows):
    def row(cells):
        return '| ' + ' | '.join(fmt(v).replace('|', '\\|') for v in cells) + ' |'
    return '\n'.join([row(headers), row(['---'] * len(headers))] + [row(r) for r in rows])


def summary(records):
    distances, missing, outside, rejections, unknown = defaultdict(list), Counter(), Counter(), Counter(), Counter()
    for record in records:
        for key, values in record['distances'].items():
            distances[key].extend(values)
        missing.update(record['missing'])
        outside.update(record['outside'])
        rejections.update(record['rejections'])
        unknown.update(record['unknown_rejections'])
    keys = set(distances) | set(missing) | {(kind, mode) for kind in ('choisis', 'construits') for mode in BANDS}
    parts = [table(('population', 'mode', 'n', 'min', 'q25', 'médiane', 'q75', 'max', 'dist absente/invalide'),
                   [(kind, mode, *distribution(distances[kind, mode]), missing[kind, mode])
                    for kind, mode in sorted(keys)])]
    parts.append('Hors bande numériques : ' + (', '.join(f'{mode} {reason} = {n}' for (mode, reason), n in sorted(outside.items())) or '0'))
    parts.append(table(('événement de rejet', 'mode déclaré', 'raison', 'somme n', 'n invalide'),
                       [(*key, rejections[key], unknown[key]) for key in sorted(set(rejections) | set(unknown))])
                 if rejections or unknown else 'Rejets de distance : non exposés dans ces journaux (absence de preuve, pas zéro rejet).')
    return '\n\n'.join(parts)


def render(runs):
    parts = ['# Diagnostic des bornes de distance',
             'Distances `dist` telles que journalisées ; quantiles par interpolation linéaire (n−1)p. '
             'AIR : dist est la distance de vol, airMin porte sur Manhattan entre villes : '
             '« hors bande » est numérique, pas une preuve de contournement. '
             'Route : roadMax est la frontière économique ; roadGen est le plafond de génération. '
             'Bornes inclusives pour ce diagnostic, airMax=0 sans plafond. '
             'Époque = dernier EPOCH_BOUNDS à la date du projet, ordre des lignes le même jour. '
             'Aucune borne empruntée à une autre répétition. — = inconnu. '
             'n=0 signifie aucun événement observé. Agrégats pondérés par événement, pas par graine. '
             'Rejets : sommes par événement/raison, susceptibles de recompter une paire ; pax_band '
             'ne distingue pas court/long. Aucun contrôle de santé ni verdict économique.']
    arms = sorted({key[0] for key in runs})
    for arm in arms:
        parts.append(f'## Bras {arm}')
        for seed in sorted({key[1] for key in runs if key[0] == arm}):
            parts.append(f'### Graine {seed}')
            records = []
            for key in sorted(k for k in runs if k[:2] == (arm, seed)):
                record = runs[key]
                records.append(record)
                parts.append(f'#### Répétition {key[2]}')
                parts.append(table(('date', 'ligne', *BOUNDS, 'évolution'),
                                   [(event['date'], event['line'], *(bounds[b] for b in BOUNDS), change or 'inchangé')
                                    for event, bounds, change in record['epochs']])
                             if record['epochs'] else 'Aucun EPOCH_BOUNDS exposé.')
                parts.append(table(('date', 'ligne', 'mode', 'src', 'dst', 'dist', 'époque', 'position numérique'),
                                   [(e['date'], e['line'], mode, e['fields'].get('src'), e['fields'].get('dst'), dist, epoch, label)
                                    for e, mode, dist, epoch, label in record['chosen']])
                             if record['chosen'] else 'Aucun PROJECT_CHOSEN exposé.')
            parts.append(summary(records))
        parts.append(f'### Agrégat du bras {arm}')
        parts.append(summary([v for k, v in runs.items() if k[0] == arm]))
    return '\n\n'.join(parts) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logs', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        print(render(load_logs(args.logs)), end='')
    except (OSError, ValueError, UnicodeError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
