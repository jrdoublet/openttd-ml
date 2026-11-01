"""Summarise existing duel/line telemetry without redefining engine extractors.

Usage: python3 sweeps/analyze_road1y_bus.py results/campaign.json [...]
The line snapshot and the company profit measure different accounting periods.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import statistics


def summary(path):
    data = json.loads(path.read_text())
    rows = [json.loads(line) for line in path.with_suffix('.jsonl').read_text().splitlines()]
    final = {}
    for row in rows:
        if row['run'][0] == 'OpexAI':
            seed = row['run'][1]
            if seed not in final or row['date'] > final[seed]['date']:
                final[seed] = row
    snapshots = {s['seed']: s for s in data.get('line_telemetry', {}).get('snapshots', [])
                 if s['arm'] == 'OpexAI'}
    artifacts = [path, path.with_suffix('.jsonl'), path.with_suffix('.manifest.json')]
    output = {'campaign': data['campaign_id'], 'bundle': data['source_bundle_sha256'],
              'artifacts': [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                            for p in artifacts if p.exists()],
              'games': data['games'], 'seeds': {}}
    for seed, row in sorted(final.items()):
        lines = snapshots.get(seed, {}).get('lines', [])
        distances = []
        for line in lines:
            tiles = line.get('ordered_station_tiles', [])
            if len(tiles) == 2:
                # map_size in this harness is an exponent, not a tile count.
                width = 2 ** data['map_size']
                distances.append(abs(tiles[0] % width - tiles[1] % width)
                                 + abs(tiles[0] // width - tiles[1] // width))
        log = path.parent / (path.stem + '_engine') / f'reference_seed{seed}_r0.log'
        text = log.read_text(errors='replace') if log.exists() else ''
        decisions = ' PORTFOLIO_RANK ' in text
        ranks = [dict(re.findall(r'(\w+)=([^\s]+)', line)) for line in text.splitlines()
                 if ' PORTFOLIO_RANK ' in line and 'mode=road' in line]
        output['seeds'][str(seed)] = {
            'date': row['date'], 'profit_year': row['profit_year'],
            'quarters': row['profit_year_quarters_valid'],
            'physical_vehicles': row['primary_vehicles'], 'money': row['money'],
            'observed_opcodes': row['observed_opcodes_total'],
            'opcode_components': row['observed_opcode_components'],
            'lines': len(lines), 'distance_mean': statistics.mean(distances) if distances else None,
            'line_detail': [{k: line.get(k) for k in (
                'ordered_town_ids', 'ordered_station_tiles', 'vehicles',
                'cargo_types', 'profit_this_year_gbp', 'endpoint_cargo_stats')}
                for line in lines],
            'decision_log_available': decisions,
            'rank_first_five': ranks[:5],
            'discards': dict(Counter(re.findall(r'PROJECT_DISCARD[^\n]*reason=([^\s]+)', text))) if decisions else None,
            'discard_details': dict(Counter(re.findall(r'PROJECT_DISCARD[^\n]*detail=(\S+)', text))) if decisions else None,
            'trace_failures': len(re.findall(r'PROJECT_DISCARD[^\n]*detail=TRACEX', text)) if decisions else None,
            'voirie_failures': dict(Counter(re.findall(r'VOIRIE_PLAN fail=([^\s]+)', text))) if decisions else None,
            'build_dates': re.findall(r'OPEX (\S+) ROAD_BUILD ', text),
            'extra_stop_successes': len(re.findall(r'ROAD1Y_EXTRA_STOPS[^\n]*ok=true', text)) if decisions else None,
            'scan_opcodes': sum(map(int, re.findall(r'BUS_DISTRICT_SCAN[^\n]*ops=(\d+)', text))) if decisions else None,
        }
    profits = [v['profit_year'] for v in output['seeds'].values() if v['profit_year'] is not None]
    output['profit_mean'] = statistics.mean(profits) if profits else None
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaigns', nargs='+', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    reports = [summary(path) for path in args.campaigns]
    args.out.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + '\n')
    for report in reports:
        print(report['campaign'], report['profit_mean'],
              [(seed, r['profit_year'], r['lines'], r['physical_vehicles'])
               for seed, r in report['seeds'].items()])


if __name__ == '__main__':
    main()
