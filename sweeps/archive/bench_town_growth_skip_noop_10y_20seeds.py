"""Valid paired benchmark for town_growth_skip_noop."""
import argparse
from pathlib import Path
import sys

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path('/work') if Path('/work').exists() else Path.cwd()
sys.path.insert(0, str(ROOT / 'sweeps'))
import bench_v2
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, SEEDS, SUCCESS_METRICS, arm_statistics,
    enable_savegame_cleanup, experiments, keep, make_cfg, paired_comparisons,
    summarise, write_json_atomically,
)

ARMS = ('OpexAI[town_growth_skip_noop=0]', 'OpexAI[town_growth_skip_noop=1]')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--years', type=int, default=10)
    parser.add_argument('--seeds', nargs='+', type=int, default=list(SEEDS))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--max-workers', type=int, default=3)
    args = parser.parse_args()
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error('invalid years, seeds, or worker count')
    ai_dir = str(ROOT / 'ai' / 'OpexAI')
    built = {
        ARMS[0]: local_folder(ai_dir, 'OpexAI', (('town_growth_skip_noop', 0),)),
        ARMS[1]: local_folder(ai_dir, 'OpexAI', (('town_growth_skip_noop', 1),)),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix('.jsonl')
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(built, args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library('51554648', 'Queue.FibonacciHeap'),
            bananas_ai_library('5046524c', 'Pathfinder.Rail'),
        ),
    ))
    summary = summarise(rows)
    failed = [r for r in summary if not r['run_ok']]
    payload = {
        'openttd_version': OPENTTD_VERSION, 'opengfx_version': OPENGFX_VERSION,
        'years': args.years, 'seeds': args.seeds, 'arms': list(ARMS),
        'openttd_config': make_cfg(1970),
        'design': 'paired OFF/ON; declared and read AI setting; one isolated company per run',
        'success_metrics': list(SUCCESS_METRICS), 'summary': summary,
        'failed_runs': [{'arm': r['arm'], 'seed': r['seed'], 'failure_reason': r['failure_reason']} for r in failed],
        'statistics': arm_statistics(summary, list(ARMS)),
        'paired_comparisons': paired_comparisons(summary, list(ARMS)),
    }
    write_json_atomically(args.out, payload)
    print('failed', len(failed), 'out', args.out)
    for comparison in payload['paired_comparisons']:
        for metric, values in comparison['metrics'].items():
            print(metric, 'difference_pct=', values['mean_difference_percent'], 'wins=', values['arm_a_beats_arm_b'], '/', values['n'])
    if failed:
        raise SystemExit('NoAI failure')

if __name__ == '__main__':
    main()
