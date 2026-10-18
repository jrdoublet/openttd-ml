"""Read V233 SITEB exposure logs; never launch a game or infer missing acceptance."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from analyze_v233_exposure import fields


def analyze_sites(lines):
    counts = Counter()
    rejects = []
    results = []
    deliveries = []
    drops = []
    for number, line in enumerate(lines, 1):
        if ' V233_GRAFT ' in line:
            data = fields(line.strip())
            counts[data['state']] += 1
            if data['state'] == 'site_rejected':
                rejects.append({'line': number, **data})
            if data['state'] == 'result':
                results.append({'line': number, **data})
                counts['built'] += data['built'] == '1'
        if ' V233_DELIVERY ' in line:
            deliveries.append({'line': number, **fields(line.strip())})
        if ' V233_DROP ' in line:
            data = fields(line.strip())
            drops.append({'line': number, **data})
            counts['drop_' + data['reason']] += 1
            if data['reason'] == 'month_coverage':
                counts['month_coverage'] += 1
    return {'counts': dict(counts), 'rejections': rejects,
            'results': results, 'deliveries': deliveries, 'drops': drops}


def analyze_directory(directory, pattern='v233b_e13_mode2_seed*_r0.log'):
    logs = {}
    totals = Counter()
    seeds_built = []
    seeds_delivered = []
    for path in sorted(directory.glob(pattern)):
        seed = int(re.search(r'_seed(\d+)_', path.name)[1])
        raw = path.read_bytes()
        result = analyze_sites(raw.decode('utf-8').splitlines())
        result['sha256'] = hashlib.sha256(raw).hexdigest()
        logs[path.name] = result
        totals.update(result['counts'])
        if result['counts'].get('built', 0):
            seeds_built.append(seed)
        if result['deliveries']:
            seeds_delivered.append(seed)
    if not logs:
        raise ValueError('No matching variant logs')
    return {'schema': 1, 'source': str(directory), 'totals': dict(totals),
            'seeds_built': sorted(seeds_built), 'seeds_delivered': sorted(seeds_delivered),
            'logs': logs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--pattern', default='v233b_e13_mode2_seed*_r0.log')
    args = parser.parse_args()
    result = analyze_directory(args.directory, args.pattern)
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
