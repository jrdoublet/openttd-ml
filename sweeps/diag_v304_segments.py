"""Summarise V304_SEARCH decision logs; no engine launcher or economic verdict."""
import argparse
import collections
import gzip
import json
from pathlib import Path
import re
import statistics


def read_rows(directory):
    rows = []
    for path in sorted(Path(directory).glob('*.log*')):
        identity = re.fullmatch(r'(.+)_seed(\d+)_r(\d+)\.log(?:\.gz)?', path.name)
        if identity is None:
            raise ValueError(f'Unknown engine log identity: {path}')
        pending_path = None
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rt', encoding='utf-8') as stream:
            for line in stream:
                if '[0]' not in line:
                    continue
                if ' V304_PATH ' in line:
                    fields = dict(re.findall(r'(\w+)=([^\s]+)', line))
                    pending_path = (int(fields['src']), int(fields['dst']),
                                    [int(t) for t in fields['tiles'].split(',') if t])
                    continue
                if ' V304_MEMORY ' in line:
                    fields = dict(re.findall(r'(\w+)=([^\s]+)', line))
                    if not rows or rows[-1]['file'] != path.name or (
                            rows[-1]['src'], rows[-1]['dst']) != (int(fields['src']), int(fields['dst'])):
                        raise ValueError(f'Unmatched memory record in {path}')
                    rows[-1]['memory_stats'] = {
                        k: int(v) for k, v in fields.items() if re.fullmatch(r'-?\d+', v)}
                    continue
                if ' V304_SEARCH ' not in line:
                    continue
                fields = dict(re.findall(r'(\w+)=([^\s]+)', line))
                row = {'file': path.name, 'arm': identity[1], 'seed': int(identity[2]),
                       'repeat': int(identity[3])}
                for key, value in fields.items():
                    row[key] = int(value) if re.fullmatch(r'-?\d+', value) else value
                required = {'src', 'dst', 'dist', 'outcome', 'iters', 'segments',
                            'expanded', 'tile_reexpanded', 'state_reexpanded',
                            'tiles', 'states', 'overflow', 'native_segments'}
                if not required <= row.keys():
                    raise ValueError(f'Incomplete V304 row in {path}: {fields}')
                row['coverage_complete'] = (row['overflow'] == 0 and
                                            row['native_segments'] == row['segments'])
                if pending_path is not None:
                    if row['outcome'] != 'OK' or (row['src'], row['dst']) != pending_path[:2]:
                        raise ValueError(f'Unmatched path record in {path}')
                    row['route'] = pending_path[2]
                    if len(row['route']) != row.get('path_len'):
                        raise ValueError(f'Truncated path record in {path}')
                    pending_path = None
                rows.append(row)
    return rows


def summarise(rows):
    groups = collections.defaultdict(list)
    for row in rows:
        distance = row['dist']
        band = '<100' if distance < 100 else '100-159' if distance < 160 else '>=160'
        groups[(row['arm'], band, row['outcome'])].append(row)
    result = []
    for (arm, band, outcome), group in sorted(groups.items()):
        item = {'arm': arm, 'distance': band, 'outcome': outcome, 'n': len(group),
                'coverage_complete': all(r['coverage_complete'] for r in group)}
        for field in ('iters', 'segments', 'expanded', 'tile_reexpanded', 'state_reexpanded'):
            values = [r[field] for r in group]
            item[field] = {'sum': sum(values), 'mean': statistics.mean(values),
                           'median': statistics.median(values), 'max': max(values)}
        result.append(item)
    return result


def compare_first_pairs(rows):
    """Descriptive only: same nominal lead pair is NOT a frozen map replay."""
    arms = collections.defaultdict(dict)
    for row in rows:
        key = row['seed'], row['repeat'], row['src'], row['dst']
        arms[row['arm']].setdefault(key, row)
    comparisons = []
    for arm, pairs in sorted(arms.items()):
        if arm == 'reference':
            continue
        for key in sorted(pairs.keys() & arms['reference'].keys()):
            ref, var = arms['reference'][key], pairs[key]
            item = {'variant': arm, 'pair': key, 'reference_outcome': ref['outcome'],
                    'variant_outcome': var['outcome'], 'reference_iters': ref['iters'],
                    'variant_iters': var['iters'], 'reference_segments': ref['segments'],
                    'variant_segments': var['segments']}
            if ref['outcome'] == var['outcome'] == 'OK' and 'route' in ref and 'route' in var:
                item['identical_route'] = ref['route'] == var['route']
                item['same_endpoints'] = (ref['route'][0], ref['route'][-1]) == (var['route'][0], var['route'][-1])
                item['path_cost_delta'] = var['path_cost'] - ref['path_cost']
            comparisons.append(item)
    return comparisons


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    rows = read_rows(args.directory)
    if not rows:
        parser.error('No V304_SEARCH rows: absence is not zero reexploration.')
    print(json.dumps({'rows': rows, 'groups': summarise(rows),
                      'first_pairs': compare_first_pairs(rows)}, indent=2))
