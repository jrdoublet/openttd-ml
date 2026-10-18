"""Frozen first-half/second-half temporal check on existing sampled rotations."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import statistics

from analyze_rva_cycle import analyze
from calibrate_rva import errors
from rva_learning import DwellModel


def context(row):
    return json.dumps([row[k] for k in ('session','line','engine','composition',
                      'length_16tile','cargo','cargo2','cap','cap2','a','b')], sort_keys=True)


def validate(paths):
    sources, output = [], []
    for path in sorted(map(Path, paths)):
        raw = path.read_bytes()
        data = gzip.decompress(raw) if path.suffix == '.gz' else raw
        result = analyze(data.decode('utf-8',errors='replace').splitlines())
        cycles = [r for r in result['cycles'] if r['residuals']]
        ticks = sorted({r['observed_tick'] for r in cycles})
        cutoff = ticks[(len(ticks)-1)//2] if ticks else None
        model = DwellModel()
        for r in cycles:
            if r['observed_tick'] <= cutoff:
                bounds = [r['dwell_a_days'][i]+r['dwell_b_days'][i] for i in (0,1)]
                model.observe(context(r), r['observed_tick'], bounds)
        for r in cycles:
            if r['forecast_tick'] <= cutoff:
                continue  # no rotation spanning the training/test boundary
            residual = r['residuals']
            physical_dwell = 2 * residual['model_dwell_per_leg_days']
            forecast = model.predict(context(r), r['forecast_tick'], physical_dwell)
            travel = residual['model_cycle_days'] - physical_dwell
            output.append({'source':path.name,'line':r['line'],'vehicle':r['vehicle'],
                'forecast_tick':r['forecast_tick'],'observed_tick':r['observed_tick'],
                'cutoff_tick':cutoff,'actual_interval_days':r['cycle_days'],
                'actual':statistics.mean(r['cycle_days']),
                'baseline':residual['model_cycle_days'],
                'predicted':travel+forecast['dwell'],'learning':forecast})
        sources.append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),
                        'samples':result['samples'],'cycles':len(cycles),'cutoff_tick':cutoff,
                        'contexts':result['contexts'],'cost':result['cost']['session_totals']})
    metrics = {}
    for field in ('baseline', 'predicted'):
        m = errors([(r[field], r['actual']) for r in output])
        metrics[field] = {'n': m['n'], 'mae_days': m['mae_annual'],
                          'bias_days': m['bias_annual'], 'wape': m['wape']}
    return {'schema':1,'split':'first_half_completed_rotations_train_second_half_started_test_per_game',
            'metric':'sampled_cycle_midpoint_days_not_independent_seeds',
            'causal_effect':False,'cost_scope':'old_cycle_probe_only_not_new_evaluator',
            'metrics':metrics,
            'covered':sum(r['learning']['n']>0 for r in output),'sources':sources,'rows':output}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directories',nargs='+',type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();paths=[f for d in a.directories for f in d.glob('*.log*')]
    a.out.write_text(json.dumps(validate(paths),indent=2)+'\n')
