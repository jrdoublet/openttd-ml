"""Campaign-level opportunity-cost projection; not per-route causal truth.

Use empirical profit per completed AIR/freight project from TRAIN seeds only.
Predict the paired package's company delta on TEST seeds. No coefficient is
installed in the AI, and lost purchases are not mistaken for lost passengers.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import statistics

from analyze_v216 import parse_log
from calibrate_rva import errors


def features(game):
    latest = {}
    for r in game['line_revenue']:
        if r.get('year') == 1972:
            latest[r['line']] = r
    profits = {'air': [], 'freight': [], 'pax': []}
    for r in latest.values():
        group = 'air' if r.get('mode') == 'air' else r.get('kind')
        if group in profits and isinstance(r.get('real_prof'), (int,float)):
            # Annual LINE_REVENUE reports prior calendar year actual profits.
            # Do not annualise young lines again here: forecast at observed ages.
            profits[group].append(r['real_prof'])
    return {'air_builds': len(game['air_build']),
            'freight_builds': sum(r.get('cargo') not in ('PASS','MAIL') for r in game['rail_build']),
            'pax_builds': sum(r.get('cargo') == 'PASS' for r in game['rail_build']),
            'profits': profits}


def validate(summary, engine):
    data = json.loads(gzip.open(summary, 'rt').read())
    pairs = data['policy_comparison']['per_pair']
    seeds = sorted(p['seed'] for p in pairs)
    train = set(seeds[::2])
    rows, sources = [], []
    for pair in pairs:
        seed = pair['seed']
        if not pair['complete']:
            raise ValueError('Incomplete pair')
        arms = {}
        for arm in ('off', 'pax'):
            path = next(Path(engine).glob(f'{arm}_seed{seed}_r0.log*'))
            arms[arm] = features(parse_log(path))
            sources.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        rows.append({'seed': seed, 'fold': 'train' if seed in train else 'test',
                     'actual': pair['metrics']['profit_year']['policy_delta'], **arms})
    marginal = {}
    for mode in ('air', 'freight'):
        values = [v for r in rows if r['fold'] == 'train' for v in r['off']['profits'][mode]]
        marginal[mode] = statistics.mean(values) if values else None
    for r in rows:
        # Observed added rail profit is explicit: this is a retrospective
        # decomposition/projection of the NETWORK residual, not a live forecast.
        rail = sum(r['pax']['profits']['pax']) - sum(r['off']['profits']['pax'])
        r['rail_only_projection'] = rail
        r['projected'] = rail + sum((r['pax'][mode+'_builds']-r['off'][mode+'_builds'])
                                    * marginal[mode] for mode in marginal)
    return {'schema': 1, 'campaign': data['campaign_id'],
            'summary_sha256': hashlib.sha256(Path(summary).read_bytes()).hexdigest(),
            'source_bundle_sha256': data['source_bundle_sha256'],
            'split': {'train': sorted(train), 'test': sorted(set(seeds)-train)},
            'empirical_profit_per_build': marginal,
            'coverage': 'retrospective_opportunity_cost_not_local_causal_calibration',
            'metrics': {fold: {k: errors([(r[field],r['actual']) for r in rows if r['fold']==fold])
                for k,field in [('rail_only','rail_only_projection'),('network','projected')]}
                for fold in ('train','test')},
            'build_totals': {arm: {key: sum(r[arm][key] for r in rows)
                for key in ('air_builds','freight_builds','pax_builds')} for arm in ('off','pax')},
            'rows': rows, 'sources': sources}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('summary',type=Path);p.add_argument('engine',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(validate(a.summary,a.engine),indent=2)+'\n')
