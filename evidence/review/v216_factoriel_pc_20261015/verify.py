"""Verify the scoped V216 evidence package without results/, Docker or network."""
import collections
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def verify():
    index = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    raw_files = {}
    destinations = set()
    for entry in index['artifacts']:
        rel = Path(entry['evidence'])
        assert not rel.is_absolute() and '..' not in rel.parts
        path = (ROOT / rel).resolve()
        assert path.is_relative_to(ROOT) and path not in destinations
        destinations.add(path)
        assert entry['source'] not in raw_files
        packed = path.read_bytes()
        raw = gzip.decompress(packed)
        for data, kind in [(raw, 'raw'), (packed, 'gzip')]:
            assert len(data) == entry[kind + '_bytes'], entry['source']
            assert hashlib.sha256(data).hexdigest() == entry[kind + '_sha256'], entry['source']
        raw_files[entry['source']] = raw

    def load(name):
        return json.loads(raw_files['results/' + name])

    seeds = []
    for kind in ['aaarail', 'aaacomplet']:
        campaign = 'v216_facto_' + kind + '_40x3_pc_20261015'
        for suffix, games, pairs in [('', 80, 40), ('_smoke', 2, 1)]:
            name = campaign + suffix
            data = load(name + '.json')
            manifest = raw_files['results/' + name + '.manifest.json']
            assert hashlib.sha256(manifest).hexdigest() == data['manifest_sha256']
            assert data['source_bundle_sha256'] == index['common_bundle_sha256']
            assert len(data['games']) == games and all(g['game_ok'] for g in data['games'])
            assert len(data['summary']) == games * 2
            for row in data['summary']:
                assert row['run_ok'] and row['game_ok'] and row['horizon_complete']
                assert row['last_date'] == '1972-12-01' and row['profit_year_quarters_valid'] == 4
            comparison = data['policy_comparison']
            assert comparison['complete_pairs'] == pairs
            assert comparison['comparison_complete'] and comparison['metric_coverage_complete']
        seeds.append(load(campaign + '.json')['seeds'])
    assert seeds[0] == seeds[1] and len(set(seeds[0])) == 40

    contrasts = load('v216_facto_pc_20261015.contrasts.json')['cells']
    cohorts = load('v216_facto_pc_20261015.cohorts.json')
    assert len(cohorts['games']) == 160
    for cell, kind, policy in [('A', 'aaacomplet', 'ref'), ('B', 'aaarail', 'complet'),
                               ('C', 'aaacomplet', 'railseul'), ('D', 'aaarail', 'ref')]:
        groups = collections.defaultdict(list)
        for game in cohorts['games']:
            if game['campaign'] == 'v216_facto_' + kind + '_40x3_pc_20261015' and game['policy'] == policy:
                for mode, cargo, *values in game['rows']:
                    groups[mode + ':' + cargo].append(values)
        for key, rows in groups.items():
            expected = contrasts[cell][key]
            assert len(rows) == expected['lines']
            for offset, field in [(0, 'revenue_sum_ratio'), (2, 'profit_sum_ratio')]:
                actual = sum(r[offset + 1] for r in rows) / sum(r[offset] for r in rows)
                assert abs(actual - expected[field]) < 1e-12, (cell, key, field)
    print(f'OK: {len(raw_files)} archives, 160/160 games + 4/4 smoke games healthy; 80/80 main pairs; manifests and cohort ratios verified.')


if __name__ == '__main__':
    verify()
